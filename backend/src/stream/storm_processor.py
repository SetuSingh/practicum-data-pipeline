"""
Storm Stream Processing Pipeline (Pure Kafka Streaming)
Processes real-time data streams with immediate compliance checking

This module implements Research Question 1 (RQ1): Stream processing approach
for real-time compliance monitoring. It demonstrates low-latency processing
of individual records with immediate violation detection and response.

Key Features:
- Real-time streaming data processing (Apache Storm topology with Kafka)
- Immediate HIPAA/GDPR compliance violation detection
- Enhanced Anonymization Engine with configurable parameters
- Low-latency metrics collection for research comparison
- Pure Kafka-based message streaming architecture

Architecture:
- Consumer: Subscribes to healthcare-stream and financial-stream topics
- Processor: Real-time compliance checking and anonymization
- Producer: Outputs processed data and violations to result topics

REQUIRES: Kafka must be running and accessible - no fallback mode
"""
import json
import time
import csv
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer  # Kafka for streaming message processing
import threading
import re  # Regular expressions for compliance pattern matching
import sys
import os

# Import our modular components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
from compliance_rules import quick_compliance_check, detailed_compliance_check

# Import anonymization components from the unified location to prevent enum identity issues
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.common.anonymization_engine import EnhancedAnonymizationEngine, AnonymizationConfig, AnonymizationMethod

