#!/usr/bin/env python3
"""
Pipeline API Routes
Handles pipeline-specific processing and research metrics collection
"""

import os
import sys
import uuid
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional

import json
from kafka import KafkaProducer
import threading
import numpy as np
import pandas as pd

# Add this helper function at the top of the file
def clean_data_for_json_serialization(data):
    """
    Clean data dictionary for JSON serialization, handling all problematic types
    
    This function recursively processes data structures and converts them to
    JSON-serializable formats. It handles NaN values, nested objects, special
    data types, and ensures all dictionary content can be serialized.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Convert keys to strings (required for JSON)
            str_key = str(key)
            cleaned[str_key] = clean_data_for_json_serialization(value)
        return cleaned
    elif isinstance(data, list):
        return [clean_data_for_json_serialization(item) for item in data]
    elif isinstance(data, tuple):
        return [clean_data_for_json_serialization(item) for item in data]
    elif isinstance(data, set):
        return [clean_data_for_json_serialization(item) for item in data]
    elif data is None:
        return None
    elif isinstance(data, bool):
        return data
    elif isinstance(data, (int, float)):
        # Handle NaN and infinity values
        if hasattr(pd, 'isna') and pd.isna(data):
            return None
        try:
            if np.isnan(data) or np.isinf(data):
                return None
        except (TypeError, ValueError):
            pass
        return data
    elif isinstance(data, str):
        return data
    elif isinstance(data, (np.integer, np.floating)):
        # Convert numpy types to Python types
        try:
            value = data.item()
            if np.isnan(value) or np.isinf(value):
                return None
            return value
        except (TypeError, ValueError):
            return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    elif hasattr(data, '__dict__'):
        # Handle custom objects by converting to dict
        try:
            return clean_data_for_json_serialization(data.__dict__)
        except Exception:
            return str(data)
    else:
        # For any other type, try to convert to string
        try:
            # Test if it's JSON serializable
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)

def safe_create_data_record(db_connector, idx, **kwargs):
    """
    Safely create a data record with detailed error handling and logging
    
    This function wraps the database insertion with comprehensive error handling
    and data validation to help debug serialization issues.
    """
    try:
        # Validate that original_data is JSON serializable
        original_data = kwargs.get('original_data', {})
        
        # Special handling for violation_types field (should be a list, not dict)
        if 'violation_types' in kwargs:
            violation_types = kwargs['violation_types']
            if isinstance(violation_types, dict):
                # Convert dict to list of violation type strings
                kwargs['violation_types'] = [str(v) for v in violation_types.values()] if violation_types else []
                print(f"      🔧 Converted violation_types from dict to list for record {idx}")
            elif isinstance(violation_types, list):
                # Handle list of violation dictionaries (from Storm processor)
                cleaned_violations = []
                for violation in violation_types:
                    if isinstance(violation, dict):
                        # Extract the violation type from the dict
                        violation_type = violation.get('type', str(violation))
                        cleaned_violations.append(violation_type)
                    else:
                        cleaned_violations.append(str(violation))
                kwargs['violation_types'] = cleaned_violations
                if any(isinstance(v, dict) for v in violation_types):
                    print(f"      🔧 Converted violation_types list from dicts to strings for record {idx}")
            elif violation_types is None:
                kwargs['violation_types'] = []
        
        # Test JSON serialization before database insertion
        try:
            json.dumps(original_data)
        except (TypeError, ValueError) as json_error:
            # If JSON serialization fails, apply more aggressive cleaning
            print(f"      🔧 JSON serialization failed for record {idx}, applying aggressive cleaning...")
            print(f"      🔧 JSON error: {str(json_error)}")
            
            # Apply the cleaning function multiple times if needed
            cleaned_data = clean_data_for_json_serialization(original_data)
            
            # Test again after cleaning
            try:
                json.dumps(cleaned_data)
                kwargs['original_data'] = cleaned_data
            except (TypeError, ValueError) as still_failing:
                print(f"      🔧 Still failing after cleaning, converting to string representation...")
                kwargs['original_data'] = {"error": "data_not_serializable", "representation": str(original_data)}
        
        # Now attempt database insertion
        return db_connector.create_data_record(**kwargs)
        
    except Exception as e:
        # Log detailed error information
        print(f"      ❌ Database insertion failed for record {idx}: {str(e)}")
        print(f"      🔍 Error type: {type(e).__name__}")
        
        # Log the problematic data structure for debugging
        original_data = kwargs.get('original_data', {})
        print(f"      🔍 Data types in record: {[f'{k}: {type(v).__name__}' for k, v in original_data.items()]}")
        
        # Try to identify the specific problematic field
        for key, value in original_data.items():
            if isinstance(value, dict):
                print(f"      🔍 Found dict field '{key}': {type(value).__name__}")
                print(f"      🔍 Dict content: {value}")
                try:
                    json.dumps(value)
                except Exception as field_error:
                    print(f"      🔍 Field '{key}' not JSON serializable: {str(field_error)}")
        
        # Check other parameters that might be causing issues
        for param_name, param_value in kwargs.items():
            if isinstance(param_value, dict):
                print(f"      🔍 Found dict in parameter '{param_name}': {param_value}")
        
        raise e

# Add src to path for processor imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Ensure that the shared common modules (including anonymization_engine) are imported from
# the *same* location as the processing engines to avoid duplicated module instances,
# which lead to Enum identity mismatches (e.g., AnonymizationMethod.K_ANONYMITY appearing
# as an "unsupported" method during equality checks).
#
# By adding the `src/common` directory directly to `sys.path` we guarantee that
# `import anonymization_engine` below resolves to the **exact** module object used by
# SparkBatchProcessor, StormStreamProcessor, and FlinkHybridProcessor. This alignment
# prevents the `Unsupported anonymization method` error observed in the logs.

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'common'))

# Re-import processors **after** modifying the path so they also use the unified module path
# (needed only on cold starts; harmless on reloads).

from src.batch.spark_processor import SparkBatchProcessor
from src.stream.storm_processor import StormStreamProcessor
from src.hybrid.flink_processor import FlinkHybridProcessor

# Import the shared anonymization components from the unified location
from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod

bp = Blueprint('pipeline', __name__, url_prefix='/pipeline')

class PipelineOrchestrator:
    """
    Orchestrates processing through different pipeline types based on user selection.
    Provides consistent interface and metrics collection for research evaluation.
    """
    
    def __init__(self):
        self.processors = {}
        self.metrics = {
            'batch': [],
            'stream': [],
            'hybrid': []
        }
    
    def get_processor(self, pipeline_type: str):
        """Get or create processor instance for pipeline type"""
        if pipeline_type not in self.processors:
            if pipeline_type == 'batch':
                self.processors[pipeline_type] = SparkBatchProcessor()
            elif pipeline_type == 'stream':
                processor = StormStreamProcessor()
                if processor.initialize_connections():
                    self.processors[pipeline_type] = processor
                else:
                    raise Exception("Failed to initialize stream processor connections")
            elif pipeline_type == 'hybrid':
                processor = FlinkHybridProcessor()
                if processor.initialize_connections():
                    self.processors[pipeline_type] = processor
                else:
                    raise Exception("Failed to initialize hybrid processor connections")
            else:
                raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        return self.processors[pipeline_type]
    
    def process_file(self, job_id: str, filepath: str, pipeline_type: str, processed_folder: str, 
                    anonymization_config: AnonymizationConfig = None, job_instance=None) -> Dict[str, Any]:
        """
        Process a file through the specified pipeline type with comprehensive metrics collection
        
        This method orchestrates processing through different pipeline architectures
        for research comparison and evaluation. It provides consistent interfaces
        and metrics collection across all pipeline types.
        
        Args:
            job_id (str): Unique identifier for this processing job
            filepath (str): Path to the input CSV file
            pipeline_type (str): Type of pipeline ('batch', 'stream', 'hybrid')
            processed_folder (str): Path to the processed files folder
            anonymization_config (AnonymizationConfig): Configuration for anonymization parameters
            job_instance: Optional database job instance for progress tracking
            
        Returns:
            Dict[str, Any]: Comprehensive metrics and results from processing
        """
        # Default anonymization config if not provided
        if anonymization_config is None:
            anonymization_config = AnonymizationConfig(
                method=AnonymizationMethod.K_ANONYMITY,
                k_value=5
            )
        
        start_time = time.time()
        
        try:
            # Get the appropriate processor for the pipeline type
            processor = self.get_processor(pipeline_type)
            
            # Update job status if tracking instance provided
            if job_instance:
                job_instance.status = 'processing'
                job_instance.progress = 5

            if pipeline_type == 'batch':
                return self._process_batch(processor, filepath, job_id, start_time, processed_folder, anonymization_config, job_instance)
            elif pipeline_type == 'stream':
                # Use REAL Kafka streaming only - no fallback
                return self._process_stream_real(processor, filepath, job_id, start_time, processed_folder, anonymization_config, job_instance)
            elif pipeline_type == 'hybrid':
                # Use REAL Kafka hybrid processing only - no fallback
                return self._process_hybrid_real(processor, filepath, job_id, start_time, processed_folder, anonymization_config, job_instance)
            else:
                raise ValueError(f"Unsupported pipeline type: {pipeline_type}")
                
        except Exception as e:
            if job_instance:
                job_instance.status = 'failed'
                job_instance.error = str(e)
            raise
    
    def _process_batch(self, processor: SparkBatchProcessor, filepath: str, job_id: str, 
                      start_time: float, processed_folder: str, anonymization_config: AnonymizationConfig, job_instance=None) -> Dict[str, Any]:
        """
        Process file using batch processing with microflow architecture
        
        This method implements the research-optimized architecture:
        Pre-Processing → [Time.start() → Pure Pipeline Processing → Time.end()] → Post-Processing
        
        All database I/O operations are moved outside the timed processing sections
        to get pure processing performance metrics for research evaluation.
        
        Args:
            processor: Spark batch processor instance
            filepath: Path to input file
            job_id: Unique job identifier
            start_time: Job start timestamp
            processed_folder: Output folder path
            job_instance: Database job instance for tracking
            
        Returns:
            Dict containing processing metrics with clean timing separation
        """
        print(f"🔄 Starting batch processing with microflow architecture...")
        
        try:
            # PRE-PROCESSING: Database setup and job initialization (not timed)
            print("📥 Pre-Processing: Job setup and initialization...")
            pre_processing_start = time.time()
            
            # Update job status (pre-processing, not timed)
            if job_instance:
                job_instance.status = 'initializing'
                job_instance.progress = 10
            
            # Create output path
            output_filename = f"processed_{job_id}_{os.path.basename(filepath)}"
            output_path = os.path.join(processed_folder, output_filename)
            
            # Initialize database connection (pre-processing, not timed)
            from database.postgres_connector import PostgresConnector
            db_connector = PostgresConnector()
            
            pre_processing_time = time.time() - pre_processing_start
            
            # PURE PROCESSING: Use microflow batch processing with clean timing
            print("⚡ Starting pure microflow processing...")
            
            # Update job status before pure processing (not timed)
            if job_instance:
                job_instance.status = 'processing'
                job_instance.progress = 15
            
            # 🔥 PURE PROCESSING TIMING STARTS HERE
            processing_results = processor.process_batch_microflow(
                input_file=filepath,
                output_file=output_path,
                batch_size=1000,  # Process in 1000-record batches
                anonymization_config=anonymization_config
            )
            # 🔥 PURE PROCESSING TIMING ENDS HERE
            
            # POST-PROCESSING: Database operations and result storage (not timed)
            print("💾 Post-Processing: Database operations and result storage...")
            post_processing_start = time.time()
            
            # Update job status after pure processing (not timed)
            if job_instance:
                job_instance.status = 'storing_results'
                job_instance.progress = 85
            
            # Load processed results for database storage (post-processing, not timed)
            processed_df = processor.spark.read.csv(output_path, header=True, inferSchema=True)
            processed_records = processed_df.collect()
            
            # Batch insert all records to database (post-processing, not timed)
            print(f"   Batch inserting {len(processed_records)} records to database...")
            file_id = job_instance.file_id if job_instance and hasattr(job_instance, 'file_id') else None
            # Use db_job_id for database foreign key constraint
            db_job_id = job_instance.db_job_id if job_instance and hasattr(job_instance, 'db_job_id') else job_id
            self._batch_insert_records(db_connector, processed_records, db_job_id, file_id)
            
            # Update job completion status (post-processing, not timed)
            if job_instance:
                job_instance.status = 'completed'
                job_instance.progress = 100
                job_instance.end_time = datetime.now()
                job_instance.total_records = processing_results['processing_metrics']['total_records']
                job_instance.violation_count = processing_results['processing_metrics']['violations_found']
                job_instance.output_path = output_path
            
            post_processing_time = time.time() - post_processing_start
            
            # Combine timing metrics with clean separation
            complete_metrics = {
                'job_id': job_id,
                'pipeline_type': 'batch_microflow',
                'file_path': filepath,
                'output_path': output_path,
                'pre_processing_time': pre_processing_time,
                'pure_processing_time': processing_results['pure_processing_time'],
                'post_processing_time': post_processing_time,
                'total_execution_time': pre_processing_time + processing_results['pure_processing_time'] + post_processing_time,
                'processing_metrics': processing_results['processing_metrics'],
                'timing_separation': {
                    'pre_processing': f"{pre_processing_time:.3f}s",
                    'pure_processing': f"{processing_results['pure_processing_time']:.3f}s",
                    'post_processing': f"{post_processing_time:.3f}s"
                },
                'research_metrics': {
                    'records_per_second': processing_results['processing_metrics']['records_per_second'],
                    'violations_found': processing_results['processing_metrics']['violations_found'],
                    'batches_processed': processing_results['processing_metrics']['batches_processed'],
                    'average_batch_time': processing_results['processing_metrics']['average_batch_time']
                }
            }
            
            print(f"✅ Batch processing completed successfully!")
            print(f"   Pure processing time: {processing_results['pure_processing_time']:.3f}s")
            print(f"   Processing rate: {processing_results['processing_metrics']['records_per_second']:.0f} records/second")
            print(f"   Records processed: {processing_results['processing_metrics']['total_records']}")
            print(f"   Violations found: {processing_results['processing_metrics']['violations_found']}")
            
            # ==================== PROMETHEUS METRICS ====================
            try:
                from src.monitoring.prometheus_metrics import metrics_collector

                metrics_collector.track_processing_performance(
                    pipeline_type='batch',
                    duration=processing_results['pure_processing_time'],
                    records_count=processing_results['processing_metrics']['total_records'],
                    anonymization_method=anonymization_config.method.value if anonymization_config else 'none'
                )
            except Exception as metrics_err:
                print(f"⚠️  Unable to record Prometheus processing metrics: {metrics_err}")

            # Push metrics to Prometheus pushgateway for batch jobs
            try:
                from src.common.pushgateway_client import pushgateway_client
                metrics = processing_results['processing_metrics']
                metrics_to_push = {
                    'processing_time': processing_results['pure_processing_time'],
                    'throughput': metrics['records_per_second'],
                    'total_records': metrics['total_records'],
                    'violations': metrics['violations_found'],
                    'violation_rate': metrics['violations_found']/metrics['total_records'] if metrics['total_records'] > 0 else 0,
                    'records_per_second': metrics['records_per_second'],
                    'anonymization_method': anonymization_config.method.value if anonymization_config else 'k_anonymity'
                }
                pushgateway_client.push_batch_metrics(metrics_to_push)
                print("📊 Metrics pushed to Prometheus pushgateway")
            except Exception as e:
                print(f"⚠️ Failed to push metrics to pushgateway: {e}")
             
            # Clean up Spark session after all operations are complete
            if processor and hasattr(processor, 'stop'):
                processor.stop()
            
            return complete_metrics
            
        except Exception as e:
            print(f"❌ Batch processing failed: {str(e)}")
            
            # Clean up Spark session on failure
            if processor and hasattr(processor, 'stop'):
                processor.stop()
            
            # Update job status on failure (not timed)
            if job_instance:
                job_instance.status = 'failed'
                job_instance.progress = 100
                job_instance.end_time = datetime.now()
                job_instance.error_message = str(e)
            
            raise e
    
    def _batch_insert_records(self, db_connector, records, job_id, file_id=None):
        """
        Batch insert all processed records to database in a single operation
        
        This method replaces individual record inserts with a single batch operation
        to eliminate the N × DB overhead issue and improve performance.
        
        Args:
            db_connector: Database connector instance
            records: List of processed records to insert
            job_id: Job identifier for tracking
            file_id: File identifier for the records (required for database)
        """
        print(f"   Preparing batch insert for {len(records)} records...")
        
        # Prepare all records for batch insertion
        batch_records = []
        violations_batch = []
        
        for idx, record in enumerate(records):
            try:
                # Convert Spark Row to dict
                record_dict = record.asDict() if hasattr(record, 'asDict') else record
                
                # Prepare record for database insertion
                record_data = {
                    'job_id': job_id,
                    'record_id': f"{job_id}_{idx}",
                    'original_data': record_dict,
                    'processed_data': record_dict,
                    'has_pii': self._has_pii_data(record_dict),
                    'has_violations': not record_dict.get('is_compliant', True),
                    'violation_types': self._extract_violation_types(record_dict),
                    'file_id': file_id,  # Use the provided file_id
                }
                
                batch_records.append(record_data)
                
                # Collect violations for batch insertion
                if not record_dict.get('is_compliant', True):
                    violations_batch.append({
                        'file_id': file_id,
                        'record_id': None,  # Will be set after records are inserted
                        'violation_type': 'compliance_violation',
                        'violation_category': 'data_exposure',
                        'severity': 'medium',
                        'description': record_dict.get('compliance_details', 'Compliance violation detected during processing'),
                        'details': record_dict.get('compliance_details', '')
                    })
                    
            except Exception as e:
                print(f"      ⚠️ Error preparing record {idx}: {str(e)}")
                continue
        
        # Perform batch database operations
        try:
            # Single batch insert for all records
            if batch_records:
                print(f"   Executing batch insert for {len(batch_records)} records...")
                db_connector.batch_insert_records(batch_records)
                
            # Single batch insert for all violations
            if violations_batch:
                print(f"   Executing batch insert for {len(violations_batch)} violations...")
                db_connector.batch_insert_violations(violations_batch)
                
            print(f"   ✅ Batch insert completed successfully")
            
        except Exception as e:
            print(f"   ❌ Batch insert failed: {str(e)}")
            # Don't raise here - we don't want database issues to fail the entire processing
            
    def _has_pii_data(self, record_dict):
        """
        Check if record contains PII (Personally Identifiable Information)
        
        Args:
            record_dict: Record dictionary to check
            
        Returns:
            bool: True if record contains PII
        """
        pii_fields = ['ssn', 'phone', 'email', 'patient_name', 'medical_record_number', 
                     'insurance_id', 'credit_card', 'account_number']
        
        for field in pii_fields:
            if field in record_dict and record_dict[field]:
                return True
        return False
    
    def _extract_violation_types(self, record_dict):
        """
        Extract violation types from record for database storage
        
        Args:
            record_dict: Processed record dictionary
            
        Returns:
            list: List of violation type strings
        """
        violation_types = []
        
        if not record_dict.get('is_compliant', True):
            # Extract violation types from compliance details
            details = record_dict.get('compliance_details', '')
            if 'phi_exposure' in details:
                violation_types.append('phi_exposure')
            if 'missing_consent' in details:
                violation_types.append('missing_consent')
            if 'gdpr_violation' in details:
                violation_types.append('gdpr_violation')
            
            # Default if no specific types found
            if not violation_types:
                violation_types.append('compliance_violation')
        
        return violation_types
    
    def _ingest_file_to_kafka(self, filepath: str, topic: str, records_per_second: int = 50) -> bool:
        """
        Ingest file data to Kafka topic for real streaming processing
        
        Args:
            filepath: Path to CSV file
            topic: Kafka topic name
            records_per_second: Rate of data ingestion to simulate streaming
            
        Returns:
            bool: True if ingestion successful
        """
        try:
            print(f"📤 Ingesting {filepath} to Kafka topic '{topic}' at {records_per_second} records/sec")
            
            # Set up Kafka producer with optimized settings
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9093'],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                retries=3,
                retry_backoff_ms=100,
                batch_size=16384,  # Larger batch size for better throughput
                linger_ms=10,      # Small linger delay to ensure message delivery
                compression_type='snappy',  # Compression for better network efficiency
                acks='all',        # Wait for all replicas to acknowledge
                request_timeout_ms=30000,  # 30 second request timeout
                delivery_timeout_ms=60000  # 60 second delivery timeout
            )
            
            # Read file and send records to Kafka
            import pandas as pd
            df = pd.read_csv(filepath)
            total_records = len(df)
            
            print(f"   📊 Streaming {total_records} records to topic '{topic}'...")
            
            # Send records to Kafka as fast as possible for true streaming performance
            batch_size = 500  # Larger batch size for better throughput
            records_sent = 0
            
            for idx, record in df.iterrows():
                record_dict = record.to_dict()
                record_dict['_ingestion_timestamp'] = datetime.now().isoformat()
                record_dict['_record_index'] = idx
                
                # Send to Kafka (async for better performance)
                producer.send(topic, record_dict)
                records_sent += 1
                
                # Batch flush for better performance
                if records_sent % batch_size == 0:
                    producer.flush()  # Ensure messages are sent
                    print(f"   📤 Streamed {records_sent}/{total_records} records...")
                
                # No artificial sleep - let Kafka handle the throughput!
            
            # Flush and close producer
            producer.flush()
            producer.close()
            
            print(f"   ✅ Successfully streamed {total_records} records to '{topic}'")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to ingest to Kafka: {str(e)}")
            return False
    
    def _process_stream_real(self, processor: StormStreamProcessor, filepath: str, job_id: str, 
                            start_time: float, processed_folder: str, anonymization_config: AnonymizationConfig,
                            job_instance=None) -> Dict[str, Any]:
        """
        Process file through REAL Storm streaming with pure timing separation
        
        This method implements the research-optimized architecture for streaming:
        Pre-Processing → [Time.start() → Pure Stream Processing → Time.end()] → Post-Processing
        
        All database I/O operations are moved outside the timed processing sections
        to get pure streaming performance metrics for research evaluation.
        
        Args:
            processor: Storm stream processor instance
            filepath: Path to input file
            job_id: Unique job identifier
            start_time: Job start timestamp
            processed_folder: Output folder path
            anonymization_config: Configuration for anonymization parameters
            job_instance: Database job instance for tracking
            
        Returns:
            Dict containing processing metrics with clean timing separation
        """
        print(f"⚡ Starting REAL Storm stream processing with clean timing separation...")
        
        try:
            # PRE-PROCESSING: Setup and data ingestion (not timed)
            print("📥 Pre-Processing: Setup and Kafka ingestion...")
            pre_processing_start = time.time()
            
            # Update job status (pre-processing, not timed)
            if job_instance:
                job_instance.status = 'initializing'
                job_instance.progress = 10
        
            # Step 1: Set up Kafka topic for this job
            topic_name = f"temp-stream-{job_id}"
            
            # Create topic if it doesn't exist
            try:
                from kafka.admin import KafkaAdminClient, NewTopic
                admin_client = KafkaAdminClient(bootstrap_servers=['localhost:9093'])
                topic_list = [NewTopic(name=topic_name, num_partitions=3, replication_factor=1)]
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                print(f"   ✅ Created Kafka topic '{topic_name}'")
            except Exception as topic_error:
                print(f"   ℹ️  Topic '{topic_name}' may already exist or auto-created: {str(topic_error)}")
            
            # Step 2: Ingest file to Kafka stream (pre-processing, not timed)
            print(f"   📤 Ingesting file to Kafka topic '{topic_name}'...")
            ingestion_success = self._ingest_file_to_kafka(filepath, topic_name, records_per_second=5000)
            
            if not ingestion_success:
                raise Exception("Kafka ingestion failed - streaming infrastructure not available")
            
            # Small delay to ensure messages are fully committed to Kafka
            time.sleep(0.5)
            
            if job_instance:
                job_instance.progress = 30
            
            pre_processing_time = time.time() - pre_processing_start
            
            # PURE STREAM PROCESSING: Process records with clean timing
            print("⚡ Starting pure stream processing...")
            
            # Update job status before pure processing (not timed)
            if job_instance:
                job_instance.status = 'processing'
                job_instance.progress = 40
            
            # Configure processor for this topic
            processor.consumer_topics = [topic_name]
            
            # Infrastructure setup (not timed)
            processing_results = []
            processing_complete = threading.Event()
            processing_error = None
            pure_processing_time_actual = 0
            
            def stream_processing_thread():
                """Real-time Kafka consumer thread for streaming processing with anonymization"""
                nonlocal processing_error, pure_processing_time_actual
                try:
                    # Create a new consumer specifically for this topic
                    from kafka import KafkaConsumer
                    import json
                    
                    # Configure Kafka logging to reduce verbosity
                    import logging
                    logging.getLogger('kafka').setLevel(logging.WARNING)
                    
                    consumer = KafkaConsumer(
                        topic_name,
                        bootstrap_servers=['localhost:9093'],
                        auto_offset_reset='earliest',  # Start from beginning to catch our messages
                        consumer_timeout_ms=15000,  # 15 second timeout for reliable processing
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        group_id=f'stream-consumer-{job_id}',
                        enable_auto_commit=True,
                        session_timeout_ms=30000,  # 30 second session timeout
                        heartbeat_interval_ms=10000,  # 10 second heartbeat
                        max_poll_interval_ms=60000,  # 60 second max poll interval
                        fetch_min_bytes=1,  # Fetch messages immediately
                        fetch_max_wait_ms=500  # Wait max 500ms for more messages
                    )
                    
                    print(f"      📡 Consumer subscribed to topic '{topic_name}' for real-time streaming")
                    
                    # 🔥 PURE PROCESSING TIMING STARTS HERE
                    pure_processing_start = time.time()
                    
                    # Process stream with anonymization integration
                    messages_processed = 0
                    processing_start_time = time.time()
                    
                    for message in consumer:
                        try:
                            # PURE PROCESSING (timed section) - Real-time streaming with anonymization
                            record_start_time = time.time()
                            record = message.value
                            
                            # Apply anonymization using the engine
                            anonymized_record = processor.anonymization_engine.anonymize_record(
                                record, anonymization_config
                            )
                            
                            # Calculate individual record processing time
                            record_processing_time = time.time() - record_start_time
                            
                            # Add streaming metadata
                            anonymized_record['_stream_processed_at'] = datetime.now().isoformat()
                            anonymized_record['_stream_partition'] = message.partition
                            anonymized_record['_stream_offset'] = message.offset
                            anonymized_record['_processing_duration_ms'] = record_processing_time * 1000
                            
                            processing_results.append(anonymized_record)
                            messages_processed += 1
                            
                            # Progress updates every 100 records
                            if messages_processed % 100 == 0:
                                elapsed = time.time() - processing_start_time
                                rate = messages_processed / elapsed if elapsed > 0 else 0
                                print(f"      📊 Streamed {messages_processed} records ({rate:.0f} records/sec)")
                                
                        except Exception as e:
                            print(f"      ⚠️  Record processing error: {str(e)}")
                            continue
                    
                    # 🔥 PURE PROCESSING TIMING ENDS HERE
                    pure_processing_time_actual = time.time() - pure_processing_start
                    
                    # Consumer timeout reached - check if we got all messages
                    print(f"      ⏰ Consumer timeout reached - processed {messages_processed} records")
                    
                    consumer.close()
                    print(f"   ✅ Stream processing completed: {len(processing_results)} records processed")
                        
                except Exception as e:
                    processing_error = str(e)
                    print(f"   ❌ Stream processing error: {str(e)}")
                finally:
                    processing_complete.set()
            
            # Start processing thread
            thread = threading.Thread(target=stream_processing_thread)
            thread.daemon = True
            thread.start()
            
            # Wait for processing to complete (NOT counted in pure processing time)
            processing_complete.wait(timeout=15)  # 15 second timeout for reliable completion
            
            # Get the actual pure processing time from the thread
            pure_processing_time = pure_processing_time_actual
            
            if processing_error:
                raise Exception(f"Stream processing failed: {processing_error}")
            
            # POST-PROCESSING: Database operations and result storage (not timed)
            print("💾 Post-Processing: Database operations and result storage...")
            post_processing_start = time.time()
            
            # Update job status after pure processing (not timed)
            if job_instance:
                job_instance.status = 'storing_results'
                job_instance.progress = 80
            
            # Create output path and save CSV results
            output_filename = f"processed_{job_id}_{os.path.basename(filepath)}"
            output_path = os.path.join(processed_folder, output_filename)
            
            # Save streaming results to CSV
            if processing_results:
                import pandas as pd
                processed_df = pd.DataFrame(processing_results)
                processed_df.to_csv(output_path, index=False)
                print(f"   💾 Saved {len(processing_results)} streamed records to {output_path}")
            
            # Initialize database connection (post-processing, not timed)
            from database.postgres_connector import PostgresConnector
            db_connector = PostgresConnector()
            
            # Batch insert all processed records (post-processing, not timed)
            print(f"   Batch inserting {len(processing_results)} stream records to database...")
            if processing_results:
                file_id = job_instance.file_id if job_instance and hasattr(job_instance, 'file_id') else None
                # Use db_job_id for database foreign key constraint
                db_job_id = job_instance.db_job_id if job_instance and hasattr(job_instance, 'db_job_id') else job_id
                self._batch_insert_stream_records(db_connector, processing_results, db_job_id, file_id)
            
            # Calculate metrics with proper violation detection
            total_records = len(processing_results)
            violations_found = sum(1 for r in processing_results if not r.get('is_compliant', True))
            records_per_second = total_records / pure_processing_time if pure_processing_time > 0 else 0
            
            # Calculate average latency from processing durations
            if processing_results:
                processing_latencies = []
                for r in processing_results:
                    duration_ms = r.get('_processing_duration_ms', 0)
                    if duration_ms:
                        processing_latencies.append(duration_ms)
                avg_latency_ms = (sum(processing_latencies) / len(processing_latencies)) if processing_latencies else 0
            else:
                avg_latency_ms = 0
            
            # Update job completion status (post-processing, not timed)
            if job_instance:
                job_instance.status = 'completed'
                job_instance.progress = 100
                job_instance.end_time = datetime.now()
                job_instance.total_records = total_records
                job_instance.violation_count = violations_found
            
            post_processing_time = time.time() - post_processing_start
            
            # Complete metrics with timing separation
            complete_metrics = {
                'job_id': job_id,
                'pipeline_type': 'stream_pure',
                'file_path': filepath,
                'pre_processing_time': pre_processing_time,
                'pure_processing_time': pure_processing_time,
                'post_processing_time': post_processing_time,
                'total_execution_time': pre_processing_time + pure_processing_time + post_processing_time,
                'processing_metrics': {
                    'total_records': total_records,
                    'violations_found': violations_found,
                    'records_per_second': records_per_second,
                    'average_processing_time': avg_latency_ms,
                    'processing_approach': 'pure_stream'
                },
                'timing_separation': {
                    'pre_processing': f"{pre_processing_time:.3f}s",
                    'pure_processing': f"{pure_processing_time:.3f}s",
                    'post_processing': f"{post_processing_time:.3f}s"
                },
                'research_metrics': {
                    'records_per_second': records_per_second,
                    'violations_found': violations_found,
                    'average_latency_ms': avg_latency_ms,
                    'streaming_paradigm': 'pure_kafka_streaming'
                }
            }
            
            print(f"✅ Stream processing completed successfully!")
            print(f"   Pure processing time: {pure_processing_time:.3f}s")
            print(f"   Processing rate: {records_per_second:.0f} records/second")
            print(f"   Records processed: {total_records}")
            print(f"   Violations found: {violations_found}")
            print(f"   Average latency: {avg_latency_ms:.2f}ms")

            # Push metrics to Prometheus pushgateway for stream jobs
            try:
                from src.common.pushgateway_client import pushgateway_client
                metrics_to_push = {
                    'processing_time': pure_processing_time,
                    'throughput': records_per_second,
                    'total_records': total_records,
                    'violations': violations_found,
                    'violation_rate': violations_found/total_records if total_records > 0 else 0,
                    'records_per_second': records_per_second,
                    'anonymization_method': 'tokenization',  # Default for stream
                    'average_latency_ms': avg_latency_ms,
                    'pipeline_type': 'stream'
                }
                pushgateway_client.push_batch_metrics(metrics_to_push, 'stream_instance')
                print("📊 Stream metrics pushed to Prometheus pushgateway")
            except Exception as e:
                print(f"⚠️ Failed to push stream metrics to pushgateway: {e}")
            
            return complete_metrics
            
        except Exception as e:
            print(f"❌ Stream processing failed: {str(e)}")
            
            # Update job status on failure (not timed)
            if job_instance:
                job_instance.status = 'failed'
                job_instance.progress = 100
                job_instance.end_time = datetime.now()
                job_instance.error_message = str(e)
            
            raise e
    
    def _batch_insert_stream_records(self, db_connector, records, job_id, file_id=None):
        """
        Batch insert stream processing results to database
        
        This method handles the post-processing database operations for stream processing
        to maintain clean timing separation between processing and I/O operations.
        
        Args:
            db_connector: Database connector instance
            records: List of processed stream records
            job_id: Job identifier for tracking
            file_id: File identifier for the records (required for database)
        """
        print(f"   Preparing batch insert for {len(records)} stream records...")
        
        # Prepare all records for batch insertion
        batch_records = []
        violations_batch = []
        
        for idx, record in enumerate(records):
            try:
                # Prepare record for database insertion
                record_data = {
                    'job_id': job_id,
                    'record_id': f"{job_id}_stream_{idx}",
                    'original_data': record,
                    'processed_data': record,
                    'has_pii': self._has_pii_data(record),
                    'has_violations': not record.get('stream_compliant', True),
                    'violation_types': [v.get('type', 'unknown') for v in record.get('stream_violations', [])],
                    'file_id': file_id,  # Use the provided file_id
                }
                
                batch_records.append(record_data)
                
                # Collect violations for batch insertion
                if record.get('has_violations', False):
                    for violation in record.get('stream_violations', []):
                        violations_batch.append({
                            'file_id': file_id,
                            'record_id': None,  # Will be set after records are inserted
                            'violation_type': violation.get('type', 'compliance_violation'),
                            'violation_category': 'data_exposure',
                            'severity': violation.get('severity', 'medium'),
                            'description': violation.get('description', 'Stream processing violation detected'),
                            'details': violation.get('description', '')
                        })
                    
            except Exception as e:
                print(f"      ⚠️ Error preparing stream record {idx}: {str(e)}")
                continue
        
        # Perform batch database operations
        try:
            # Single batch insert for all records
            if batch_records:
                print(f"   Executing batch insert for {len(batch_records)} stream records...")
                db_connector.batch_insert_records(batch_records)
                
            # Single batch insert for all violations
            if violations_batch:
                print(f"   Executing batch insert for {len(violations_batch)} stream violations...")
                db_connector.batch_insert_violations(violations_batch)
                
            print(f"   ✅ Stream batch insert completed successfully")
            
        except Exception as e:
            print(f"   ❌ Stream batch insert failed: {str(e)}")
            # Don't raise here - we don't want database issues to fail the entire processing
    

    
    def _process_hybrid_real(self, processor: FlinkHybridProcessor, filepath: str, job_id: str,
                            start_time: float, processed_folder: str, anonymization_config: AnonymizationConfig,
                            job_instance=None) -> Dict[str, Any]:
        """Process file through REAL Flink hybrid processing with Kafka ingestion and anonymization"""
        
        print(f"🧠 Starting REAL Flink hybrid processing for job {job_id}")
        
        if job_instance:
            job_instance.progress = 10
            job_instance.status = 'processing'
        
        try:
            # Step 1: Set up Kafka topic for this job
            topic_name = f"temp-hybrid-{job_id}"
            
            # Create topic if it doesn't exist
            try:
                from kafka.admin import KafkaAdminClient, NewTopic
                admin_client = KafkaAdminClient(bootstrap_servers=['localhost:9093'])
                topic_list = [NewTopic(name=topic_name, num_partitions=3, replication_factor=1)]
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                print(f"   ✅ Created Kafka topic '{topic_name}'")
            except Exception as topic_error:
                print(f"   ℹ️  Topic '{topic_name}' may already exist or auto-created: {str(topic_error)}")
            
            if job_instance:
                job_instance.progress = 20
            
            # Step 2: Ingest file to Kafka stream
            print(f"   📤 Step 1: Ingesting file to Kafka topic '{topic_name}'...")
            ingestion_success = self._ingest_file_to_kafka(filepath, topic_name, records_per_second=5000)
            
            if not ingestion_success:
                raise Exception("Kafka ingestion failed - hybrid processing infrastructure not available")
            
            # Small delay to ensure messages are fully committed to Kafka
            time.sleep(0.5)
            
            if job_instance:
                job_instance.progress = 40
            
            # Step 3: Start real hybrid processing
            print(f"   🧠 Step 2: Starting real Flink hybrid processing with intelligent routing...")
            
            routing_decisions = []
            batch_routed = 0
            stream_routed = 0
            processing_results = []
            processing_complete = threading.Event()
            processing_error = None
            
            # 🔥 PURE PROCESSING TIMING STARTS HERE
            pure_processing_start = time.time()
            
            def hybrid_processing_thread():
                """Real-time Kafka consumer with intelligent routing and anonymization"""
                nonlocal processing_error, routing_decisions, batch_routed, stream_routed
                try:
                    # Configure processor for this topic
                    processor.consumer_topics = [topic_name]
                    
                    # Create a new consumer specifically for this topic
                    from kafka import KafkaConsumer
                    import json
                    
                    consumer = KafkaConsumer(
                        topic_name,
                        bootstrap_servers=['localhost:9093'],
                        auto_offset_reset='earliest',
                        consumer_timeout_ms=15000,  # 15 second timeout for reliable processing
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        group_id=f'hybrid-consumer-{job_id}',
                        enable_auto_commit=True,
                        session_timeout_ms=30000,  # 30 second session timeout
                        heartbeat_interval_ms=10000,  # 10 second heartbeat
                        max_poll_interval_ms=60000,  # 60 second max poll interval
                        fetch_min_bytes=1,  # Fetch messages immediately
                        fetch_max_wait_ms=500  # Wait max 500ms for more messages
                    )
                    
                    print(f"      🎯 Hybrid consumer subscribed to topic '{topic_name}' for intelligent routing")
                    
                    # Process hybrid stream with intelligent routing and anonymization
                    processing_start_time = time.time()
                    
                    for message in consumer:
                        try:
                            record = message.value
                            
                            # Real hybrid processing: analyze and route FIRST
                            characteristics = processor.analyze_data_characteristics(record)
                            decision = processor.make_routing_decision(record, characteristics)
                            routing_decisions.append(decision)
                            
                            # Apply anonymization using the engine AFTER routing decision
                            anonymized_record = processor.anonymization_engine.anonymize_record(
                                record, anonymization_config
                            )
                            
                            # Process based on routing decision with anonymized data
                            if decision['route'] == 'batch':
                                batch_routed += 1
                                anonymized_record['processed_via'] = 'hybrid_batch'
                                anonymized_record['routing_decision'] = decision
                                anonymized_record['batch_priority'] = decision.get('priority', 'medium')
                                
                            elif decision['route'] == 'stream':
                                stream_routed += 1
                                stream_start = time.time()
                                # Add real-time processing metadata
                                anonymized_record['processed_via'] = 'hybrid_stream'
                                anonymized_record['routing_decision'] = decision
                                anonymized_record['stream_latency_ms'] = (time.time() - stream_start) * 1000
                                anonymized_record['stream_priority'] = decision.get('priority', 'high')
                            
                            # Add hybrid metadata
                            anonymized_record['_hybrid_processed_at'] = datetime.now().isoformat()
                            anonymized_record['_hybrid_partition'] = message.partition
                            anonymized_record['_hybrid_offset'] = message.offset
                            # Note: Individual record processing time is already captured in stream_latency_ms for stream records
                            
                            processing_results.append(anonymized_record)
                            
                            if len(processing_results) % 50 == 0:
                                elapsed = time.time() - processing_start_time
                                rate = len(processing_results) / elapsed if elapsed > 0 else 0
                                print(f"      🔄 Processed {len(processing_results)} records "
                                      f"(B:{batch_routed}, S:{stream_routed}) ({rate:.0f} records/sec)")
                                
                        except Exception as e:
                            print(f"      ⚠️  Record processing error: {str(e)}")
                            continue
                    
                    consumer.close()
                    print(f"   ✅ Hybrid processing completed: {len(processing_results)} records")
                    print(f"      🎯 Routing: {batch_routed} → batch, {stream_routed} → stream")
                        
                except Exception as e:
                    processing_error = str(e)
                    print(f"   ❌ Hybrid processing error: {str(e)}")
                finally:
                    processing_complete.set()
            
            # Start processing thread
            thread = threading.Thread(target=hybrid_processing_thread)
            thread.daemon = True
            thread.start()
            
            if job_instance:
                job_instance.progress = 60
            
            # Wait for processing to complete
            processing_complete.wait(timeout=30)  # 30 second timeout for hybrid processing
            
            # 🔥 PURE PROCESSING TIMING ENDS HERE
            pure_processing_time = time.time() - pure_processing_start
            
            if processing_error:
                raise Exception(f"Hybrid processing failed: {processing_error}")
            
            # POST-PROCESSING: Database operations and result storage (not timed)
            print("💾 Post-Processing: Database operations and result storage...")
            post_processing_start = time.time()
            
            if job_instance:
                job_instance.status = 'storing_results'
                job_instance.progress = 80
            
            # Create output path and save CSV results
            output_filename = f"processed_{job_id}_{os.path.basename(filepath)}"
            output_path = os.path.join(processed_folder, output_filename)
            
            # Calculate hybrid metrics
            total_records = len(processing_results)
            violations_found = sum(1 for r in processing_results if not r.get('is_compliant', True))
            
            # Analyze routing patterns
            routing_reasons = [d['reason'] for d in routing_decisions] if routing_decisions else []
            routing_reason_counts = {reason: routing_reasons.count(reason) for reason in set(routing_reasons)}
            
            # Save hybrid results to CSV
            if processing_results:
                import pandas as pd
                processed_df = pd.DataFrame(processing_results)
                processed_df.to_csv(output_path, index=False)
                print(f"   💾 Saved {total_records} hybrid records to {output_path}")
            
            # Initialize database connection (post-processing, not timed)
            from database.postgres_connector import PostgresConnector
            db_connector = PostgresConnector()
            
            # Batch insert all processed records (post-processing, not timed)
            print(f"   Batch inserting {total_records} hybrid records to database...")
            if processing_results:
                file_id = job_instance.file_id if job_instance and hasattr(job_instance, 'file_id') else None
                # Use db_job_id for database foreign key constraint
                db_job_id = job_instance.db_job_id if job_instance and hasattr(job_instance, 'db_job_id') else job_id
                self._batch_insert_records(db_connector, processing_results, db_job_id, file_id)
            
            # Calculate metrics from processing results
            records_per_second = total_records / pure_processing_time if pure_processing_time > 0 else 0
            
            # Calculate average latency from stream-routed records
            stream_latencies = [r.get('stream_latency_ms', 0) for r in processing_results if r.get('stream_latency_ms')]
            avg_latency_ms = sum(stream_latencies) / len(stream_latencies) if stream_latencies else 0
            
            # Update job completion status (post-processing, not timed)
            if job_instance:
                job_instance.status = 'completed'
                job_instance.progress = 100
                job_instance.end_time = datetime.now()
                job_instance.total_records = total_records
                job_instance.violation_count = violations_found
                job_instance.output_path = output_path
            
            post_processing_time = time.time() - post_processing_start
            
            # Complete metrics with timing separation and routing analytics
            complete_metrics = {
                'job_id': job_id,
                'pipeline_type': 'hybrid',
                'file_path': filepath,
                'output_path': output_path,
                'pure_processing_time': pure_processing_time,
                'post_processing_time': post_processing_time,
                'total_execution_time': pure_processing_time + post_processing_time,
                'processing_metrics': {
                    'total_records': total_records,
                    'violations_found': violations_found,
                    'records_per_second': records_per_second,
                    'routing_stats': {
                        'batch_routed': batch_routed,
                        'stream_routed': stream_routed,
                        'batch_percentage': batch_routed / total_records * 100 if total_records > 0 else 0,
                        'stream_percentage': stream_routed / total_records * 100 if total_records > 0 else 0,
                        'routing_reasons': routing_reason_counts
                    },
                    'hybrid_method': 'real_kafka_intelligent_routing',
                    'anonymization_method': anonymization_config.method.value if anonymization_config else 'none'
                },
                'research_metrics': {
                    'records_per_second': records_per_second,
                    'violations_found': violations_found,
                    'average_latency_ms': avg_latency_ms,
                    'routing_intelligence': True,
                    'real_time_processing': True
                }
            }
            
            # Store metrics for research evaluation
            self.metrics['hybrid'].append(complete_metrics)
            
            print(f"✅ Hybrid processing completed successfully!")
            print(f"   Pure processing time: {pure_processing_time:.3f}s")
            print(f"   Processing rate: {records_per_second:.0f} records/second")
            print(f"   Records processed: {total_records}")
            print(f"   Violations found: {violations_found}")
            print(f"   Average latency: {avg_latency_ms:.2f}ms")
            print(f"   🎯 Routing: {batch_routed} → batch, {stream_routed} → stream")

            # Push metrics to Prometheus pushgateway for hybrid jobs
            try:
                from src.common.pushgateway_client import pushgateway_client
                metrics_to_push = {
                    'processing_time': pure_processing_time,
                    'throughput': records_per_second,
                    'total_records': total_records,
                    'violations': violations_found,
                    'violation_rate': violations_found/total_records if total_records > 0 else 0,
                    'records_per_second': records_per_second,
                    'anonymization_method': anonymization_config.method.value if anonymization_config else 'differential_privacy',
                    'average_latency_ms': avg_latency_ms,
                    'pipeline_type': 'hybrid',
                    'batch_routed': batch_routed,
                    'stream_routed': stream_routed
                }
                pushgateway_client.push_batch_metrics(metrics_to_push, 'hybrid_instance')
                print("📊 Hybrid metrics pushed to Prometheus pushgateway")
            except Exception as e:
                print(f"⚠️ Failed to push hybrid metrics to pushgateway: {e}")
            
            return complete_metrics
            
        except Exception as e:
            print(f"❌ REAL hybrid processing failed for job {job_id}: {str(e)}")
            if job_instance:
                job_instance.status = 'failed'
                job_instance.error = f"Real hybrid processing error: {str(e)}"
            raise
    

    
    def get_research_metrics(self, pipeline_type: Optional[str] = None) -> Dict[str, Any]:
        """Get collected metrics for research evaluation"""
        if pipeline_type:
            return {
                'pipeline_type': pipeline_type,
                'metrics': self.metrics.get(pipeline_type, []),
                'total_jobs': len(self.metrics.get(pipeline_type, [])),
                'collected_at': datetime.now().isoformat()
            }
        else:
            return {
                'all_metrics': self.metrics,
                'summary': {
                    'batch_jobs': len(self.metrics['batch']),
                    'stream_jobs': len(self.metrics['stream']),
                    'hybrid_jobs': len(self.metrics['hybrid']),
                    'total_jobs': sum(len(m) for m in self.metrics.values())
                },
                'collected_at': datetime.now().isoformat()
            }


# Global orchestrator instance
orchestrator = PipelineOrchestrator()

# ================================
# OPTIMIZED STREAMING ARCHITECTURE
# ================================

class OptimizedStreamManager:
    """
    Manages persistent Kafka consumers and static topics for high-performance streaming
    
    This eliminates the overhead of:
    - Dynamic topic creation per job
    - Consumer startup delays
    - Polling timeouts
    - Topic metadata propagation
    """
    
    def __init__(self):
        self.static_topics = {
            'healthcare-stream': {'partitions': 3, 'replicas': 1},
            'financial-stream': {'partitions': 3, 'replicas': 1}, 
            'hybrid-input': {'partitions': 6, 'replicas': 1},
            'processed-output': {'partitions': 6, 'replicas': 1}
        }
        self.persistent_consumers = {}
        self.running = False
        
    def initialize_static_topics(self):
        """Create static topics at application startup"""
        try:
            from kafka.admin import KafkaAdminClient, NewTopic
            admin_client = KafkaAdminClient(bootstrap_servers=['localhost:9093'])
            
            # Create all static topics at once
            topic_list = []
            for topic_name, config in self.static_topics.items():
                topic_list.append(NewTopic(
                    name=topic_name,
                    num_partitions=config['partitions'],
                    replication_factor=config['replicas']
                ))
            
            # Create topics (will skip existing ones)
            try:
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                print("✅ Static topics ready")
            except Exception as e:
                print("ℹ️  Static topics already exist")
                
        except Exception as e:
            print("❌ Failed to initialize topics")
            
    def start_persistent_consumers(self):
        """Start persistent consumers that stay alive throughout app lifecycle"""
        self.running = True
        
        # Create persistent consumers for each topic
        for topic_name in self.static_topics:
            consumer_thread = threading.Thread(
                target=self._run_persistent_consumer,
                args=(topic_name,),
                daemon=True
            )
            consumer_thread.start()
            # Reduced verbosity - only show summary
        
        print(f"🔄 Started {len(self.static_topics)} persistent consumers")
    
    def _run_persistent_consumer(self, topic_name):
        """Run a persistent consumer that processes messages when jobs are active"""
        from kafka import KafkaConsumer
        import json
        
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=['localhost:9093'],
            auto_offset_reset='latest',  # Only process new messages
            consumer_timeout_ms=500,     # Very short timeout for responsiveness
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            group_id=f'persistent-{topic_name}',
            enable_auto_commit=True
        )
        
        # Reduced verbosity - no individual consumer ready messages
        
        while self.running:
            try:
                for message in consumer:
                    if not self.running:
                        break
                    
                    # Process message immediately without polling delays
                    self._process_message_immediately(message, topic_name)
                    
            except Exception as e:
                if self.running:  # Only log if not shutting down
                    # Reduced verbosity - only log critical errors
                    time.sleep(1)  # Brief pause before retry
        
        consumer.close()
        # Reduced verbosity - no individual stop messages
    
    def _process_message_immediately(self, message, topic_name):
        """Process message immediately without delays"""
        # Route to appropriate processor based on topic
        record = message.value
        
        # Add message metadata
        record['_kafka_topic'] = topic_name
        record['_kafka_partition'] = message.partition
        record['_kafka_offset'] = message.offset
        record['_received_at'] = time.time()
        
        # Store in memory buffer for active jobs to pick up
        # This eliminates polling delays
        self._notify_active_jobs(record, topic_name)
    
    def _notify_active_jobs(self, record, topic_name):
        """Notify active jobs that a new record is available"""
        # Implementation would notify waiting jobs
        # For now, this is a placeholder for the optimized architecture
        pass
    
    def publish_to_stream(self, records, topic_name):
        """Optimized batch publishing to static topics"""
        from kafka import KafkaProducer
        import json
        
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9093'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            batch_size=16384,      # Batch messages for efficiency
            linger_ms=0,           # No batching delay for immediate processing
            compression_type='gzip' # Compress for better throughput
        )
        
        # Batch publish all records
        futures = []
        for record in records:
            future = producer.send(topic_name, record)
            futures.append(future)
        
        # Wait for all messages to be sent
        producer.flush()
        producer.close()
        
        return len(records)
    
    def stop_all_consumers(self):
        """Gracefully stop all persistent consumers"""
        self.running = False
        print("🛑 Stopping all persistent consumers...")

# Global stream manager instance
stream_manager = OptimizedStreamManager()

# ================================
# END OPTIMIZED ARCHITECTURE  
# ================================

# ================================
# COMMENTED OUT PIPELINE ROUTES - FOR TESTING
# ================================

# @bp.route('/process', methods=['POST'])
# def process_file():
#     """Process uploaded file through specified pipeline with anonymization parameters"""
#     try:
#         from app import processing_jobs, db_connector
#         
#         data = request.json
#         job_id = data.get('job_id')
#         filepath = data.get('filepath')
#         pipeline_type = data.get('pipeline_type', 'batch')
#         
#         # Extract anonymization parameters
#         anonymization_technique = data.get('anonymization_technique', 'k_anonymity')
#         k_value = data.get('k_value', 5)
#         epsilon = data.get('epsilon', 1.0)
#         key_size = data.get('key_size', 256)
#         
#         if not job_id or job_id not in processing_jobs:
#             return jsonify({'error': 'Invalid job ID'}), 400
#         
#         if not filepath or not os.path.exists(filepath):
#             return jsonify({'error': 'File not found'}), 400
#         
#         job = processing_jobs[job_id]
#         
#         # Create anonymization configuration based on technique
#         try:
#             if anonymization_technique == 'k_anonymity':
#                 anonymization_config = AnonymizationConfig(
#                     method=AnonymizationMethod.K_ANONYMITY,
#                     k_value=int(k_value)
#                 )
#             elif anonymization_technique == 'differential_privacy':
#                 anonymization_config = AnonymizationConfig(
#                     method=AnonymizationMethod.DIFFERENTIAL_PRIVACY,
#                     epsilon=float(epsilon)
#                 )
#             elif anonymization_technique == 'tokenization':
#                 anonymization_config = AnonymizationConfig(
#                     method=AnonymizationMethod.TOKENIZATION,
#                     key_length=int(key_size)
#                 )
#             else:
#                 return jsonify({'error': f'Invalid anonymization technique: {anonymization_technique}'}), 400
#         except (ValueError, TypeError) as param_error:
#             return jsonify({'error': f'Invalid anonymization parameters: {str(param_error)}'}), 400
#         
#         # Process through specified pipeline with anonymization config
#         metrics = orchestrator.process_file(job_id, filepath, pipeline_type, 
#                                           current_app.config['PROCESSED_FOLDER'], 
#                                           anonymization_config, job)
#         
#         return jsonify({
#             'status': 'success',
#             'message': f'File processed through {pipeline_type} pipeline with {anonymization_technique}',
#             'metrics': metrics,
#             'anonymization_config': {
#                 'technique': anonymization_technique,
#                 'parameters': {
#                     'k_value': k_value if anonymization_technique == 'k_anonymity' else None,
#                     'epsilon': epsilon if anonymization_technique == 'differential_privacy' else None,
#                     'key_size': key_size if anonymization_technique == 'tokenization' else None
#                 }
#             }
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @bp.route('/metrics', methods=['GET'])
# def get_pipeline_metrics():
#     """Get research evaluation metrics"""
#     try:
#         pipeline_type = request.args.get('pipeline_type')
#         metrics = orchestrator.get_research_metrics(pipeline_type)
#         
#         return jsonify({
#             'status': 'success',
#             'data': metrics
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @bp.route('/metrics/comparison', methods=['GET'])
# def get_comparative_metrics():
#     """Get comparative metrics for research evaluation"""
#     try:
#         all_metrics = orchestrator.get_research_metrics()
#         
#         # Calculate comparative statistics
#         comparison = {
#             'throughput_comparison': {},
#             'latency_comparison': {},
#             'violation_detection_comparison': {}
#         }
#         
#         for pipeline_type, metrics_list in all_metrics['all_metrics'].items():
#             if metrics_list:
#                 throughputs = [m['throughput_records_per_second'] for m in metrics_list]
#                 violation_rates = [m['violation_rate'] for m in metrics_list]
#                 
#                 comparison['throughput_comparison'][pipeline_type] = {
#                     'average': sum(throughputs) / len(throughputs),
#                     'max': max(throughputs),
#                     'min': min(throughputs)
#                 }
#                 
#                 comparison['violation_detection_comparison'][pipeline_type] = {
#                     'average_violation_rate': sum(violation_rates) / len(violation_rates),
#                     'total_jobs': len(metrics_list)
#                 }
#                 
#                 # Add latency metrics for stream and hybrid
#                 if pipeline_type in ['stream', 'hybrid']:
#                     latencies = [m.get('average_latency_seconds', 0) for m in metrics_list]
#                     comparison['latency_comparison'][pipeline_type] = {
#                         'average_latency': sum(latencies) / len(latencies),
#                         'max_latency': max(latencies),
#                         'min_latency': min(latencies)
#                     }
#         
#         return jsonify({
#             'status': 'success',
#             'comparison': comparison,
#             'generated_at': datetime.now().isoformat()
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @bp.route('/metrics/rq2-anonymization', methods=['GET'])
# def get_rq2_anonymization_metrics():
#     """
#     Get comprehensive anonymization metrics for RQ2 research analysis
#     
#     This endpoint aggregates anonymization performance data across all pipelines
#     and techniques for comprehensive research evaluation and comparison.
#     """
#     try:
#         from app import db_connector
#         
#         # Query database for recent processing jobs with anonymization data
#         jobs_query = """
#         SELECT 
#             dpj.job_id,
#             dpj.file_id,
#             dpj.pipeline_type,
#             dpj.status,
#             dpj.start_time,
#             dpj.end_time,
#             dpj.records_processed,
#             dpj.results,
#             df.filename,
#             df.file_size,
#             COUNT(dcv.id) as violations_count
#         FROM data_processing_jobs dpj
#         LEFT JOIN data_files df ON dpj.file_id = df.id
#         LEFT JOIN data_compliance_violations dcv ON df.id = dcv.file_id
#         WHERE dpj.status = 'completed'
#         AND dpj.start_time >= NOW() - INTERVAL '24 HOURS'
#         GROUP BY dpj.job_id, dpj.file_id, dpj.pipeline_type, dpj.status, 
#                  dpj.start_time, dpj.end_time, dpj.records_processed, 
#                  dpj.results, df.filename, df.file_size
#         ORDER BY dpj.start_time DESC
#         """
#         
#         jobs_result = db_connector.execute_query(jobs_query)
#         
#         # Aggregate anonymization metrics by technique and pipeline
#         anonymization_analysis = {
#             'techniques_comparison': {
#                 'k_anonymity': {'jobs': 0, 'avg_processing_time': 0, 'avg_throughput': 0, 'privacy_levels': []},
#                 'differential_privacy': {'jobs': 0, 'avg_processing_time': 0, 'avg_throughput': 0, 'privacy_levels': []},
#                 'tokenization': {'jobs': 0, 'avg_processing_time': 0, 'avg_throughput': 0, 'privacy_levels': []}
#             },
#             'pipeline_performance': {
#                 'batch': {'anonymization_overhead': [], 'violation_detection_rate': []},
#                 'stream': {'anonymization_overhead': [], 'violation_detection_rate': []}, 
#                 'hybrid': {'anonymization_overhead': [], 'violation_detection_rate': []}
#             },
#             'parameter_analysis': {
#                 'k_values': {},        # k-anonymity parameter analysis
#                 'epsilon_values': {},  # differential privacy parameter analysis
#                 'key_sizes': {}        # tokenization parameter analysis
#             },
#             'quality_metrics': {
#                 'information_loss_by_technique': {},
#                 'utility_preservation_by_pipeline': {},
#                 'privacy_level_distribution': {}
#             }
#         }
#         
#         # Process each job's anonymization metrics
#         for job in jobs_result:
#             if job.get('results'):
#                 try:
#                     job_results = json.loads(job['results']) if isinstance(job['results'], str) else job['results']
#                     
#                     # Extract anonymization configuration if present
#                     anon_config = job_results.get('anonymization_config', {})
#                     technique = anon_config.get('technique', 'unknown')
#                     parameters = anon_config.get('parameters', {})
#                     
#                     # Calculate key metrics
#                     processing_time = (job['end_time'] - job['start_time']).total_seconds() if job['end_time'] else 0
#                     throughput = job['records_processed'] / processing_time if processing_time > 0 else 0
#                     violation_rate = job['violations_count'] / job['records_processed'] if job['records_processed'] > 0 else 0
#                     
#                     # Update technique-specific metrics
#                     if technique in anonymization_analysis['techniques_comparison']:
#                         tech_metrics = anonymization_analysis['techniques_comparison'][technique]
#                         tech_metrics['jobs'] += 1
#                         tech_metrics['avg_processing_time'] += processing_time
#                         tech_metrics['avg_throughput'] += throughput
#                         
#                         # Calculate privacy level based on technique and parameters
#                         privacy_level = 0.5  # Default
#                         if technique == 'k_anonymity' and parameters.get('k_value'):
#                             privacy_level = min(1.0, parameters['k_value'] / 20.0)
#                         elif technique == 'differential_privacy' and parameters.get('epsilon'):
#                             privacy_level = max(0.1, 1.0 - parameters['epsilon'])
#                         elif technique == 'tokenization':
#                             privacy_level = 0.7
#                         
#                         tech_metrics['privacy_levels'].append(privacy_level)
#                     
#                     # Update pipeline-specific metrics
#                     pipeline = job['pipeline_type']
#                     if pipeline in anonymization_analysis['pipeline_performance']:
#                         pipe_metrics = anonymization_analysis['pipeline_performance'][pipeline]
#                         pipe_metrics['violation_detection_rate'].append(violation_rate)
#                         
#                         # Estimate anonymization overhead (simplified)
#                         base_processing_rate = 1000  # records/second baseline
#                         overhead = max(0, (base_processing_rate - throughput) / base_processing_rate)
#                         pipe_metrics['anonymization_overhead'].append(overhead)
#                     
#                     # Parameter-specific analysis
#                     if technique == 'k_anonymity' and parameters.get('k_value'):
#                         k_val = str(parameters['k_value'])
#                         if k_val not in anonymization_analysis['parameter_analysis']['k_values']:
#                             anonymization_analysis['parameter_analysis']['k_values'][k_val] = []
#                         anonymization_analysis['parameter_analysis']['k_values'][k_val].append({
#                             'throughput': throughput,
#                             'privacy_level': privacy_level,
#                             'processing_time': processing_time
#                         })
#                     
#                 except (json.JSONDecodeError, KeyError) as e:
#                     print(f"Error processing job results: {e}")
#                     continue
#         
#         # Calculate averages and statistical summaries
#         for technique, metrics in anonymization_analysis['techniques_comparison'].items():
#             if metrics['jobs'] > 0:
#                 metrics['avg_processing_time'] /= metrics['jobs']
#                 metrics['avg_throughput'] /= metrics['jobs']
#                 metrics['avg_privacy_level'] = sum(metrics['privacy_levels']) / len(metrics['privacy_levels']) if metrics['privacy_levels'] else 0
#                 metrics['privacy_std'] = np.std(metrics['privacy_levels']) if len(metrics['privacy_levels']) > 1 else 0
#         
#         # Pipeline performance summaries
#         for pipeline, metrics in anonymization_analysis['pipeline_performance'].items():
#             if metrics['violation_detection_rate']:
#                 metrics['avg_violation_detection'] = sum(metrics['violation_detection_rate']) / len(metrics['violation_detection_rate'])
#                 metrics['avg_anonymization_overhead'] = sum(metrics['anonymization_overhead']) / len(metrics['anonymization_overhead']) if metrics['anonymization_overhead'] else 0
#         
#         # Add research insights
#         research_insights = {
#             'best_privacy_technique': max(anonymization_analysis['techniques_comparison'], 
#                                         key=lambda x: anonymization_analysis['techniques_comparison'][x].get('avg_privacy_level', 0)),
#             'fastest_pipeline': max(anonymization_analysis['pipeline_performance'],
#                                   key=lambda x: len(anonymization_analysis['pipeline_performance'][x]['violation_detection_rate'])),
#             'optimal_parameters': {
#                 'k_anonymity': 'k=5 (balanced privacy-utility)',
#                 'differential_privacy': 'ε=1.0 (moderate privacy)',
#                 'tokenization': '256-bit keys (standard security)'
#             },
#             'performance_ranking': sorted(
#                 anonymization_analysis['techniques_comparison'].items(),
#                 key=lambda x: x[1].get('avg_throughput', 0),
#                 reverse=True
#             )
#         }
#         
#         return jsonify({
#             'status': 'success',
#             'anonymization_analysis': anonymization_analysis,
#             'research_insights': research_insights,
#             'data_collection_period': '24 hours',
#             'total_jobs_analyzed': sum(metrics['jobs'] for metrics in anonymization_analysis['techniques_comparison'].values()),
#             'generated_at': datetime.now().isoformat()
#         })
#         
#     except Exception as e:
#         return jsonify({'error': f'RQ2 metrics collection failed: {str(e)}'}), 500

