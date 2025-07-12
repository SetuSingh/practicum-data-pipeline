"""
Flink Hybrid Processing Pipeline
Intelligently routes data between batch and stream processing based on characteristics

This module implements the hybrid processing approach that combines both Research
Questions 1 and 2. It demonstrates intelligent routing between batch and stream
processing modes based on data characteristics, volume, and compliance urgency.

Key Features:
- Intelligent routing between batch and stream processing
- Real-time decision making based on data characteristics
- Adaptive processing based on volume and complexity
- Urgent violation handling via stream processing
- Bulk processing via batch mode for efficiency
- Comprehensive metrics for research comparison

Architecture:
- Input: Unified data stream from multiple sources
- Router: Intelligent decision engine for processing mode selection
- Dual Processing: Both stream and batch capabilities
- Output: Processed data with routing metadata for analysis
"""
import json
import time
import threading
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer  # Kafka for unified data streaming
import pandas as pd  # DataFrame processing for batch operations
import sys
import os

# Import our modular components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
from compliance_rules import quick_compliance_check, detailed_compliance_check
from schemas import get_schema_for_data

class FlinkHybridProcessor:
    def __init__(self, kafka_servers=['localhost:9093']):
        """
        Initialize the hybrid processor with intelligent routing capabilities
        
        Args:
            kafka_servers (list): List of Kafka broker addresses
        """
        self.kafka_servers = kafka_servers  # Kafka cluster configuration
        self.consumer = None                # Kafka consumer for input data
        self.producer = None                # Kafka producer for output data
        self.running = False                # Processing state flag
        
        # Intelligent routing configuration parameters
        # These thresholds determine when to use batch vs stream processing
        self.routing_config = {
            'batch_threshold_records': 1000,  # Route to batch if buffer >1000 records
            'stream_latency_threshold': 0.1,  # Route to stream if <100ms latency required
            'volume_threshold_mb': 10,        # Route to batch if data volume >10MB
            'violation_urgency': True         # Always route violations to stream for immediate handling
        }
        
        # Comprehensive metrics for research evaluation
        # Tracks routing decisions and performance characteristics
        self.metrics = {
            'total_processed': 0,      # Total records processed
            'routed_to_batch': 0,      # Number of records sent to batch processing
            'routed_to_stream': 0,     # Number of records sent to stream processing
            'violations_detected': 0,  # Number of compliance violations found
            'routing_decisions': [],   # Detailed log of routing decisions for analysis
            'start_time': None         # Processing start timestamp
        }
        
        # Thread-safe batch buffer for accumulating records
        self.batch_buffer = []              # Buffer for batch processing
        self.buffer_lock = threading.Lock() # Thread safety for concurrent access
        
        # Setup imports for processing modules
        # This allows the hybrid processor to use both batch and stream capabilities
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'batch'))
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'stream'))
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
    
    def setup_kafka(self):
        """
        Setup Kafka connections for hybrid processing
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Setup consumer for unified input stream
            # All data types flow through 'hybrid-input' topic for intelligent routing
            self.consumer = KafkaConsumer(
                'hybrid-input',
                bootstrap_servers=self.kafka_servers,
                auto_offset_reset='latest',  # Process only new messages for real-time analysis
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))  # JSON deserialization
            )
            
            # Setup producer for multiple output streams
            # Different outputs for batch, stream, and routing metadata
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')  # JSON serialization
            )
            
            print("Flink Kafka setup complete")
            return True
            
        except Exception as e:
            print(f"Failed to setup Kafka: {e}")
            return False
    
    def initialize_connections(self):
        """
        Initialize connections for hybrid processing (standardized method name)
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        return self.setup_kafka()
    
    def analyze_data_characteristics(self, record):
        """
        Analyze data characteristics to determine optimal processing mode
        
        This method implements the intelligent analysis that drives routing
        decisions in the hybrid architecture. It evaluates multiple dimensions
        of the data to make optimal processing choices.
        
        Args:
            record (dict): Input data record to analyze
            
        Returns:
            dict: Characteristics analysis for routing decision
        """
        characteristics = {
            'size_estimate': len(json.dumps(record)),          # Data size in bytes
            'has_violations': self.quick_violation_check(record), # Compliance violations
            'complexity_score': self.calculate_complexity(record), # Processing complexity
            'timestamp': datetime.now()                        # Analysis timestamp
        }
        
        return characteristics
    
    def quick_violation_check(self, record):
        """
        Perform rapid compliance violation detection using modular rules
        
        This method uses the centralized compliance rules for fast violation
        detection in routing decisions, ensuring consistency across all processors.
        
        Args:
            record (dict): Data record to check
            
        Returns:
            bool: True if violations detected, False otherwise
        """
        # Determine data type for appropriate rule selection
        data_type = 'healthcare' if 'patient_name' in record else 'financial'
        
        # Use modular quick compliance check for routing decisions
        return quick_compliance_check(record, data_type)
    
    def check_compliance(self, record):
        """
        Perform compliance checking using modular compliance rules (standardized method name)
        
        This method provides a consistent interface across all processors
        for compliance checking functionality.
        
        Args:
            record (dict): Data record to check
            
        Returns:
            bool: True if violations detected, False otherwise
        """
        return self.quick_violation_check(record)
    
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
    
    def calculate_complexity(self, record):
        """
        Calculate processing complexity score for routing decisions
        
        This method quantifies how computationally expensive the record
        will be to process, helping route complex records to batch
        processing where they can be handled more efficiently.
        
        Args:
            record (dict): Data record to analyze
            
        Returns:
            float: Complexity score (higher = more complex)
        """
        complexity = 0
        
        # More fields increase complexity (each field needs processing)
        complexity += len(record.keys()) * 0.1
        
        # Large text fields add significant complexity
        for value in record.values():
            if isinstance(value, str) and len(value) > 50:
                complexity += 0.2  # Long strings require more processing
        
        # Date/time fields add complexity (parsing and validation)
        for key in record.keys():
            if 'date' in key.lower() or 'time' in key.lower():
                complexity += 0.3  # DateTime processing is computationally expensive
        
        return complexity
    
    def make_routing_decision(self, record, characteristics):
        """
        Make intelligent routing decision between batch and stream processing
        
        This is the core intelligence of the hybrid architecture. It implements
        a decision tree based on multiple factors to optimize processing
        efficiency while ensuring compliance requirements are met.
        
        Args:
            record (dict): Input data record
            characteristics (dict): Analyzed characteristics of the record
            
        Returns:
            dict: Routing decision with justification for research analysis
        """
        # Initialize decision structure with metadata for research tracking
        decision = {
            'record_id': record.get('id', 'unknown'),  # Record identifier for tracking
            'route': 'stream',                         # Default to stream processing
            'reason': 'default',                       # Reason for routing decision
            'characteristics': characteristics,         # Data characteristics that influenced decision
            'timestamp': datetime.now()                # Decision timestamp
        }
        
        # Priority Rule 1: Route violations to stream for immediate response
        # Compliance violations require urgent handling regardless of other factors
        if characteristics['has_violations'] and self.routing_config['violation_urgency']:
            decision['route'] = 'stream'
            decision['reason'] = 'urgent_violation'
            return decision
        
        # Priority Rule 2: Route to batch when buffer reaches threshold
        # High volume benefits from batch processing efficiency
        buffer_size = len(self.batch_buffer)
        if buffer_size >= self.routing_config['batch_threshold_records']:
            decision['route'] = 'batch'
            decision['reason'] = 'volume_threshold'
            return decision
        
        # Priority Rule 3: Route complex data to batch processing
        # Complex records benefit from batch processing optimizations
        if characteristics['complexity_score'] > 1.0:
            decision['route'] = 'batch'
            decision['reason'] = 'high_complexity'
            return decision
        
        # Default Rule: Route to stream for real-time processing
        # Simple, non-urgent records get real-time processing for low latency
        decision['route'] = 'stream'
        decision['reason'] = 'realtime_processing'
        return decision
    
    def process_via_stream(self, record):
        """Process record through stream pipeline"""
        start_time = time.time()
        
        # Simple stream processing (similar to Storm processor)
        processed_record = record.copy()
        processed_record['processed_via'] = 'stream'
        processed_record['processed_at'] = datetime.now().isoformat()
        
        # Quick compliance check and anonymization
        if self.quick_violation_check(record):
            processed_record['anonymized'] = True
            # Simple tokenization using standardized method
            processed_record = self.anonymize_data(processed_record, "tokenization")
        
        processing_time = time.time() - start_time
        processed_record['processing_time_ms'] = processing_time * 1000
        
        # Send to output
        self.producer.send('hybrid-stream-output', processed_record)
        
        return processed_record, processing_time
    
    def process_data(self, record):
        """
        Process data through stream pipeline (standardized method name)
        
        This method provides a consistent interface across all processors
        for data processing functionality.
        
        Args:
            record (dict): Input data record
            
        Returns:
            tuple: (processed_record, processing_time)
        """
        return self.process_via_stream(record)
    
    def add_to_batch_buffer(self, record):
        """Add record to batch buffer"""
        with self.buffer_lock:
            self.batch_buffer.append(record)
            
        # Trigger batch processing if buffer is full
        if len(self.batch_buffer) >= self.routing_config['batch_threshold_records']:
            self.process_batch_buffer()
    
    def process_batch_buffer(self):
        """Process accumulated batch buffer"""
        if not self.batch_buffer:
            return
        
        start_time = time.time()
        
        with self.buffer_lock:
            batch_data = self.batch_buffer.copy()
            self.batch_buffer.clear()
        
        print(f"Processing batch of {len(batch_data)} records...")
        
        # Convert to DataFrame for batch processing
        df = pd.DataFrame(batch_data)
        
        # Simple batch processing
        df['processed_via'] = 'batch'
        df['processed_at'] = datetime.now().isoformat()
        df['batch_size'] = len(batch_data)
        
        # Batch compliance checking
        for idx, row in df.iterrows():
            violations = self.quick_violation_check(row.to_dict())
            df.at[idx, 'has_violations'] = violations
            
            if violations:
                # Anonymize violating records using standardized method
                anonymized_record = self.anonymize_data(row.to_dict(), "tokenization")
                for field in ['ssn', 'phone', 'email', 'patient_name']:
                    if field in anonymized_record:
                        df.at[idx, field] = anonymized_record[field]
        
        processing_time = time.time() - start_time
        df['processing_time_ms'] = processing_time * 1000
        
        # Send batch results
        batch_results = df.to_dict('records')
        for record in batch_results:
            self.producer.send('hybrid-batch-output', record)
        
        print(f"Batch processing complete: {len(batch_results)} records in {processing_time:.2f}s")
        
        return batch_results, processing_time
    
    def start_hybrid_processing(self):
        """Start hybrid processing loop"""
        if not self.setup_kafka():
            return
        
        self.running = True
        self.metrics['start_time'] = time.time()
        
        print("Starting Flink hybrid processing...")
        print("Intelligent routing between batch and stream processing")
        
        # Start batch processing thread
        batch_thread = threading.Thread(target=self.periodic_batch_processing)
        batch_thread.daemon = True
        batch_thread.start()
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    record = message.value
                    
                    # Analyze data characteristics
                    characteristics = self.analyze_data_characteristics(record)
                    
                    # Make routing decision
                    routing_decision = self.make_routing_decision(record, characteristics)
                    self.metrics['routing_decisions'].append(routing_decision)
                    
                    # Route accordingly
                    if routing_decision['route'] == 'stream':
                        processed_record, processing_time = self.process_via_stream(record)
                        self.metrics['routed_to_stream'] += 1
                    
                    elif routing_decision['route'] == 'batch':
                        self.add_to_batch_buffer(record)
                        self.metrics['routed_to_batch'] += 1
                    
                    # Update metrics
                    self.metrics['total_processed'] += 1
                    if characteristics['has_violations']:
                        self.metrics['violations_detected'] += 1
                    
                    # Print progress
                    if self.metrics['total_processed'] % 100 == 0:
                        self.print_progress()
                
                except Exception as e:
                    print(f"Error processing record: {e}")
                    continue
        
        except KeyboardInterrupt:
            print("\nStopping hybrid processing...")
        
        finally:
            self.stop()
    
    def start_processing(self):
        """
        Start processing (standardized method name)
        
        This method provides a consistent interface across all processors
        for starting the processing pipeline.
        """
        return self.start_hybrid_processing()
    
    def periodic_batch_processing(self):
        """Periodically process batch buffer even if not full"""
        while self.running:
            time.sleep(30)  # Process batch every 30 seconds
            if self.batch_buffer:
                self.process_batch_buffer()
    
    def print_progress(self):
        """Print processing progress"""
        total = self.metrics['total_processed']
        stream_pct = (self.metrics['routed_to_stream'] / total * 100) if total > 0 else 0
        batch_pct = (self.metrics['routed_to_batch'] / total * 100) if total > 0 else 0
        violation_pct = (self.metrics['violations_detected'] / total * 100) if total > 0 else 0
        
        print(f"Processed {total} records: "
              f"Stream: {self.metrics['routed_to_stream']} ({stream_pct:.1f}%), "
              f"Batch: {self.metrics['routed_to_batch']} ({batch_pct:.1f}%), "
              f"Violations: {self.metrics['violations_detected']} ({violation_pct:.1f}%)")
    
    def stop(self):
        """Stop hybrid processing"""
        self.running = False
        
        # Process any remaining batch buffer
        if self.batch_buffer:
            self.process_batch_buffer()
        
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        
        # Print final metrics
        total_time = time.time() - self.metrics['start_time']
        total_records = self.metrics['total_processed']
        
        print("\n=== Hybrid Processing Complete ===")
        print(f"Total processing time: {total_time:.2f} seconds")
        print(f"Total records processed: {total_records}")
        print(f"Routed to stream: {self.metrics['routed_to_stream']}")
        print(f"Routed to batch: {self.metrics['routed_to_batch']}")
        print(f"Violations detected: {self.metrics['violations_detected']}")
        print(f"Overall throughput: {total_records/total_time:.2f} records/second")
        
        # Routing decision analysis
        if self.metrics['routing_decisions']:
            reasons = [d['reason'] for d in self.metrics['routing_decisions']]
            reason_counts = {reason: reasons.count(reason) for reason in set(reasons)}
            print("\nRouting decisions:")
            for reason, count in reason_counts.items():
                print(f"  {reason}: {count} ({count/len(reasons)*100:.1f}%)")
    
    def stop_processing(self):
        """
        Stop processing (standardized method name)
        
        This method provides a consistent interface across all processors
        for stopping the processing pipeline.
        """
        return self.stop()

def main():
    """Test the hybrid processor"""
    processor = FlinkHybridProcessor()
    processor.start_hybrid_processing()

if __name__ == "__main__":
    main() 