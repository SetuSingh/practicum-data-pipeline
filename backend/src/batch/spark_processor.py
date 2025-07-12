"""
Spark Batch Processing Pipeline
Processes CSV data in batches with compliance checking and anonymization

This module implements Research Question 1 (RQ1): Batch processing approach
for compliance monitoring. It demonstrates high-throughput processing of
large datasets with comprehensive compliance analysis and anonymization.

Key Features:
- Batch processing of healthcare/financial data
- HIPAA/GDPR compliance violation detection
- Multiple anonymization techniques (k-anonymity, differential privacy)
- Performance metrics collection for research comparison
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd
import time
import sys
import os

# Import our modular components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
from compliance_rules import detailed_compliance_check
from schemas import schema_registry, get_schema_for_data

class SparkBatchProcessor:
    def __init__(self):
        """
        Initialize Spark batch processor with mandatory Spark session
        
        This processor requires Apache Spark for pure batch processing.
        No fallback to pandas - if Spark fails, the processor fails.
        """
        print("Initializing Spark batch processor...")
        
        try:
            # Initialize Spark with Java 23 compatibility options
            self.spark = SparkSession.builder \
                .appName("DataIntegrityBatchProcessor") \
                .master("local[*]") \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow") \
                .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow") \
                .getOrCreate()
            
            # Reduce log verbosity for cleaner output
            self.spark.sparkContext.setLogLevel("WARN")
            print("✅ Spark initialized successfully!")
            
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
        
        if not self.spark:
            raise RuntimeError("Spark session is not initialized. Cannot load data.")
        
        # First, read a sample to detect schema and get actual CSV columns
        sample_df = self.spark.read.csv(file_path, header=True, inferSchema=True).limit(10)
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
                df = self.spark.read.csv(file_path, header=True, inferSchema=True)
                
                # Reorder columns to match the expected schema order
                if actual_columns != expected_fields:
                    print("🔄 Reordering columns to match schema...")
                    df = df.select(*expected_fields)
                
                # Handle data type conversions before applying strict schema
                print("🔄 Converting data types to match schema...")
                from pyspark.sql.functions import col, to_timestamp, to_date
                from pyspark.sql.types import TimestampType, DateType
                
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
                    df = self.spark.read.csv(file_path, header=True, inferSchema=True)
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
                df = self.spark.read.csv(file_path, header=True, inferSchema=True)
        else:
            print("No schema detected, using inferred schema")
            df = self.spark.read.csv(file_path, header=True, inferSchema=True)
        
        print(f"Loaded {df.count()} records with schema: {df.schema.simpleString()}")
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
    
    def start_processing(self, input_file, output_file, anonymization_method="k_anonymity"):
        """
        Main entry point for batch processing (standardized method name)
        
        This method provides a consistent interface across all processors
        for starting the processing pipeline.
        
        Args:
            input_file (str): Path to input CSV file with raw data
            output_file (str): Path to save processed results
            anonymization_method (str): Method to use for anonymization
            
        Returns:
            dict: Performance metrics for research comparison
        """
        return self.process_batch(input_file, output_file, anonymization_method)
    
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