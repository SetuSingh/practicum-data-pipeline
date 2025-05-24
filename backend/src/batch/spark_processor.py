"""
Spark Batch Processing Pipeline
Processes CSV data in batches with compliance checking and anonymization

This module implements Research Question 1 (RQ1): Batch processing approach
for compliance monitoring. It demonstrates high-throughput processing of
large datasets with comprehensive compliance analysis and anonymization.

Key Features:
- Batch processing of healthcare/financial data
- HIPAA/GDPR compliance violation detection
- Enhanced Anonymization Engine with configurable parameters
- Performance metrics collection for research comparison
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, to_date, when, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, DateType, BooleanType
import pandas as pd
import time
import sys
import os
import csv

# Import our modular components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
from compliance_rules import detailed_compliance_check
from schemas import schema_registry, get_schema_for_data

# Import anonymization components from the unified location to prevent enum identity issues
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.common.anonymization_engine import EnhancedAnonymizationEngine, AnonymizationConfig, AnonymizationMethod

class SparkBatchProcessor:
    def __init__(self):
        """
        Initialize Spark batch processor with mandatory Spark session
        
        This processor requires Apache Spark for pure batch processing.
        No fallback to pandas - if Spark fails, the processor fails.
        """
        print("Initializing Spark batch processor...")
        
        # Initialize Enhanced Anonymization Engine
        self.anonymization_engine = EnhancedAnonymizationEngine()
        self.spark = None
        
    def _initialize_spark(self):
        """Initialize Spark session with proper configuration - ALWAYS creates fresh session for research benchmarking"""
        # ALWAYS stop existing session first to ensure cold start for research accuracy
        if self.spark is not None:
            try:
                self.spark.stop()
                print("🔄 Stopped existing Spark session for cold start")
            except:
                pass  # Session was already stopped
            self.spark = None
        
        # Clear any global Spark session to force true cold start
        import pyspark.sql
        try:
            pyspark.sql.SparkSession._instantiatedSession = None
            pyspark.sql.SparkSession._activeSession = None
        except:
            pass
        
        # Try to clear file system caches for true cold start (macOS/Linux)
        try:
            import subprocess
            import os
            if os.name == 'posix':  # Unix-like systems
                # Note: This would require sudo, so we'll just note the limitation
                print("🔄 Note: File system caches may still be warm (requires sudo to clear)")
        except:
            pass
        
        try:
            # Initialize fresh Spark session with Java 23 compatibility options
            # Use a unique app name to avoid session reuse
            import time
            app_name = f"DataIntegrityBatchProcessor_{int(time.time())}"
            
            self.spark = SparkSession.builder \
                .appName(app_name) \
                .master("local[*]") \
                .config("spark.sql.adaptive.enabled", "false") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "false") \
                .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
                .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
                .config("spark.kryo.unsafe", "false") \
                .getOrCreate()
            
            # Reduce log verbosity for cleaner output
            self.spark.sparkContext.setLogLevel("WARN")
            print("✅ Fresh Spark session initialized for cold start!")
            
        except Exception as e:
            print(f"❌ Spark initialization failed: {str(e)}")
            print("❌ Pure Spark processing required - no fallback available")
            raise RuntimeError(f"Spark initialization failed: {str(e)}. Pure Spark processing requires a working Spark installation.")
    
    def load_data(self, file_path):
        """
        Load CSV data into Spark DataFrame with auto-detected schema
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            pyspark.sql.DataFrame: Loaded Spark DataFrame
        """
        print(f"Loading data from {file_path}...")
        
        self._initialize_spark()
        
        # For research benchmarking: copy file to avoid file system caching
        import shutil
        import tempfile
        import os
        import time
        temp_file = None
        try:
            # Create a temporary copy to avoid file system caching
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, f"cold_start_{int(time.time())}.csv")
            shutil.copy2(file_path, temp_file)
            actual_file_path = temp_file
            print(f"🔄 Using temporary file copy for cold start: {actual_file_path}")
        except Exception as e:
            # If copying fails, use original file
            actual_file_path = file_path
            print(f"⚠️ Could not create temp file copy: {e}, using original file")
        
        if not self.spark:
            raise RuntimeError("Spark session is not initialized. Cannot load data.")
        
        # First, read a sample to detect schema and get actual CSV columns
        sample_df = self.spark.read.csv(actual_file_path, header=True, inferSchema=True).limit(10)
        sample_data = sample_df.toPandas()
        actual_columns = list(sample_data.columns)
        
        # Auto-detect schema based on filename and data content
        schema_def = get_schema_for_data(sample_data, file_path)
        
        if schema_def:
            print(f"Detected schema: {schema_def.name} ({schema_def.data_type.value})")
            
            # Check if CSV columns match the detected schema
            expected_fields = [field.name for field in schema_def.fields]
            print(f"Expected fields ({len(expected_fields)}): {expected_fields}")
            print(f"Actual CSV columns ({len(actual_columns)}): {actual_columns}")
            
            # Check if all required columns are present (regardless of order)
            if set(actual_columns) == set(expected_fields):
                print("✅ CSV columns match detected schema - using strict schema enforcement")
                
                # Load with inferred schema first
                df = self.spark.read.csv(actual_file_path, header=True, inferSchema=True)
                
                # Reorder columns to match the expected schema order
                if actual_columns != expected_fields:
                    print("🔄 Reordering columns to match schema...")
                    df = df.select(*expected_fields)
                
                # Handle data type conversions before applying strict schema
                print("🔄 Converting data types to match schema...")
                
                spark_schema = schema_def.get_spark_schema()
                for field in spark_schema.fields:
                    current_type = df.schema[field.name].dataType
                    target_type = field.dataType
                    
                    # Convert date to timestamp if needed
                    if isinstance(target_type, TimestampType) and isinstance(current_type, DateType):
                        print(f"   Converting {field.name} from date to timestamp")
                        df = df.withColumn(field.name, to_timestamp(col(field.name)))
                    # Convert string to timestamp if needed (for datetime fields)
                    elif isinstance(target_type, TimestampType) and current_type.typeName() == 'string':
                        print(f"   Converting {field.name} from string to timestamp")
                        df = df.withColumn(field.name, to_timestamp(col(field.name)))
                
                # Now apply the strict schema (this should work after conversions)
                try:
                    df = self.spark.createDataFrame(df.rdd, spark_schema)
                    print("✅ Successfully applied strict schema with type conversions")
                except Exception as e:
                    print(f"⚠️  Schema enforcement failed even after conversions: {e}")
                    print("   Falling back to inferred schema...")
                    df = self.spark.read.csv(actual_file_path, header=True, inferSchema=True)
                    if actual_columns != expected_fields:
                        df = df.select(*expected_fields)
            else:
                print("⚠️  CSV columns don't match detected schema - falling back to inference")
                missing_fields = set(expected_fields) - set(actual_columns)
                extra_fields = set(actual_columns) - set(expected_fields)
                if missing_fields:
                    print(f"   Missing fields: {list(missing_fields)}")
                if extra_fields:
                    print(f"   Extra fields: {list(extra_fields)}")
                df = self.spark.read.csv(actual_file_path, header=True, inferSchema=True)
        else:
            print("No schema detected, using inferred schema")
            df = self.spark.read.csv(actual_file_path, header=True, inferSchema=True)
        
        print(f"Loaded {df.count()} records with schema: {df.schema.simpleString()}")
        
        # Clean up temporary file if it was created
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                os.rmdir(os.path.dirname(temp_file))
                print(f"🧹 Cleaned up temporary file: {temp_file}")
            except Exception as e:
                print(f"⚠️ Could not clean up temporary file: {e}")
        
        return df
    
    def check_compliance(self, df):
        """
        Perform comprehensive compliance checking using modular compliance rules
        
        This method uses the centralized compliance rules engine to check for
        HIPAA/GDPR violations, making it easy to maintain and extend rules.
        
        Args:
            df (pyspark.sql.DataFrame): Input Spark DataFrame with healthcare/financial data
            
        Returns:
            pyspark.sql.DataFrame: Spark DataFrame with detailed compliance check results
        """
        print("Performing compliance checks using modular rule engine...")
        
        if not self.spark:
            raise RuntimeError("Spark session is not initialized. Cannot perform compliance checking.")
        
        try:
            # Convert to Pandas for compliance checking
            pandas_df = df.toPandas()
        except Exception as e:
            print(f"   ❌ Error in DataFrame conversion: {str(e)}")
            raise
        
        # Determine data type for appropriate rule selection
        data_type = 'healthcare' if 'patient_name' in pandas_df.columns else 'financial'
        
        # Apply compliance rules to each record
        compliance_results = []
        for _, record in pandas_df.iterrows():
            record_dict = record.to_dict()
            
            # Use detailed compliance check from modular rules
            compliance_result = detailed_compliance_check(record_dict, data_type)
            
            # Add compliance metadata to record
            record_dict['compliance_violations'] = len(compliance_result['violations'])
            record_dict['compliance_details'] = str(compliance_result['violations'])
            record_dict['is_compliant'] = compliance_result['compliant']
            
            # Add individual violation flags for backward compatibility
            violation_types = [v['type'] for v in compliance_result['violations']]
            record_dict['has_phi_exposure'] = bool('phi_exposure' in violation_types)
            record_dict['has_consent_violation'] = bool('missing_consent' in violation_types)
            record_dict['violation_severity'] = self._get_max_severity(compliance_result['violations'])
            
            compliance_results.append(record_dict)
        
        # Convert back to appropriate DataFrame type
        if self.spark:
            try:
                # Convert to pandas first, then to Spark for better compatibility
                pandas_result = pd.DataFrame(compliance_results)
                result_df = self.spark.createDataFrame(pandas_result)
                total_records = result_df.count()
                violation_records = result_df.filter(col("compliance_violations") > 0).count()
            except Exception as e:
                print(f"   ❌ Spark DataFrame creation failed: {str(e)}")
                print("   ❌ Pure Spark processing required - no fallback available")
                raise RuntimeError(f"Spark DataFrame creation failed: {str(e)}. This indicates a schema or data type issue that must be resolved for pure Spark processing.")
        else:
            # This case should ideally not be reached if __init__ succeeded
            raise RuntimeError("Spark session is not initialized. Cannot perform compliance checking.")
        
        print(f"Compliance check complete:")
        print(f"  Total records: {total_records}")
        print(f"  Records with violations: {violation_records}")
        print(f"  Violation rate: {violation_records/total_records*100:.1f}%")
        
        return result_df
    
    def _get_max_severity(self, violations):
        """Get the highest severity level from violations"""
        if not violations:
            return 'none'
        
        severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        severity_scores = [severity_order.get(v['severity'], 0) for v in violations]
        # Use __builtins__.max to avoid conflict with PySpark's max function
        max_severity = __builtins__['max'](severity_scores) if severity_scores else 0
        
        for severity, level in severity_order.items():
            if level == max_severity:
                return severity
        
        return 'unknown'
    
    def anonymize_data(self, df, method="k_anonymity"):
        """
        Apply anonymization techniques for Research Question 2 (RQ2)
        
        This method implements different anonymization approaches to balance
        data utility and privacy protection. Each method has different
        trade-offs between privacy and data usefulness for research comparison.
        
        Args:
            df (pyspark.sql.DataFrame): Input Spark DataFrame with compliance violations
            method (str): Anonymization method ('k_anonymity' or 'differential_privacy')
            
        Returns:
            pyspark.sql.DataFrame: Spark DataFrame with anonymized sensitive data
        """
        print(f"Applying {method} anonymization...")
        
        if not self.spark:
            raise RuntimeError("Spark session is not initialized. Cannot apply anonymization.")
        
        # Spark-based anonymization
        if method == "k_anonymity":
            # K-Anonymity: Generalize data to ensure k identical records exist
            df = df.withColumn("diagnosis_generalized",
                             when(col("diagnosis").isin("diabetes", "hypertension"), "chronic_disease")
                             .when(col("diagnosis").isin("asthma", "flu"), "respiratory")
                             .otherwise("other"))
            
            # Mask all PHI identifiers with consistent format
            df = df.withColumn("ssn_masked", lit("***-**-****"))      # Masked SSN
            df = df.withColumn("phone_masked", lit("***-***-****"))   # Masked phone
            df = df.withColumn("email_masked", lit("***@***.com"))    # Masked email
            
        elif method == "differential_privacy":
            # Apply DP protection to all sensitive fields
            df = df.withColumn("ssn_dp", lit("DP_PROTECTED"))     # DP-protected SSN
            df = df.withColumn("phone_dp", lit("DP_PROTECTED"))   # DP-protected phone
            df = df.withColumn("email_dp", lit("DP_PROTECTED"))   # DP-protected email
        
        return df
    
    def save_results(self, df, output_path):
        """
        Save processed Spark DataFrame to CSV file for analysis
        
        Args:
            df (pyspark.sql.DataFrame): Processed Spark DataFrame with compliance and anonymization results
            output_path (str): Path where to save the CSV file
            
        Returns:
            pandas.DataFrame: Converted DataFrame for further analysis
        """
        print(f"Saving results to {output_path}...")
        
        if not self.spark:
            raise RuntimeError("Spark session is not initialized. Cannot save results.")
        
        # Convert Spark DataFrame to Pandas for saving
        result_df = df.toPandas()
        result_df.to_csv(output_path, index=False)
        print(f"Saved {len(result_df)} records")
        
        return result_df
    
    def process_batch(self, input_file, output_file, anonymization_method="k_anonymity"):
        """
        Main batch processing pipeline for compliance monitoring and anonymization
        
        This is the core method that demonstrates the batch processing approach
        for Research Question 1. It processes large datasets in a single batch
        operation, providing high throughput but higher latency.
        
        Args:
            input_file (str): Path to input CSV file with raw data
            output_file (str): Path to save processed results
            anonymization_method (str): Method to use for anonymization
            
        Returns:
            dict: Performance metrics for research comparison
        """
        start_time = time.time()
        print("=== Starting Batch Processing ===")
        
        # Force cold Spark context: start new session
        self._initialize_spark()
        
        # Step 1: Load raw data from CSV file
        df = self.load_data(input_file)
        
        # Step 2: Perform compliance checking to identify violations
        df = self.check_compliance(df)
        
        # Step 3: Apply anonymization to protect sensitive data
        df = self.anonymize_data(df, anonymization_method)
        
        # Step 4: Save processed results for analysis
        result_df = self.save_results(df, output_file)
        
        # Calculate processing metrics for research evaluation
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Extract compliance statistics from processed data
        total_records = len(result_df)
        violations = result_df['compliance_violations'].sum() if 'compliance_violations' in result_df.columns else 0
        
        # Display batch processing results
        print("\n=== Batch Processing Complete ===")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Throughput: {total_records/processing_time:.2f} records/second")
        print(f"Total records: {total_records}")
        print(f"Violations found: {violations}")
        print(f"Violation rate: {violations/total_records*100:.1f}%")
        
        # Return metrics for research comparison between processing modes
        return {
            'processing_time': processing_time,
            'throughput': total_records/processing_time,
            'total_records': total_records,
            'violations': violations,
            'violation_rate': violations/total_records
        }
    
    def process_batch_microflow(self, input_file, output_file, batch_size=1000, anonymization_config=None):
        """
        Process data using microflow architecture with clean timing separation
        
        This method implements the research-optimized architecture:
        Pre-Processing → [Time.start() → Pure Pipeline Processing → Time.end()] → Post-Processing
        
        FIXED: ALL Spark operations now happen INSIDE the timed section for uniform boundaries
        
        Args:
            input_file (str): Path to input CSV file
            output_file (str): Path to output CSV file (will be saved in post-processing)
            batch_size (int): Number of records to process in each microflow batch
            anonymization_config (AnonymizationConfig): Configuration for anonymization parameters
            
        Returns:
            dict: Complete processing metrics with separate timing domains
        """
        # Force cold Spark context: start new session
        self._initialize_spark()
        
        # ==================== PRE-PROCESSING PHASE ====================
        # ONLY file path validation and basic setup - NO Spark operations
        pre_processing_start = time.time()
        
        print("📥 Pre-Processing: File validation and basic setup...")
        
        # Basic file validation (infrastructure only)
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Default anonymization config if not provided
        if anonymization_config is None:
            anonymization_config = AnonymizationConfig(
                method=AnonymizationMethod.K_ANONYMITY,
                k_value=5
            )
        
        # Initialize result containers (not timed)
        processing_metrics = {
            'total_records': 0,  # Will be set during processing
            'batch_size': batch_size,
            'batches_processed': 0,
            'pure_processing_times': [],
            'total_processing_time': 0.0,
            'records_per_second': 0.0,
            'violations_found': 0,
            'anonymization_config': anonymization_config
        }
        
        pre_processing_time = time.time() - pre_processing_start
        print(f"   ✅ Pre-processing complete: {pre_processing_time:.3f}s")
        
        # ==================== PIPELINE PROCESSING PHASE ====================
        # ALL Spark operations happen here with clean timing
        print("⚡ Starting pure Spark pipeline processing...")
        
        # 🔥 PIPELINE PROCESSING TIMING STARTS HERE
        pipeline_processing_start = time.time()
        
        # Step 1: Spark DataFrame loading and schema operations (TIMED)
        print("   📊 Loading data with Spark DataFrame operations...")
        
        df = self.spark.read.csv(input_file, header=True, inferSchema=True)
        total_records = df.count()
        
        # Schema detection and enforcement
        # Convert Spark DataFrame to Pandas for schema detection
        pandas_sample = df.limit(100).toPandas()  # Use sample for detection
        detected_schema_name = schema_registry.detect_schema(pandas_sample)
        
        if detected_schema_name:
            detected_schema_obj = schema_registry.get_schema(detected_schema_name)
            if detected_schema_obj:
                detected_schema = {
                    'name': detected_schema_obj.name,
                    'type': detected_schema_obj.data_type.value,
                    'fields': [f.name for f in detected_schema_obj.fields]
                }
            else:
                # Fallback to basic schema
                detected_schema = {
                    'name': 'unknown',
                    'type': 'unknown', 
                    'fields': df.columns
                }
        else:
            # Fallback to basic schema
            detected_schema = {
                'name': 'unknown',
                'type': 'unknown',
                'fields': df.columns
            }
        
        # Get actual CSV columns
        csv_columns = df.columns
        
        # Schema validation and enforcement
        if set(csv_columns) == set(detected_schema['fields']):
            print(f"✅ Schema validated: {detected_schema['name']} ({total_records} records)")
            
            # Reorder columns to match schema
            df = df.select(*detected_schema['fields'])
            
            # Apply data type conversions if schema supports it
            if detected_schema['name'] != 'unknown':
                df = self.apply_schema_types(df, detected_schema)
        else:
            print(f"⚠️ Column mismatch! Using flexible schema mapping")
            # Handle mismatched schemas (existing logic)
            
        # Convert to records for processing
        all_records = df.collect()
        records = [row.asDict() for row in all_records]
        
        # Step 3: Microflow batch processing (TIMED)
        all_processed_records = []  # Final results container
        
        # Process in microflow batches
        for batch_start in range(0, total_records, batch_size):
            batch_end = min(batch_start + batch_size, total_records)
            batch_records = records[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            
            # Process each record in the batch (PIPELINE PROCESSING)
            batch_results = []
            batch_violations = 0
            
            for record in batch_records:
                # Convert Spark Row to dict for processing
                record_dict = record.copy()
                
                # Step 4a: Compliance checking (PIPELINE PROCESSING)
                data_type = 'healthcare' if 'patient_name' in record_dict else 'financial'
                compliance_result = detailed_compliance_check(record_dict, data_type)
                
                # Step 4b: Anonymization if needed (PIPELINE PROCESSING)
                if not compliance_result['compliant']:
                    anonymized_record = self.anonymization_engine.anonymize_record(record_dict, anonymization_config)
                    batch_violations += 1
                else:
                    anonymized_record = record_dict
                
                # Step 4c: Add processing metadata (PIPELINE PROCESSING)
                anonymized_record['compliance_violations'] = len(compliance_result['violations'])
                anonymized_record['compliance_details'] = str(compliance_result['violations'])
                anonymized_record['is_compliant'] = compliance_result['compliant']
                anonymized_record['processing_batch'] = batch_num
                anonymized_record['anonymization_method'] = anonymization_config.method.value
                anonymized_record['anonymization_parameters'] = str(anonymization_config)
                
                batch_results.append(anonymized_record)
            
            # Update metrics (still in pipeline processing)
            processing_metrics['batches_processed'] += 1
            processing_metrics['violations_found'] += batch_violations
            
            # Add to final results (still in pipeline processing)
            all_processed_records.extend(batch_results)
            
            # Progress tracking
            elapsed = time.time() - pipeline_processing_start
            rate = (batch_end) / elapsed if elapsed > 0 else 0
            # Only show progress for larger datasets or final batch
            if total_records > 500 and (batch_num % 2 == 0 or batch_end == total_records):
                print(f"   🔄 Processed batch {batch_num}: {batch_end}/{total_records} records ({rate:.0f} records/sec)")
            elif batch_end == total_records:
                print(f"   🔄 Processed batch {batch_num}: {batch_end}/{total_records} records ({rate:.0f} records/sec)")
        
        # Calculate final metrics
        pipeline_processing_time = time.time() - pipeline_processing_start
        records_per_second = total_records / pipeline_processing_time
        violations_found = sum(1 for record in all_processed_records if record.get('compliance_violations', 0) > 0)
        num_batches = (total_records + batch_size - 1) // batch_size
        average_batch_time = pipeline_processing_time / num_batches if num_batches > 0 else pipeline_processing_time
        print("✅ Spark pipeline processing complete!")
        print(f"   Pipeline processing time: {pipeline_processing_time:.3f}s")
        print(f"   Processing rate: {records_per_second:.0f} records/second")
        print(f"   Violations found: {violations_found}")

        processing_metrics = {
            'total_processing_time': pipeline_processing_time,
            'records_per_second': records_per_second,
            'average_batch_time': average_batch_time,
            'batches_processed': num_batches,
            'violations_found': violations_found,
            'total_records': total_records
        }
        
        # ==================== POST-PROCESSING PHASE ====================
        # File saving and result storage - NO processing timing
        post_processing_start = time.time()
        
        print("💾 Post-Processing: Saving results to CSV...")
        
        # Save results directly to CSV (infrastructure only)
        if all_processed_records:
            # Get all possible field names from all records
            fieldnames = set()
            for record in all_processed_records:
                fieldnames.update(record.keys())
            fieldnames = list(fieldnames)
            
            # Write to CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_processed_records)
            
            print(f"   ✅ Saved {len(all_processed_records)} records to {output_file}")
        else:
            print("   ⚠️ No records to save")
        
        post_processing_time = time.time() - post_processing_start
        print(f"   ✅ Post-processing complete: {post_processing_time:.3f}s")
        
        # ==================== FINAL METRICS ====================
        # Complete metrics with timing separation
        complete_metrics = {
            'processing_approach': 'microflow_batch',
            'pre_processing_time': pre_processing_time,
            'pure_processing_time': pipeline_processing_time,  # This is now the Spark pipeline time
            'post_processing_time': post_processing_time,
            'total_execution_time': pre_processing_time + pipeline_processing_time + post_processing_time,
            'processing_metrics': processing_metrics,
            'timing_separation': {
                'pre_processing': f"{pre_processing_time:.3f}s",
                'pure_processing': f"{pipeline_processing_time:.3f}s",
                'post_processing': f"{post_processing_time:.3f}s"
            }
        }
        
        # Note: Spark session is kept alive for potential post-processing
        # The caller is responsible for stopping the session when done
        
        return complete_metrics
    
    def _apply_anonymization(self, record, method="k_anonymity"):
        """
        Apply anonymization to a single record (helper method)
        
        Args:
            record (dict): Record to anonymize
            method (str): Anonymization method
            
        Returns:
            dict: Anonymized record
        """
        anonymized = record.copy()
        
        if method == "k_anonymity":
            # Apply k-anonymity generalization
            if 'ssn' in record:
                anonymized['ssn'] = f"***-**-{record['ssn'][-4:]}"
            if 'phone' in record:
                anonymized['phone'] = f"***-***-{record['phone'][-4:]}"
            if 'patient_name' in record:
                anonymized['patient_name'] = f"PATIENT_{hash(record['patient_name']) % 1000:03d}"
        
        elif method == "differential_privacy":
            # Apply differential privacy
            if 'ssn' in record:
                anonymized['ssn'] = "DP_PROTECTED_SSN"
            if 'phone' in record:
                anonymized['phone'] = "DP_PROTECTED_PHONE"
            if 'patient_name' in record:
                anonymized['patient_name'] = "DP_PROTECTED_NAME"
        
        elif method == "tokenization":
            # Apply tokenization
            if 'ssn' in record:
                anonymized['ssn'] = f"TOKEN_{hash(record['ssn']) % 10000:04d}"
            if 'phone' in record:
                anonymized['phone'] = f"PHONE_TOKEN_{hash(record['phone']) % 1000:03d}"
            if 'patient_name' in record:
                anonymized['patient_name'] = f"PATIENT_TOKEN_{hash(record['patient_name']) % 1000:03d}"
        
        return anonymized
    
    def start_processing(self, input_file, output_file, anonymization_config=None, use_microflow=True):
        """
        Main entry point for batch processing with option for microflow architecture
        
        Args:
            input_file (str): Path to input CSV file
            output_file (str): Path to output CSV file
            anonymization_config (AnonymizationConfig): Configuration for anonymization parameters
            use_microflow (bool): Whether to use microflow architecture (default: True)
            
        Returns:
            dict: Processing metrics and results
        """
        if use_microflow:
            return self.process_batch_microflow(input_file, output_file, 
                                              batch_size=1000, 
                                              anonymization_config=anonymization_config)
        else:
            # Legacy batch processing (for comparison) - convert config to method string
            method_string = anonymization_config.method.value if anonymization_config else "k_anonymity"
            return self.process_batch(input_file, output_file, method_string)
    
    def stop_processing(self):
        """
        Properly stop Spark session and release resources (standardized method name)
        
        This is important for resource cleanup in Spark applications
        """
        if self.spark:
            self.spark.stop()
            print("🛑 Spark session stopped")
        else:
            print("🛑 No Spark session to stop (pandas mode)")

    def stop(self):
        """
        Properly stop Spark session and release resources
        
        This is important for resource cleanup in Spark applications
        """
        self.stop_processing()

    def apply_schema_types(self, df, detected_schema):
        """Apply schema type conversions to Spark DataFrame"""
        try:
            # Basic type conversions for common fields
            if 'treatment_date' in df.columns:
                # Convert treatment_date to timestamp
                df = df.withColumn('treatment_date', to_timestamp(col('treatment_date')))
            
            if 'timestamp' in df.columns:
                # Ensure timestamp is proper timestamp type
                df = df.withColumn('timestamp', to_timestamp(col('timestamp')))
            
            # Convert boolean fields with proper type handling
            boolean_fields = ['has_violation', 'has_violations']
            for field in boolean_fields:
                if field in df.columns:
                    # Cast to string first, then apply boolean logic
                    df = df.withColumn(field, 
                        when(col(field).cast("string").isin('true', 'True', '1'), True)
                        .when(col(field).cast("string").isin('false', 'False', '0'), False)
                        .when(col(field) == 1, True)
                        .when(col(field) == 0, False)
                        .otherwise(False)
                    )
            
            return df
        except Exception as e:
            print(f"⚠️ Schema type conversion failed: {e}")
            return df  # Return original DataFrame if conversion fails

def main():
    """
    Test the batch processor with healthcare data
    
    This function demonstrates how to use the SparkBatchProcessor for
    research experiments. It processes sample data and outputs metrics
    that can be used for comparison with other processing approaches.
    """
    processor = SparkBatchProcessor()
    
    try:
        # Process healthcare data if available
        if os.path.exists("data/healthcare_batch.csv"):
            print("Processing healthcare data with batch approach...")
            metrics = processor.process_batch(
                "data/healthcare_batch.csv",                    # Input: raw healthcare data
                "data/healthcare_processed_batch.csv",          # Output: processed data
                "k_anonymity"                                   # Anonymization method
            )
            print(f"Batch processing metrics: {metrics}")
        else:
            print("No input data found. Run data generator first!")
            print("Use: python src/common/data_generator.py")
            
    except Exception as e:
        print(f"Error in batch processing: {e}")
    finally:
        # Always cleanup Spark resources
        processor.stop()

if __name__ == "__main__":
    main() 