# @bp.route('/processors/status', methods=['GET'])
# def get_processor_status():
#     """Get status of all pipeline processors"""
#     try:
#         status = {}
#         
#         for pipeline_type in ['batch', 'stream', 'hybrid']:
#             try:
#                 processor = orchestrator.get_processor(pipeline_type)
#                 status[pipeline_type] = {
#                     'available': True,
#                     'type': type(processor).__name__,
#                     'initialized': True
#                 }
#             except Exception as e:
#                 status[pipeline_type] = {
#                     'available': False,
#                     'error': str(e),
#                     'initialized': False
#                 }
#         
#         return jsonify({
#             'status': 'success',
#             'processors': status
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500 

# @bp.route('/test/real-vs-simulated', methods=['POST'])
# def test_real_vs_simulated():
#     """Test real vs simulated processing for research evaluation"""
#     try:
#         data = request.json
#         filepath = data.get('filepath')
#         
#         if not filepath or not os.path.exists(filepath):
#             return jsonify({'error': 'File not found'}), 400
#         
#         print("🧪 Testing REAL vs SIMULATED processing...")
#         
#         results = {}
#         
#         # Test BATCH (always real)
#         print("\n🔄 Testing BATCH (real Spark)...")
#         try:
#             batch_processor = orchestrator.get_processor('batch')
#             job_id = str(uuid.uuid4())[:8]
#             start_time = time.time()
#             
#             # Create default anonymization config for testing
#             default_anon_config = AnonymizationConfig(method=AnonymizationMethod.K_ANONYMITY, k_value=5)
#             batch_metrics = orchestrator._process_batch(batch_processor, filepath, f"batch-test-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'], default_anon_config)
#             results['batch'] = {
#                 'status': 'success',
#                 'mode': 'real_spark',
#                 'metrics': batch_metrics
#             }
#         except Exception as e:
#             results['batch'] = {
#                 'status': 'failed',
#                 'mode': 'real_spark',
#                 'error': str(e)
#             }
#         
#         # Test STREAM (real vs simulated)
#         print("\n🔄 Testing STREAM (real Kafka vs simulated)...")
#         stream_processor = orchestrator.get_processor('stream')
#         
#         # Try real streaming
#         try:
#             job_id = str(uuid.uuid4())[:8]
#             start_time = time.time()
#             
#             real_stream_metrics = orchestrator._process_stream_real(stream_processor, filepath, f"stream-real-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'], AnonymizationConfig())
#             results['stream_real'] = {
#                 'status': 'success',
#                 'mode': 'real_kafka_streaming',
#                 'metrics': real_stream_metrics
#             }
#         except Exception as e:
#             results['stream_real'] = {
#                 'status': 'failed',
#                 'mode': 'real_kafka_streaming',
#                 'error': str(e)
#             }
#         
#         # Note: Simulated streaming removed - only real Kafka streaming supported
#         
#         # Test HYBRID (real vs simulated)
#         print("\n🔄 Testing HYBRID (real Kafka routing vs simulated)...")
#         hybrid_processor = orchestrator.get_processor('hybrid')
#         
#         # Try real hybrid
#         try:
#             job_id = str(uuid.uuid4())[:8]
#             start_time = time.time()
#             
#             real_hybrid_metrics = orchestrator._process_hybrid_real(hybrid_processor, filepath, f"hybrid-real-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'], AnonymizationConfig())
#             results['hybrid_real'] = {
#                 'status': 'success',
#                 'mode': 'real_kafka_intelligent_routing',
#                 'metrics': real_hybrid_metrics
#             }
#         except Exception as e:
#             results['hybrid_real'] = {
#                 'status': 'failed',
#                 'mode': 'real_kafka_intelligent_routing',
#                 'error': str(e)
#             }
#         
#         # Note: Simulated hybrid processing removed - only real Kafka routing supported
#         
#         # Generate comparison report
#         comparison = {
#             'test_file': filepath,
#             'timestamp': datetime.now().isoformat(),
#             'results': results,
#             'summary': {
#                 'batch_real_available': results['batch']['status'] == 'success',
#                 'stream_real_available': results['stream_real']['status'] == 'success',
#                 'stream_simulated_available': results['stream_simulated']['status'] == 'success',
#                 'hybrid_real_available': results['hybrid_real']['status'] == 'success',
#                 'hybrid_simulated_available': results['hybrid_simulated']['status'] == 'success'
#             }
#         }
#         
#         # Performance comparison if both modes available
#         if (results['stream_real']['status'] == 'success' and 
#             results['stream_simulated']['status'] == 'success'):
#             
#             real_throughput = results['stream_real']['metrics']['throughput_records_per_second']
#             sim_throughput = results['stream_simulated']['metrics']['throughput_records_per_second']
#             
#             comparison['performance_comparison'] = {
#                 'stream_real_throughput': real_throughput,
#                 'stream_simulated_throughput': sim_throughput,
#                 'throughput_difference_pct': ((real_throughput - sim_throughput) / sim_throughput * 100) if sim_throughput > 0 else 0
#             }
#         
#         return jsonify({
#             'status': 'success',
#             'comparison': comparison
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @bp.route('/modes/available', methods=['GET'])
# def get_available_modes():
#     """Get available processing modes for each pipeline type"""
#     try:
#         modes = {
#             'batch': {
#                 'real_spark': {
#                     'available': True,
#                     'description': 'Apache Spark distributed processing',
#                     'requirements': ['Spark environment', 'Java runtime'],
#                     'test_endpoint': '/api/pipeline/test/real-vs-simulated'
#                 }
#             },
#             'stream': {
#                 'real_kafka_streaming': {
#                     'available': None,  # Will test
#                     'description': 'Real Kafka streaming with Storm processing',
#                     'requirements': ['Kafka broker', 'Topic creation permissions'],
#                     'test_endpoint': '/api/pipeline/test/real-vs-simulated'
#                 },
#                 'simulated_streaming': {
#                     'available': True,
#                     'description': 'File-based record-by-record processing simulation',
#                     'requirements': ['None'],
#                     'test_endpoint': '/api/pipeline/test/real-vs-simulated'
#                 }
#             },
#             'hybrid': {
#                 'real_kafka_intelligent_routing': {
#                     'available': None,  # Will test
#                     'description': 'Real Kafka with Flink intelligent routing',
#                     'requirements': ['Kafka broker', 'Topic creation permissions'],
#                     'test_endpoint': '/api/pipeline/test/real-vs-simulated'
#                 },
#                 'simulated_intelligent_routing': {
#                     'available': True,
#                     'description': 'File-based processing with real routing logic',
#                     'requirements': ['None'],
#                     'test_endpoint': '/api/pipeline/test/real-vs-simulated'
#                 }
#             }
#         }
#         
#         # Test Kafka availability
#         try:
#             from kafka import KafkaProducer
#             producer = KafkaProducer(
#                 bootstrap_servers=['localhost:9093'],
#                 retries=1,
#                 request_timeout_ms=5000
#             )
#             producer.close()
#             kafka_available = True
#         except Exception:
#             kafka_available = False
#         
#         # Update availability based on tests
#         modes['stream']['real_kafka_streaming']['available'] = kafka_available
#         modes['hybrid']['real_kafka_intelligent_routing']['available'] = kafka_available
#         
#         return jsonify({
#             'status': 'success',
#             'kafka_available': kafka_available,
#             'modes': modes,
#             'recommendations': {
#                 'for_research': 'Use real modes when available for accurate performance metrics',
#                 'for_development': 'Simulated modes work without infrastructure requirements',
#                 'setup_kafka': 'Run `brew install kafka` or use Docker for real streaming capabilities'
#             }
#         })
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}'), 500 

# ================================
# END COMMENTED OUT PIPELINE ROUTES 
# ================================

# Initialize optimized streaming at app startup
def initialize_optimized_streaming():
    """Initialize the optimized streaming architecture"""
    print("🚀 Initializing streaming...")
    
    try:
        stream_manager.initialize_static_topics()
        stream_manager.start_persistent_consumers()
        print("✅ Streaming ready")
    except Exception as e:
        print(f"❌ Streaming init failed: {e}")
        # Continue without optimized streaming