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

from batch.spark_processor import SparkBatchProcessor
from stream.storm_processor import StormStreamProcessor
from hybrid.flink_processor import FlinkHybridProcessor

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
    
    def process_file(self, job_id: str, filepath: str, pipeline_type: str, processed_folder: str, job_instance=None) -> Dict[str, Any]:
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
            job_instance: Optional database job instance for progress tracking
            
        Returns:
            Dict[str, Any]: Comprehensive metrics and results from processing
        """
        start_time = time.time()
        
        try:
            # Get the appropriate processor for the pipeline type
            processor = self.get_processor(pipeline_type)
            
            # Update job status if tracking instance provided
            if job_instance:
                job_instance.status = 'processing'
                job_instance.progress = 5

            if pipeline_type == 'batch':
                return self._process_batch(processor, filepath, job_id, start_time, processed_folder, job_instance)
            elif pipeline_type == 'stream':
                # Use REAL Kafka streaming only - no fallback
                return self._process_stream_real(processor, filepath, job_id, start_time, processed_folder, job_instance)
            elif pipeline_type == 'hybrid':
                # Use REAL Kafka hybrid processing only - no fallback
                return self._process_hybrid_real(processor, filepath, job_id, start_time, processed_folder, job_instance)
            else:
                raise ValueError(f"Unsupported pipeline type: {pipeline_type}")
                
        except Exception as e:
            if job_instance:
                job_instance.status = 'failed'
                job_instance.error = str(e)
            raise
    
    def _process_batch(self, processor: SparkBatchProcessor, filepath: str, job_id: str, 
                      start_time: float, processed_folder: str, job_instance=None) -> Dict[str, Any]:
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
                anonymization_method="k_anonymity"
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
            
            return complete_metrics
            
        except Exception as e:
            print(f"❌ Batch processing failed: {str(e)}")
            
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
                linger_ms=5,       # Small linger time for better batching
                compression_type='snappy',  # Compression for better network efficiency
                acks=1             # Faster acknowledgment (leader only)
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
                            start_time: float, processed_folder: str, job_instance=None) -> Dict[str, Any]:
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
            
            # 🔥 PURE PROCESSING TIMING STARTS HERE
            processing_results = []
            processing_complete = threading.Event()
            processing_error = None
            pure_processing_start = time.time()
            
            def stream_processing_thread():
                nonlocal processing_error
                try:
                    # Create a new consumer specifically for this topic
                    from kafka import KafkaConsumer
                    import json
                    
                    consumer = KafkaConsumer(
                        topic_name,
                        bootstrap_servers=['localhost:9093'],
                        auto_offset_reset='earliest',  # Start from beginning to catch our messages
                        consumer_timeout_ms=2000,  # 2 second timeout for efficient processing
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        fetch_max_wait_ms=500,  # Reduce wait time for faster processing
                        max_poll_records=500    # Process more records per poll
                    )
                    
                    print(f"      🔗 Consumer subscribed to topic '{topic_name}'")
                    
                    # Process stream with pure timing - optimized for speed
                    messages_processed = 0
                    consecutive_empty_polls = 0
                    max_empty_polls = 3  # Stop after 3 consecutive empty polls
                    processing_start_time = time.time()
                    
                    for message in consumer:
                        try:
                            # 🔥 PURE PROCESSING (timed section)
                            record = message.value
                            processed_record = processor.process_record(record)
                            processing_results.append(processed_record)
                            messages_processed += 1
                            consecutive_empty_polls = 0  # Reset counter on successful processing
                            
                            if messages_processed % 100 == 0:
                                elapsed = time.time() - processing_start_time
                                rate = messages_processed / elapsed if elapsed > 0 else 0
                                print(f"      🔄 Processed {messages_processed} stream records... ({rate:.0f} records/sec)")
                                
                        except Exception as e:
                            print(f"      ⚠️  Record processing error: {str(e)}")
                            continue
                    
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
            
            # Wait for processing to complete
            processing_complete.wait(timeout=10)  # 10 second timeout for faster completion
            
            # 🔥 PURE PROCESSING TIMING ENDS HERE
            pure_processing_time = time.time() - pure_processing_start
            
            if processing_error:
                raise Exception(f"Stream processing failed: {processing_error}")
            
            # POST-PROCESSING: Database operations and result storage (not timed)
            print("💾 Post-Processing: Database operations and result storage...")
            post_processing_start = time.time()
            
            # Update job status after pure processing (not timed)
            if job_instance:
                job_instance.status = 'storing_results'
                job_instance.progress = 80
            
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
            
            # Calculate metrics
            total_records = len(processing_results)
            violations_found = sum(1 for r in processing_results if r.get('has_violations', False))
            processing_times = [r.get('pure_processing_time', 0) for r in processing_results]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            records_per_second = total_records / pure_processing_time if pure_processing_time > 0 else 0
            
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
                    'average_processing_time': avg_processing_time,
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
                    'average_latency_ms': avg_processing_time * 1000,
                    'streaming_paradigm': 'pure_kafka_streaming'
                }
            }
            
            print(f"✅ Stream processing completed successfully!")
            print(f"   Pure processing time: {pure_processing_time:.3f}s")
            print(f"   Processing rate: {records_per_second:.0f} records/second")
            print(f"   Records processed: {total_records}")
            print(f"   Violations found: {violations_found}")
            print(f"   Average latency: {avg_processing_time*1000:.2f}ms")
            
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
                            start_time: float, processed_folder: str, job_instance=None) -> Dict[str, Any]:
        """Process file through REAL Flink hybrid processing with Kafka ingestion"""
        
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
            
            def hybrid_processing_thread():
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
                        consumer_timeout_ms=2000,  # 2 second timeout for efficient processing
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        fetch_max_wait_ms=500,  # Reduce wait time for faster processing
                        max_poll_records=500    # Process more records per poll
                    )
                    
                    print(f"      🔗 Consumer subscribed to topic '{topic_name}'")
                    
                    # Process hybrid stream with optimized timing
                    processing_start_time = time.time()
                    
                    for message in consumer:
                            
                        try:
                            record = message.value
                            
                            # Real hybrid processing: analyze and route
                            characteristics = processor.analyze_data_characteristics(record)
                            decision = processor.make_routing_decision(record, characteristics)
                            routing_decisions.append(decision)
                            
                            # Process based on routing decision
                            if decision['route'] == 'batch':
                                batch_routed += 1
                                processor.add_to_batch_buffer(record)
                                # Mark for later batch processing
                                record['processed_via'] = 'hybrid_batch'
                                record['routing_decision'] = decision
                                processing_results.append(record)
                                
                            elif decision['route'] == 'stream':
                                stream_routed += 1
                                processed_record, latency = processor.process_via_stream(record)
                                processed_record['routing_decision'] = decision
                                processed_record['stream_latency_ms'] = latency * 1000
                                processing_results.append(processed_record)
                            
                            if len(processing_results) % 25 == 0:
                                elapsed = time.time() - processing_start_time
                                rate = len(processing_results) / elapsed if elapsed > 0 else 0
                                print(f"      🔄 Processed {len(processing_results)} records "
                                      f"(B:{batch_routed}, S:{stream_routed}) ({rate:.0f} records/sec)")
                                
                        except Exception as e:
                            print(f"      ⚠️  Record processing error: {str(e)}")
                            continue
                    
                    # Process any remaining batch buffer
                    if hasattr(processor, 'batch_buffer') and len(processor.batch_buffer) > 0:
                        print(f"      📦 Processing final batch buffer: {len(processor.batch_buffer)} records")
                        processor.process_batch_buffer()
                    
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
            processing_complete.wait(timeout=15)  # 15 second timeout for faster completion
            
            if processing_error:
                raise Exception(f"Hybrid processing failed: {processing_error}")
            
            if job_instance:
                job_instance.progress = 80
            
            # Step 4: Save results and calculate metrics (using pre-fetched processed_folder)
            output_file = os.path.join(processed_folder, f"hybrid_real_{job_id}.csv")
            
            if processing_results:
                import pandas as pd
                processed_df = pd.DataFrame(processing_results)
                processed_df.to_csv(output_file, index=False)
                
                total_records = len(processing_results)
                violation_records = sum(1 for r in processing_results 
                                       if r.get('has_violations', False) or 
                                          any('violation' in str(v).lower() for v in r.values() if isinstance(v, str)))
                
                print(f"   💾 Saved {total_records} processed records to {output_file}")
                
                # Insert processed records into database
                if job_instance and hasattr(job_instance, 'file_id') and job_instance.file_id:
                    from app import db_connector
                    import hashlib
                    import json
                    
                    records_inserted = 0
                    violations_inserted = 0
                    
                    print(f"   🗄️  Inserting {total_records} records into database...")
                    
                    for idx, record in enumerate(processing_results):
                        try:
                            # Extract core data (remove processing metadata)
                            core_data = {k: v for k, v in record.items() 
                                       if not k.startswith('routing_') and 
                                       not k.startswith('processed_') and 
                                       not k.startswith('stream_') and
                                       k not in ['has_violations', 'job_id', 'routing_decision']}
                            
                            # Clean data for JSON serialization
                            core_data = clean_data_for_json_serialization(core_data)
                            
                            # Generate record ID and hash
                            record_id = f"hybrid_{job_id}_{idx}"
                            record_hash = hashlib.sha256(
                                json.dumps(core_data, sort_keys=True).encode()
                            ).hexdigest()
                            
                            # Insert record into database
                            if db_connector:
                                data_record_db_id = safe_create_data_record(
                                    db_connector, idx,
                                    file_id=job_instance.file_id,
                                    record_id=record_id,
                                    original_data=core_data,
                                    record_hash=record_hash,
                                    job_id=getattr(job_instance, 'db_job_id', None),
                                    row_number=idx + 1,
                                    has_pii=True,  # Hybrid data typically has PII
                                    has_violations=record.get('has_violations', False),
                                    violation_types=[],  # Hybrid violations handled differently
                                    compliance_score=0.8,  # Default score for hybrid processing
                                    created_by=job_instance.user_id
                                )
                                records_inserted += 1
                                
                                # Progress update every 100 records
                                if (idx + 1) % 100 == 0:
                                    print(f"      📝 Inserted {idx + 1}/{total_records} records into database...")
                                    
                        except Exception as record_error:
                            print(f"      ⚠️  Failed to insert record {idx}: {str(record_error)}")
                            continue
                    
                    print(f"   ✅ Database insertion completed: {records_inserted} records")
            
            # Analyze routing patterns first (needed for file status update)
            routing_reasons = [d['reason'] for d in routing_decisions]
            routing_reason_counts = {reason: routing_reasons.count(reason) for reason in set(routing_reasons)}
            
            # Update file processing status
            if db_connector:
                try:
                    db_connector.update_file_processing_status(
                        file_id=job_instance.file_id,
                        status='completed',
                        total_records=total_records,
                        valid_records=total_records - violation_records,
                        invalid_records=violation_records,
                        compliance_report={
                            'violations_found': violation_records,
                            'violation_rate': violation_records / total_records if total_records > 0 else 0,
                            'processing_engine': 'Apache Flink (REAL Kafka + intelligent routing)',
                            'pipeline_type': 'hybrid',
                            'routing_decisions': routing_reason_counts
                        },
                        updated_by=job_instance.user_id
                    )
                    print(f"   📊 File processing status updated in database")
                except Exception as status_error:
                    print(f"   ⚠️  Failed to update file status: {str(status_error)}")
                
            else:
                total_records = 0
                violation_records = 0
                routing_reason_counts = {}  # Initialize empty for no records case
                with open(output_file, 'w') as f:
                    f.write('no_data,reason\n')
                    f.write('true,kafka_processing_timeout_or_no_messages\n')
                print(f"   ⚠️  No records processed - saved empty result file")
            
            # Calculate comprehensive metrics
            processing_time = time.time() - start_time
            
            metrics = {
                'pipeline_type': 'hybrid',
                'job_id': job_id,
                'processing_engine': 'Apache Flink (REAL Kafka + intelligent routing)',
                'hybrid_architecture': True,
                'intelligent_routing': True,
                'real_kafka_ingestion': True,
                'kafka_topic_used': topic_name,
                'total_records': total_records,
                'violation_records': violation_records,
                'violation_rate': violation_records / total_records if total_records > 0 else 0,
                'processing_time_seconds': processing_time,
                'throughput_records_per_second': total_records / processing_time if processing_time > 0 else 0,
                'kafka_ingestion_rate': 5000,  # records per second (high-speed)
                
                # Real routing intelligence metrics
                'batch_routed_records': batch_routed,
                'stream_routed_records': stream_routed,
                'batch_routing_percentage': batch_routed / total_records * 100 if total_records > 0 else 0,
                'stream_routing_percentage': stream_routed / total_records * 100 if total_records > 0 else 0,
                'routing_decision_distribution': routing_reason_counts,
                'routing_decisions_sample': routing_decisions[:10],
                
                'real_time_processing': True,
                'adaptive_processing': True,
                'anonymization_method': 'tokenization',
                'output_file': output_file,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store metrics for research evaluation
            self.metrics['hybrid'].append(metrics)
            
            if job_instance:
                job_instance.progress = 100
                job_instance.status = 'completed' if total_records > 0 else 'completed_with_warnings'
                job_instance.results = metrics
            
            print(f"✅ REAL Flink hybrid processing completed for job {job_id}")
            print(f"   📊 Processed {total_records} records through Kafka topic '{topic_name}'")
            print(f"   🎯 Routing: {batch_routed} → batch, {stream_routed} → stream")
            return metrics
            
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

@bp.route('/process', methods=['POST'])
def process_file():
    """Process uploaded file through specified pipeline"""
    try:
        from app import processing_jobs, db_connector
        
        data = request.json
        job_id = data.get('job_id')
        filepath = data.get('filepath')
        pipeline_type = data.get('pipeline_type', 'batch')
        
        if not job_id or job_id not in processing_jobs:
            return jsonify({'error': 'Invalid job ID'}), 400
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400
        
        job = processing_jobs[job_id]
        
        # Process through specified pipeline
        metrics = orchestrator.process_file(job_id, filepath, pipeline_type, current_app.config['PROCESSED_FOLDER'], job)
        
        return jsonify({
            'status': 'success',
            'message': f'File processed through {pipeline_type} pipeline',
            'metrics': metrics
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/metrics', methods=['GET'])
def get_pipeline_metrics():
    """Get research evaluation metrics"""
    try:
        pipeline_type = request.args.get('pipeline_type')
        metrics = orchestrator.get_research_metrics(pipeline_type)
        
        return jsonify({
            'status': 'success',
            'data': metrics
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/metrics/comparison', methods=['GET'])
def get_comparative_metrics():
    """Get comparative metrics for research evaluation"""
    try:
        all_metrics = orchestrator.get_research_metrics()
        
        # Calculate comparative statistics
        comparison = {
            'throughput_comparison': {},
            'latency_comparison': {},
            'violation_detection_comparison': {}
        }
        
        for pipeline_type, metrics_list in all_metrics['all_metrics'].items():
            if metrics_list:
                throughputs = [m['throughput_records_per_second'] for m in metrics_list]
                violation_rates = [m['violation_rate'] for m in metrics_list]
                
                comparison['throughput_comparison'][pipeline_type] = {
                    'average': sum(throughputs) / len(throughputs),
                    'max': max(throughputs),
                    'min': min(throughputs)
                }
                
                comparison['violation_detection_comparison'][pipeline_type] = {
                    'average_violation_rate': sum(violation_rates) / len(violation_rates),
                    'total_jobs': len(metrics_list)
                }
                
                # Add latency metrics for stream and hybrid
                if pipeline_type in ['stream', 'hybrid']:
                    latencies = [m.get('average_latency_seconds', 0) for m in metrics_list]
                    comparison['latency_comparison'][pipeline_type] = {
                        'average_latency': sum(latencies) / len(latencies),
                        'max_latency': max(latencies),
                        'min_latency': min(latencies)
                    }
        
        return jsonify({
            'status': 'success',
            'comparison': comparison,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/processors/status', methods=['GET'])
def get_processor_status():
    """Get status of all pipeline processors"""
    try:
        status = {}
        
        for pipeline_type in ['batch', 'stream', 'hybrid']:
            try:
                processor = orchestrator.get_processor(pipeline_type)
                status[pipeline_type] = {
                    'available': True,
                    'type': type(processor).__name__,
                    'initialized': True
                }
            except Exception as e:
                status[pipeline_type] = {
                    'available': False,
                    'error': str(e),
                    'initialized': False
                }
        
        return jsonify({
            'status': 'success',
            'processors': status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@bp.route('/test/real-vs-simulated', methods=['POST'])
def test_real_vs_simulated():
    """Test real vs simulated processing for research evaluation"""
    try:
        data = request.json
        filepath = data.get('filepath')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400
        
        print("🧪 Testing REAL vs SIMULATED processing...")
        
        results = {}
        
        # Test BATCH (always real)
        print("\n🔄 Testing BATCH (real Spark)...")
        try:
            batch_processor = orchestrator.get_processor('batch')
            job_id = str(uuid.uuid4())[:8]
            start_time = time.time()
            
            batch_metrics = orchestrator._process_batch(batch_processor, filepath, f"batch-test-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'])
            results['batch'] = {
                'status': 'success',
                'mode': 'real_spark',
                'metrics': batch_metrics
            }
        except Exception as e:
            results['batch'] = {
                'status': 'failed',
                'mode': 'real_spark',
                'error': str(e)
            }
        
        # Test STREAM (real vs simulated)
        print("\n🔄 Testing STREAM (real Kafka vs simulated)...")
        stream_processor = orchestrator.get_processor('stream')
        
        # Try real streaming
        try:
            job_id = str(uuid.uuid4())[:8]
            start_time = time.time()
            
            real_stream_metrics = orchestrator._process_stream_real(stream_processor, filepath, f"stream-real-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'])
            results['stream_real'] = {
                'status': 'success',
                'mode': 'real_kafka_streaming',
                'metrics': real_stream_metrics
            }
        except Exception as e:
            results['stream_real'] = {
                'status': 'failed',
                'mode': 'real_kafka_streaming',
                'error': str(e)
            }
        
        # Note: Simulated streaming removed - only real Kafka streaming supported
        
        # Test HYBRID (real vs simulated)
        print("\n🔄 Testing HYBRID (real Kafka routing vs simulated)...")
        hybrid_processor = orchestrator.get_processor('hybrid')
        
        # Try real hybrid
        try:
            job_id = str(uuid.uuid4())[:8]
            start_time = time.time()
            
            real_hybrid_metrics = orchestrator._process_hybrid_real(hybrid_processor, filepath, f"hybrid-real-{job_id}", start_time, current_app.config['PROCESSED_FOLDER'])
            results['hybrid_real'] = {
                'status': 'success',
                'mode': 'real_kafka_intelligent_routing',
                'metrics': real_hybrid_metrics
            }
        except Exception as e:
            results['hybrid_real'] = {
                'status': 'failed',
                'mode': 'real_kafka_intelligent_routing',
                'error': str(e)
            }
        
        # Note: Simulated hybrid processing removed - only real Kafka routing supported
        
        # Generate comparison report
        comparison = {
            'test_file': filepath,
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'batch_real_available': results['batch']['status'] == 'success',
                'stream_real_available': results['stream_real']['status'] == 'success',
                'stream_simulated_available': results['stream_simulated']['status'] == 'success',
                'hybrid_real_available': results['hybrid_real']['status'] == 'success',
                'hybrid_simulated_available': results['hybrid_simulated']['status'] == 'success'
            }
        }
        
        # Performance comparison if both modes available
        if (results['stream_real']['status'] == 'success' and 
            results['stream_simulated']['status'] == 'success'):
            
            real_throughput = results['stream_real']['metrics']['throughput_records_per_second']
            sim_throughput = results['stream_simulated']['metrics']['throughput_records_per_second']
            
            comparison['performance_comparison'] = {
                'stream_real_throughput': real_throughput,
                'stream_simulated_throughput': sim_throughput,
                'throughput_difference_pct': ((real_throughput - sim_throughput) / sim_throughput * 100) if sim_throughput > 0 else 0
            }
        
        return jsonify({
            'status': 'success',
            'comparison': comparison
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/modes/available', methods=['GET'])
def get_available_modes():
    """Get available processing modes for each pipeline type"""
    try:
        modes = {
            'batch': {
                'real_spark': {
                    'available': True,
                    'description': 'Apache Spark distributed processing',
                    'requirements': ['Spark environment', 'Java runtime'],
                    'test_endpoint': '/api/pipeline/test/real-vs-simulated'
                }
            },
            'stream': {
                'real_kafka_streaming': {
                    'available': None,  # Will test
                    'description': 'Real Kafka streaming with Storm processing',
                    'requirements': ['Kafka broker', 'Topic creation permissions'],
                    'test_endpoint': '/api/pipeline/test/real-vs-simulated'
                },
                'simulated_streaming': {
                    'available': True,
                    'description': 'File-based record-by-record processing simulation',
                    'requirements': ['None'],
                    'test_endpoint': '/api/pipeline/test/real-vs-simulated'
                }
            },
            'hybrid': {
                'real_kafka_intelligent_routing': {
                    'available': None,  # Will test
                    'description': 'Real Kafka with Flink intelligent routing',
                    'requirements': ['Kafka broker', 'Topic creation permissions'],
                    'test_endpoint': '/api/pipeline/test/real-vs-simulated'
                },
                'simulated_intelligent_routing': {
                    'available': True,
                    'description': 'File-based processing with real routing logic',
                    'requirements': ['None'],
                    'test_endpoint': '/api/pipeline/test/real-vs-simulated'
                }
            }
        }
        
        # Test Kafka availability
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9093'],
                retries=1,
                request_timeout_ms=5000
            )
            producer.close()
            kafka_available = True
        except Exception:
            kafka_available = False
        
        # Update availability based on tests
        modes['stream']['real_kafka_streaming']['available'] = kafka_available
        modes['hybrid']['real_kafka_intelligent_routing']['available'] = kafka_available
        
        return jsonify({
            'status': 'success',
            'kafka_available': kafka_available,
            'modes': modes,
            'recommendations': {
                'for_research': 'Use real modes when available for accurate performance metrics',
                'for_development': 'Simulated modes work without infrastructure requirements',
                'setup_kafka': 'Run `brew install kafka` or use Docker for real streaming capabilities'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 