class StormStreamProcessor:
    def __init__(self, kafka_servers=['localhost:9093']):
        """
        Initialize the pure Kafka stream processor
        
        Args:
            kafka_servers (list): List of Kafka broker addresses
        """
        self.kafka_servers = kafka_servers  # Kafka broker endpoints
        self.consumer = None                # Kafka consumer for input streams
        self.producer = None                # Kafka producer for output streams
        self.running = False                # Processing state flag
        
        # Initialize Enhanced Anonymization Engine
        self.anonymization_engine = EnhancedAnonymizationEngine()
        
        # Metrics collection for research evaluation and comparison
        self.metrics = {
            'processed_records': 0,     # Total records processed
            'violations_detected': 0,   # Number of compliance violations found
            'start_time': None,         # Processing start timestamp
            'processing_times': []      # Individual record processing times for latency analysis
        }
    
    def setup_kafka(self):
        """
        Setup Kafka consumer and producer connections for stream processing
        
        Returns:
            bool: True if setup successful, False otherwise
        
        Raises:
            Exception: If Kafka setup fails (no fallback mode)
        """
        print("🔌 Setting up Kafka connections...")
        
        # Setup consumer to read from input streams
        # Subscribes to both healthcare and financial data streams
        self.consumer = KafkaConsumer(
            'healthcare-stream',    # Real-time healthcare data
            'financial-stream',     # Real-time financial data
            bootstrap_servers=self.kafka_servers,
            auto_offset_reset='latest',  # Start from newest messages (real-time processing)
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))  # JSON deserializer
        )
        
        # Setup producer to output processed results
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')  # JSON serializer
        )
        
        # Test connections by getting metadata
        try:
            # Test producer connection
            producer_metadata = self.producer.partitions_for('processed-stream')
            
            # Test consumer connection by subscribing (this validates the connection)
            # The consumer is already subscribed to topics in the constructor
            
            print("✅ Kafka setup complete - Consumer and Producer connected")
        except Exception as e:
            print(f"❌ Kafka connection test failed: {e}")
            raise
        return True
    
    def initialize_connections(self):
        """
        Initialize connections for stream processing (standardized method name)
        
        Returns:
            bool: True if setup successful
        
        Raises:
            Exception: If Kafka connections cannot be established
        """
        return self.setup_kafka()
    
    def check_compliance_realtime(self, record):
        """
        Perform real-time compliance checking using modular compliance rules
        
        This method uses the centralized compliance rules engine for fast
        violation detection. It's optimized for streaming with quick checks
        while maintaining consistency with batch processing rules.
        
        Args:
            record (dict): Single data record from the stream
            
        Returns:
            list: List of violation details found in the record
        """
        # Determine data type for appropriate rule selection
        data_type = 'healthcare' if 'patient_name' in record else 'financial'
        
        # Use modular compliance checking for consistency
        has_violations = quick_compliance_check(record, data_type)
        
        if has_violations:
            # Get detailed violation information for processing decisions
            compliance_result = detailed_compliance_check(record, data_type)
            return compliance_result['violations']
        
        return []
    
    def check_compliance(self, record):
        """
        Perform compliance checking using modular compliance rules (standardized method name)
        
        This method provides a consistent interface across all processors
        for compliance checking functionality.
        
        Args:
            record (dict): Single data record from the stream
            
        Returns:
            list: List of violation details found in the record
        """
        return self.check_compliance_realtime(record)
    
    def anonymize_realtime(self, record, method="tokenization"):
        """
        Apply real-time anonymization for Research Question 2 (RQ2)
        
        This method implements tokenization-based anonymization optimized for
        streaming data. Tokenization is preferred for streams because it's
        fast, deterministic, and preserves referential integrity across records.
        
        Args:
            record (dict): Data record with potential violations
            method (str): Anonymization method ('tokenization' or 'differential_privacy')
            
        Returns:
            dict: Anonymized record with sensitive data replaced by tokens
        """
        anonymized = record.copy()  # Create copy to avoid modifying original
        
        if method == "tokenization":
            # Tokenization: Replace sensitive data with deterministic tokens
            # This approach maintains referential integrity while hiding actual values
            # Hash-based tokens ensure same input always produces same token
            
            # Tokenize Social Security Number
            if 'ssn' in record:
                anonymized['ssn'] = f"TOKEN_{hash(record['ssn']) % 10000:04d}"
                
            # Tokenize phone number
            if 'phone' in record:
                anonymized['phone'] = f"PHONE_TOKEN_{hash(record['phone']) % 1000:03d}"
                
            # Tokenize email address
            if 'email' in record:
                anonymized['email'] = f"EMAIL_TOKEN_{hash(record['email']) % 1000:03d}"
                
            # Tokenize patient/customer name
            if 'patient_name' in record:
                anonymized['patient_name'] = f"PATIENT_{hash(record['patient_name']) % 1000:03d}"
        
        elif method == "differential_privacy":
            # Differential Privacy: Add mathematical privacy guarantees
            # For streaming data, we use a simple masking approach
            # Real DP would require careful privacy budget management across streams
            
            anonymized['ssn'] = "DP_PROTECTED"          # DP-protected SSN
            anonymized['phone'] = "DP_PROTECTED"        # DP-protected phone
            anonymized['email'] = "DP_PROTECTED"        # DP-protected email
            if 'patient_name' in record:
                anonymized['patient_name'] = "DP_PROTECTED"  # DP-protected name
        
        return anonymized
    
    def anonymize_data(self, record, method="tokenization"):
        """
        Apply anonymization to data (standardized method name)
        
        This method provides a consistent interface across all processors
        for data anonymization functionality.
        
        Args:
            record (dict): Data record with potential violations
            method (str): Anonymization method ('tokenization' or 'differential_privacy')
            
        Returns:
            dict: Anonymized record with sensitive data replaced by tokens
        """
        return self.anonymize_realtime(record, method)
    
    def process_record(self, record, anonymization_config):
        """
        Process a single record through the stream pipeline with accurate timing.
        
        This method handles the core streaming logic:
        1. Real-time compliance checking
        2. Conditional anonymization (only for violated records)
        3. Metadata addition
        
        Args:
            record (dict): Single data record from the stream
            anonymization_config (AnonymizationConfig): Configuration for anonymization
            
        Returns:
            dict: Processed and potentially anonymized record
        """
        # 🔥 PURE PROCESSING TIMING STARTS HERE
        pure_processing_start = time.time()
        
        # Step 1: Add processing metadata for tracking (pure processing)
        record['stream_processed_at'] = datetime.now().isoformat()
        
        # Step 2: Perform real-time compliance checking (pure processing)
        violations = self.check_compliance_realtime(record)
        record['stream_violations'] = violations            # List of violations found
        record['stream_compliant'] = len(violations) == 0   # Boolean compliance status
        record['has_violations'] = len(violations) > 0      # Standard violation flag
        
        # Step 3: Apply anonymization for records with violations (pure processing)
        # Only anonymize when violations are detected to preserve data utility
        if violations:
            anonymized_record = self.anonymization_engine.anonymize_record(record, anonymization_config)
        else:
            anonymized_record = record  # Keep compliant records unchanged
        
        # Step 4: Add processing metadata (pure processing)
        anonymized_record['processing_method'] = 'stream'
        anonymized_record['anonymization_applied'] = len(violations) > 0
        anonymized_record['anonymization_method'] = anonymization_config.method.value
        anonymized_record['anonymization_parameters'] = str(anonymization_config)
        
        # 🔥 PURE PROCESSING TIMING ENDS HERE
        pure_processing_time = time.time() - pure_processing_start
        
        # Add timing information (not part of processing timing)
        anonymized_record['pure_processing_time'] = pure_processing_time
        
        # Update metrics (not part of processing timing)
        self.metrics['processed_records'] += 1
        # FIX: Store actual processing duration, not epoch timestamp
        self.metrics['processing_times'].append(pure_processing_time)
        
        if len(violations) > 0:
            self.metrics['violations_detected'] += 1
        
        return anonymized_record
    
    def process_data(self, record):
        """
        Process data (standardized method name)
        
        This method provides a consistent interface across all processors
        for data processing functionality.
        
        Args:
            record (dict): Single data record from the stream
            
        Returns:
            dict: Processed and potentially anonymized record
        """
        return self.process_record(record)
    
    def start_stream_processing(self):
        """
        Start the main stream processing loop
        
        This method implements the continuous processing loop that simulates
        Apache Storm's real-time processing capabilities. It consumes messages
        from Kafka topics and processes them individually in real-time.
        
        Raises:
            Exception: If Kafka setup fails or connection is lost
        """
        # Setup Kafka connections - REQUIRED, no fallback
        print("🚀 Initializing Pure Kafka Stream Processor...")
        self.setup_kafka()
        
        # Initialize processing state and metrics
        self.running = True
        self.metrics['start_time'] = time.time()
        
        print("✅ Starting Storm stream processing...")
        print("📡 Consuming from topics: healthcare-stream, financial-stream")
        print("📤 Producing to topics: processed-stream, compliance-violations")
        
        # Main processing loop - consume and process messages continuously
        for message in self.consumer:
            if not self.running:
                break  # Stop processing if shutdown requested
            
            # Extract record from Kafka message and process it
            record = message.value
            processed_record = self.process_record(record)
    
    def process_file(self, input_file, output_file, anonymization_config=None):
        """
        Process a file with stream processing approach and CSV output
        
        This method simulates streaming by processing records individually
        while storing results in memory for CSV output in post-processing.
        
        Args:
            input_file (str): Path to input CSV file
            output_file (str): Path to output CSV file
            anonymization_config (AnonymizationConfig): Configuration for anonymization parameters
            
        Returns:
            dict: Complete processing metrics with timing separation
        """
        # ==================== PRE-PROCESSING PHASE ====================
        pre_processing_start = time.time()
        
        print("📥 Pre-Processing: File loading and stream setup...")
        
        # Basic file validation (infrastructure only)
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Load file data (infrastructure only)
        records = []
        with open(input_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            records = list(reader)
        
        total_records = len(records)
        processed_records = []
        
        pre_processing_time = time.time() - pre_processing_start
        print(f"   ✅ Pre-processing complete: {pre_processing_time:.3f}s")
        
        # ==================== PIPELINE PROCESSING PHASE ====================
        print("⚡ Starting pure stream processing...")
        
        # 🔥 PIPELINE PROCESSING TIMING STARTS HERE
        pipeline_processing_start = time.time()
        
        # Process each record individually (streaming paradigm)
        for i, record in enumerate(records):
            processed_record = self.process_record(record, anonymization_config)
            processed_records.append(processed_record)
            
            # Progress reporting
            if (i + 1) % 100 == 0 or i == 0:
                elapsed = time.time() - pipeline_processing_start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                # Only print every 200 records to reduce verbosity
                if (i + 1) % 500 == 0:
                    print(f"   🔄 Processed {i + 1}/{total_records} records ({rate:.0f} rec/sec)")
        
        # 🔥 PIPELINE PROCESSING TIMING ENDS HERE
        pipeline_processing_time = time.time() - pipeline_processing_start
        
        violations_found = sum(1 for record in processed_records if record.get('has_violations', False))
        records_per_second = total_records / pipeline_processing_time
        
        print(f"✅ Stream processing complete!")
        print(f"   Pipeline processing time: {pipeline_processing_time:.3f}s")
        print(f"   Processing rate: {records_per_second:.0f} records/second")
        print(f"   Violations found: {violations_found}")
        
        # ==================== POST-PROCESSING PHASE ====================
        post_processing_start = time.time()
        
        print("💾 Post-Processing: Saving results to CSV...")
        
        # Save results directly to CSV (infrastructure only)
        if processed_records:
            # Get field names from first record
            fieldnames = list(processed_records[0].keys())
            
            # Write to CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_records)
            
            print(f"   ✅ Saved {len(processed_records)} records to {output_file}")
        else:
            print("   ⚠️ No records to save")
        
        post_processing_time = time.time() - post_processing_start
        print(f"   ✅ Post-processing complete: {post_processing_time:.3f}s")
        
        # ==================== FINAL METRICS ====================
        return {
            'processing_approach': 'stream',
            'pre_processing_time': pre_processing_time,
            'pure_processing_time': pipeline_processing_time,
            'post_processing_time': post_processing_time,
            'total_execution_time': pre_processing_time + pipeline_processing_time + post_processing_time,
            'processing_metrics': {
                'total_records': total_records,
                'records_per_second': records_per_second,
                'violations_found': violations_found,
                'anonymization_config': anonymization_config
            },
            'timing_separation': {
                'pre_processing': f"{pre_processing_time:.3f}s",
                'pure_processing': f"{pipeline_processing_time:.3f}s",
                'post_processing': f"{post_processing_time:.3f}s"
            }
        }

    def start_processing(self):
        """
        Start processing (standardized method name)
        
        This method provides a consistent interface across all processors
        for starting the processing pipeline.
        """
        return self.start_stream_processing()
    
    def stop(self):
        """
        Stop stream processing and display final metrics
        
        This method gracefully shuts down the processor and provides
        comprehensive metrics for research evaluation and comparison.
        """
        self.running = False  # Signal processing loop to stop
        
        # Close Kafka connections
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        
        # Calculate final metrics for research comparison
        pipeline_processing_time = time.time() - self.metrics['start_time']
        total_time = pipeline_processing_time
        records_per_second = self.metrics['processed_records'] / total_time if total_time > 0 else 0
        
        # Calculate violations from processed data
        violations_found = sum(1 for record in processed_records if record.get('has_violations', False))
        
        if not processed_records:
            total_time = 0
        throughput = self.metrics['processed_records'] / total_time if total_time > 0 else 0
        violation_rate = (self.metrics['violations_detected'] / self.metrics['processed_records'] * 100) if self.metrics['processed_records'] > 0 else 0
        # FIX: Calculate average latency correctly (already in seconds, convert to ms)
        avg_latency_ms = (sum(self.metrics['processing_times']) / len(self.metrics['processing_times']) * 1000) if self.metrics['processing_times'] else 0
        
        # Reduced verbosity - essential metrics only
        print(f"✅ Stream processing complete!")
        print(f"   Pure processing time: {total_time:.3f}s")
        print(f"   Processing rate: {records_per_second:.0f} records/second")
        print(f"   Records processed: {total_records}")
        print(f"   Violations found: {violations_found}")
        print(f"   Average latency: {avg_latency_ms:.2f}ms")
    
    def stop_processing(self):
        """
        Stop processing (standardized method name)
        
        This method provides a consistent interface across all processors
        for stopping the processing pipeline.
        """
        return self.stop()

class StreamDataProducer:
    """
    Simulates real-time data generation for testing stream processing
    
    This class generates continuous streams of healthcare and financial data
    with compliance violations for testing our stream processing pipeline.
    It simulates real-world data sources that would feed into a streaming
    compliance monitoring system.
    """
    def __init__(self, kafka_servers=['localhost:9093']):
        """
        Initialize the stream data producer
        
        Args:
            kafka_servers (list): List of Kafka broker addresses
        """
        # Setup Kafka producer for streaming data generation
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')  # JSON serialization
        )
        
        # Import and initialize our data generator for creating test records
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
        from data_generator import SimpleDataGenerator
        self.data_generator = SimpleDataGenerator()
    
    def generate_stream(self, topic, data_type, records_per_second=10, duration_seconds=60):
        """
        Generate continuous stream of data for testing
        
        This method simulates real-time data arrival at specified rates,
        allowing us to test stream processing performance under different
        load conditions for research evaluation.
        
        Args:
            topic (str): Kafka topic to send data to
            data_type (str): Type of data ('healthcare' or 'financial')
            records_per_second (int): Rate of data generation
            duration_seconds (int): How long to generate data
        """
        print(f"Generating {records_per_second} {data_type} records/second to {topic} for {duration_seconds} seconds")
        
        # Calculate sleep interval to achieve desired rate
        interval = 1.0 / records_per_second
        end_time = time.time() + duration_seconds
        
        # Generate and send records at the specified rate
        while time.time() < end_time:
            # Generate a single record with potential compliance violations
            record = self.data_generator.generate_stream_record(data_type)
            
            # Send record to Kafka topic for stream processing
            self.producer.send(topic, record)
            
            # Wait to maintain desired rate
            time.sleep(interval)
        
        # Cleanup producer connection
        self.producer.close()
        print(f"Stream generation complete for {topic}")

