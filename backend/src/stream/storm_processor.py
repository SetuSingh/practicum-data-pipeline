"""
Storm Stream Processing Pipeline (Simulated with Kafka Consumer)
Processes real-time data streams with immediate compliance checking

This module implements Research Question 1 (RQ1): Stream processing approach
for real-time compliance monitoring. It demonstrates low-latency processing
of individual records with immediate violation detection and response.

Key Features:
- Real-time streaming data processing (simulating Apache Storm topology)
- Immediate HIPAA/GDPR compliance violation detection
- Real-time tokenization for privacy protection
- Low-latency metrics collection for research comparison
- Kafka-based message streaming architecture

Architecture:
- Consumer: Subscribes to healthcare-stream and financial-stream topics
- Processor: Real-time compliance checking and anonymization
- Producer: Outputs processed data and violations to result topics
"""
import json
import time
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer  # Kafka for streaming message processing
import threading
import re  # Regular expressions for compliance pattern matching
import sys
import os

# Import our modular components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
from compliance_rules import quick_compliance_check, detailed_compliance_check

class StormStreamProcessor:
    def __init__(self, kafka_servers=['localhost:9093']):
        """
        Initialize the stream processor with Kafka configuration
        
        Args:
            kafka_servers (list): List of Kafka broker addresses
        """
        self.kafka_servers = kafka_servers  # Kafka broker endpoints
        self.consumer = None                # Kafka consumer for input streams
        self.producer = None                # Kafka producer for output streams
        self.running = False                # Processing state flag
        
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
        """
        try:
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
            
            print("Kafka setup complete")
            return True
            
        except Exception as e:
            print(f"Failed to setup Kafka: {e}")
            return False
    
    def initialize_connections(self):
        """
        Initialize connections for stream processing (standardized method name)
        
        Returns:
            bool: True if setup successful, False otherwise
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
    
    def process_record(self, record):
        """
        Process a single streaming record with compliance checking and anonymization
        
        This is the core method that demonstrates stream processing capabilities
        for Research Question 1. Each record is processed independently with
        immediate compliance checking and anonymization when needed.
        
        Args:
            record (dict): Single data record from the stream
            
        Returns:
            dict: Processed and potentially anonymized record
        """
        start_time = time.time()  # Start latency measurement
        
        # Add processing metadata for tracking
        record['stream_processed_at'] = datetime.now().isoformat()
        
        # Step 1: Perform real-time compliance checking
        violations = self.check_compliance_realtime(record)
        record['stream_violations'] = violations            # List of violations found
        record['stream_compliant'] = len(violations) == 0   # Boolean compliance status
        record['has_violations'] = len(violations) > 0      # Standard violation flag
        
        # Step 2: Apply anonymization for records with violations
        # Only anonymize when violations are detected to preserve data utility
        if violations:
            anonymized_record = self.anonymize_realtime(record, "tokenization")
        else:
            anonymized_record = record  # Keep compliant records unchanged
        
        # Step 3: Update streaming metrics for research evaluation
        self.metrics['processed_records'] += 1
        if violations:
            self.metrics['violations_detected'] += 1
        
        # Track individual record processing time for latency analysis
        processing_time = time.time() - start_time
        self.metrics['processing_times'].append(processing_time)
        
        # Add timing information to the record for downstream analysis
        anonymized_record['record_latency_ms'] = processing_time * 1000
        anonymized_record['processing_time_seconds'] = processing_time
        
        # Step 4: Route processed records to appropriate output topics
        # Note: Commenting out Kafka producer calls to avoid hanging issues
        # In production, these would send to downstream systems
        try:
            # Violations go to special topic for immediate attention
            if violations and self.producer:
                self.producer.send('compliance-violations', anonymized_record)
            
            # All processed records go to main output stream
            if self.producer:
                self.producer.send('processed-stream', anonymized_record)
        except Exception as e:
            # Don't let producer errors stop record processing
            print(f"      ⚠️  Producer send error (non-blocking): {str(e)}")
        
        # Progress reporting for monitoring stream processing performance
        if self.metrics['processed_records'] % 100 == 0:
            avg_time = sum(self.metrics['processing_times'][-100:]) / min(100, len(self.metrics['processing_times']))
            print(f"      📊 Processed {self.metrics['processed_records']} records, "
                  f"Violations: {self.metrics['violations_detected']}, "
                  f"Avg processing time: {avg_time*1000:.2f}ms")
        
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
        """
        # Setup Kafka connections before starting processing
        if not self.setup_kafka():
            print("Failed to setup Kafka connections")
            return
        
        # Initialize processing state and metrics
        self.running = True
        self.metrics['start_time'] = time.time()
        
        print("Starting Storm stream processing...")
        print("Waiting for messages on topics: healthcare-stream, financial-stream")
        
        try:
            # Main processing loop - consume and process messages continuously
            for message in self.consumer:
                if not self.running:
                    break  # Stop processing if shutdown requested
                
                try:
                    # Extract record from Kafka message and process it
                    record = message.value
                    processed_record = self.process_record(record)
                    
                except Exception as e:
                    print(f"Error processing record: {e}")
                    continue  # Skip problematic records and continue processing
        
        except KeyboardInterrupt:
            print("\nStopping stream processing...")
        
        finally:
            # Always cleanup resources when stopping
            self.stop()
    
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
        
        # Calculate final performance metrics for research analysis
        total_time = time.time() - self.metrics['start_time']
        throughput = self.metrics['processed_records'] / total_time if total_time > 0 else 0
        violation_rate = (self.metrics['violations_detected'] / self.metrics['processed_records'] * 100) if self.metrics['processed_records'] > 0 else 0
        avg_processing_time = sum(self.metrics['processing_times']) / len(self.metrics['processing_times']) if self.metrics['processing_times'] else 0
        
        # Display comprehensive results for research comparison
        print("\n=== Stream Processing Complete ===")
        print(f"Total processing time: {total_time:.2f} seconds")
        print(f"Records processed: {self.metrics['processed_records']}")
        print(f"Violations detected: {self.metrics['violations_detected']}")
        print(f"Violation rate: {violation_rate:.1f}%")
        print(f"Throughput: {throughput:.2f} records/second")
        print(f"Average latency: {avg_processing_time*1000:.2f}ms")
    
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