def main():
    """
    Main function for testing stream processing capabilities
    
    This function provides a command-line interface for running either:
    1. Stream processor (consumer mode) - processes incoming data streams
    2. Data generator (producer mode) - generates test data streams
    
    This allows for comprehensive testing of stream processing performance
    under different conditions for research evaluation.
    """
    import argparse
    
    # Setup command-line argument parsing for flexible testing
    parser = argparse.ArgumentParser(description='Storm Stream Processor')
    parser.add_argument('--mode', choices=['consumer', 'producer'], default='consumer',
                       help='Run as consumer (processor) or producer (data generator)')
    parser.add_argument('--topic', default='healthcare-stream',
                       help='Kafka topic name for data streaming')
    parser.add_argument('--rate', type=int, default=10, 
                       help='Records per second for producer mode')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Duration in seconds for producer mode')
    
    args = parser.parse_args()
    
    if args.mode == 'consumer':
        # Start stream processing (Research Question 1 evaluation)
        print("Starting stream processor for real-time compliance monitoring...")
        processor = StormStreamProcessor()
        processor.start_stream_processing()
    
    elif args.mode == 'producer':
        # Generate test data streams for evaluation
        print("Starting data producer for stream testing...")
        producer = StreamDataProducer()
        
        # Determine data type based on topic name
        data_type = 'healthcare' if 'healthcare' in args.topic else 'financial'
        
        # Generate continuous stream at specified rate
        producer.generate_stream(args.topic, data_type, args.rate, args.duration)

if __name__ == "__main__":
    main() 