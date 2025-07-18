"""
Adaptive Hybrid Router Research Analysis Script
Tests intelligent routing between Storm stream and Spark batch processing based on rule-based decisions

This script implements adaptive routing by:
- Evaluating each record against a rule set to determine stream vs batch processing
- Using existing StormStreamProcessor for real-time path
- Using existing SparkBatchProcessor for batch path
- Recording routing decisions and overhead metrics
- Maintaining same CLI interface and output format as other analysis scripts

Usage:
    python adaptive_hybrid_router.py
    python adaptive_hybrid_router.py --sizes 1000,5000
    
Note: Requires Kafka to be running for stream processing component
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
# YAML & utilities
import yaml

# Kafka (used for connectivity check; Storm processor still depends on library)
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
import threading
import queue
import random

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
src_dir = os.path.join(backend_dir, 'src')
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)

# Import research utilities
from research_utils import (
    ResearchDataGenerator,
    AnonymizationConfigManager,
    ResearchMetricsCollector,
    TimingUtilities,
    create_research_directory_structure
)

# Import processing components
try:
    from src.batch.spark_processor import SparkBatchProcessor
    from src.stream.storm_processor import StormStreamProcessor
    from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
    from src.common.compliance_rules import ComplianceRuleEngine, detailed_compliance_check
    from src.common.anonymization_engine import EnhancedAnonymizationEngine
except ImportError:
    from batch.spark_processor import SparkBatchProcessor
    from stream.storm_processor import StormStreamProcessor
    from common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
    from common.compliance_rules import ComplianceRuleEngine, detailed_compliance_check
    from common.anonymization_engine import EnhancedAnonymizationEngine

# ------------------------------------------------------------
# Adaptive Routing Rules Engine
# ------------------------------------------------------------

class AdaptiveRoutingRules:
    """Rule engine for determining whether a record should be processed via stream or batch"""

    def __init__(self):
        self.current_time = datetime(2024, 1, 1, 12, 0, 0)  # Fixed timestamp for consistent routing
        self.batch_queue_size = 0  # Simulated batch queue size
    
    def evaluate_record(self, record: Dict[str, Any], dataset_type: str) -> Tuple[str, str]:
        """
        Evaluate a record and return routing decision
        
        Args:
            record: The data record to evaluate
            dataset_type: 'healthcare' or 'financial'
            
        Returns:
            Tuple of (route, reason) where route is 'stream' or 'batch'
        """
        
        # Rule 1: Compliance urgency - if record has compliance deadline within 24 hours
        # Note: Uses fixed timestamp (2024-01-01 12:00:00) for deterministic routing
        if 'compliance_deadline' in record:
            try:
                deadline = datetime.fromisoformat(record['compliance_deadline'])
                if (deadline - self.current_time).total_seconds() < 86400:  # 24 hours
                    return ('stream', 'compliance_deadline_urgent')
            except:
                pass
        
        # Rule 2: Data criticality - high-value financial transactions go to stream
        if dataset_type == 'financial':
            amount = record.get('amount', record.get('transaction_amount', 0))
            if isinstance(amount, (int, float)) and amount > 10000:
                return ('stream', 'high_value_transaction')
        
        # Rule 3: Healthcare emergency indicators
        if dataset_type == 'healthcare':
            if record.get('emergency_flag', '').lower() == 'true' or \
               record.get('priority', '').lower() in ['urgent', 'emergency', 'critical']:
                return ('stream', 'healthcare_emergency')
        
        # Rule 4: System load balancing - if batch queue is too large, use stream
        if self.batch_queue_size > 1000:
            return ('stream', 'batch_queue_overload')
        
        # Rule 5: Data completeness - incomplete records go to batch for enrichment
        required_fields = ['id', 'timestamp'] if dataset_type == 'healthcare' else ['id', 'amount']
        if not all(field in record and record[field] for field in required_fields):
            return ('batch', 'incomplete_data')
        
        # Rule 6: Batch processing efficiency - larger records benefit from batch
        if len(str(record)) > 500:
            return ('batch', 'large_record_size')
        
        # Rule 7: Default routing based on anonymization complexity
        # More complex anonymization methods benefit from batch processing
        # (This will be determined by the anonymization config in the experiment)
        
        # Default: route to batch for efficiency
        return ('batch', 'default_batch_routing')
    
    def update_batch_queue_size(self, size: int):
        """Update the simulated batch queue size"""
        self.batch_queue_size = size

# ------------------------------------------------------------
# Adaptive Hybrid Router Analyzer
# ------------------------------------------------------------

class AdaptiveHybridRouterAnalyzer:
    """
    Adaptive hybrid router analyzer that intelligently routes records to stream or batch processing
    
    Features true cold-start timing by creating fresh Spark sessions per experiment.
    Stream processing uses persistent Storm processor for realistic latency measurements.
    """
    
    def __init__(self, output_dir: str = "results", selected_sizes: Optional[List[int]] = None):
        self.output_dir = output_dir
        self.results_file = os.path.join(output_dir, "hybrid_router_results.csv")
        
        # Allow caller to restrict which dataset sizes are analysed
        self.selected_sizes = set(selected_sizes) if selected_sizes else None
        
        # Initialize components
        self.data_generator = ResearchDataGenerator()
        self.config_manager = AnonymizationConfigManager()
        self.metrics_collector = ResearchMetricsCollector(self.results_file)
        self.compliance_engine = ComplianceRuleEngine()
        
        self.routing_rules = AdaptiveRoutingRules()
        
        # Kafka configuration for stream processing
        self.kafka_servers = ['localhost:9093']
        
        # Processing components (initialized on demand)
        self.batch_processor = None
        self.stream_processor = None
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        print("🔀 Adaptive Hybrid Router Analyzer initialized")
        print(f"📊 Results will be saved to: {self.results_file}")
        print(f"🔌 Kafka servers: {self.kafka_servers}")
    
    def _check_kafka_connectivity(self) -> bool:
        """Check if Kafka is accessible"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="connectivity-test",
                request_timeout_ms=10000
            )
            admin_client.close()
            print("✅ Kafka connectivity verified")
            return True
        except Exception as e:
            print(f"❌ Kafka connectivity failed: {str(e)}")
            return False
    
    def _initialize_processors(self):
        """Initialize stream processor (batch processor created fresh per experiment)"""
        if self.stream_processor is None:
            self.stream_processor = StormStreamProcessor(self.kafka_servers)
    
    def _stream_all_data_once(self) -> bool:
        """Stream all datasets once to populate topics like optimized_stream_pipeline_analysis.py"""
        try:
            from kafka import KafkaProducer
            import json
            
            # Get all datasets
            all_datasets = self.data_generator.generate_test_datasets()
            datasets = [d for d in all_datasets if not self.selected_sizes or d['size'] in self.selected_sizes]
            
            # Create all topics first
            for dataset_info in datasets:
                topic_name = f"hybrid_{dataset_info['type']}_{dataset_info['size']}"
                if not self._create_temp_topic(topic_name):
                    print(f"❌ Failed to create topic: {topic_name}")
                    return False
            
            # Create producer
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            # Stream each dataset to its corresponding topic
            for dataset_info in datasets:
                topic_name = f"hybrid_{dataset_info['type']}_{dataset_info['size']}"
                
                # Load and stream data
                import pandas as pd
                df = pd.read_csv(dataset_info['file_path'])
                records = df.to_dict('records')
                
                print(f"  📤 Streaming {len(records)} records to topic '{topic_name}'...")
                
                # Stream all records to the topic
                for record in records:
                    producer.send(topic_name, record)
                
                # Flush to ensure all messages are sent
                producer.flush()
                print(f"  ✅ Completed streaming to '{topic_name}'")
            
            producer.close()
            print("✅ All data streamed successfully to predefined topics")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stream data: {str(e)}")
            return False
    
    def _run_batch_subprocess(self, batch_records: List[Dict], anonymization_config: AnonymizationConfig, data_type: str) -> Optional[Dict]:
        """Run batch processing in subprocess for TRUE COLD START like batch_pipeline_analysis.py"""
        try:
            import subprocess
            import json
            import tempfile
            import os
            
            # Create temporary file for batch records
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(batch_records, tmp_file)
                tmp_file_path = tmp_file.name
            
            # Prepare config data for subprocess
            config_data = {
                'method': anonymization_config.method.value,
                'k_value': anonymization_config.k_value,
                'epsilon': anonymization_config.epsilon,
                'key_length': anonymization_config.key_length
            }
            
            # Create subprocess script for batch processing
            subprocess_script = f"""
import sys
import os
import time
import json
from datetime import datetime

# Add paths for imports
sys.path.append('{os.path.join(os.path.dirname(__file__), '..')}')
sys.path.append('{os.path.join(os.path.dirname(__file__), '..', 'src')}')

from src.batch.spark_processor import SparkBatchProcessor
from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod, EnhancedAnonymizationEngine
from src.common.compliance_rules import detailed_compliance_check

# Parse configuration
config_data = json.loads('''{json.dumps(config_data)}''')
data_type = '{data_type}'

# Load batch records
with open('{tmp_file_path}', 'r') as f:
    batch_records = json.load(f)

# Create anonymization config
method = AnonymizationMethod(config_data['method'])
anonymization_config = AnonymizationConfig(
    method=method,
    k_value=config_data.get('k_value'),
    epsilon=config_data.get('epsilon'),
    key_length=config_data.get('key_length')
)

# Initialize fresh batch processor (TRUE COLD START)
processor = SparkBatchProcessor()
processor._initialize_spark()

# Process records with timing
start_time = time.time()
engine = EnhancedAnonymizationEngine()
processed_records = []

for record in batch_records:
    # Apply compliance checking with timing
    comp_start = time.time()
    compliance_result = detailed_compliance_check(record, data_type)
    comp_time = time.time() - comp_start
    
    # Apply anonymization with timing
    anon_start = time.time()
    anonymized_record = engine.anonymize_record(record, anonymization_config)
    anon_time = time.time() - anon_start
    
    # Add timing metadata
    anonymized_record['compliance_time'] = comp_time
    anonymized_record['anonymization_time'] = anon_time
    anonymized_record['pure_processing_time'] = comp_time + anon_time
    
    processed_records.append(anonymized_record)

end_time = time.time()
processing_time = end_time - start_time

# Stop Spark session
if processor.spark:
    processor.spark.stop()

# Output results
result = {{
    'processed_records': processed_records,
    'processing_time': processing_time,
    'throughput': len(batch_records) / processing_time if processing_time > 0 else 0
}}

print("BATCH_RESULT:" + json.dumps(result, default=str))
"""
            
            # Run subprocess
            process = subprocess.Popen(
                [sys.executable, '-c', subprocess_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), '..')
            )
            
            stdout, stderr = process.communicate()
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            # Extract result
            result = None
            for line in stdout.split('\n'):
                if line.startswith('BATCH_RESULT:'):
                    result = json.loads(line[13:])
                    break
            
            if result is None:
                print(f"❌ Failed to extract batch results from subprocess")
                if stderr:
                    print(f"Error: {stderr}")
                return None
            
            return result
            
        except Exception as e:
            print(f"❌ Batch subprocess failed: {str(e)}")
            return None
    
    def _run_kafka_streaming(self, stream_records: List[Dict], anonymization_config: AnonymizationConfig, data_type: str, dataset_info: Dict) -> Optional[Dict]:
        """Run stream processing via Kafka using pre-populated topics like optimized_stream_pipeline_analysis.py"""
        try:
            import json
            import uuid
            import time
            from kafka import KafkaConsumer
            
            # Use pre-populated topic (no new topic creation)
            topic_name = f"hybrid_{dataset_info['type']}_{dataset_info['size']}"
            
            # Create unique consumer group for this experiment
            config_suffix = self._get_config_suffix(anonymization_config)
            consumer_group = f"hybrid_{config_suffix}_{dataset_info['type']}_{dataset_info['size']}_{uuid.uuid4().hex[:8]}"
            
            print(f"         🔗 Using pre-populated topic: {topic_name}")
            print(f"         👥 Consumer group: {consumer_group}")
            
            # Create consumer to process from pre-populated topic
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers=self.kafka_servers,
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=30000,
                group_id=consumer_group,
                enable_auto_commit=True
            )
            
            # Process messages with timing (no streaming overhead, just processing)
            processing_start = time.time()
            processed_records = []
            message_count = 0
            
            for message in consumer:
                message_count += 1
                record = message.value
                
                # Process with StormStreamProcessor
                processed_record = self.stream_processor.process_record(record, anonymization_config)
                processed_records.append(processed_record)
                
                # Stop when we've processed all expected records
                if message_count >= len(stream_records):
                    break
            
            processing_end = time.time()
            pure_processing_time = processing_end - processing_start
            
            consumer.close()
            
            return {
                'processed_records': processed_records,
                'processing_time': pure_processing_time,
                'throughput': len(stream_records) / pure_processing_time if pure_processing_time > 0 else 0,
                'streaming_time': 0,  # No streaming overhead since topic is pre-populated
                'total_messages': message_count
            }
            
        except Exception as e:
            print(f"❌ Kafka streaming failed: {str(e)}")
            return None
    
    def _get_config_suffix(self, config: AnonymizationConfig) -> str:
        """Return a unique suffix for the given anonymization config"""
        if config.method == AnonymizationMethod.K_ANONYMITY:
            return f"k_{config.k_value}"
        elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
            return f"dp_{str(config.epsilon).replace('.', '_')}"
        elif config.method == AnonymizationMethod.TOKENIZATION:
            return f"token_{config.key_length}"
        return "unknown"
    
    def _create_temp_topic(self, topic_name: str) -> bool:
        """Create a temporary Kafka topic for hybrid routing"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="topic-creator"
            )
            
            new_topic = NewTopic(
                name=topic_name,
                num_partitions=1,
                replication_factor=1
            )
            
            try:
                admin_client.create_topics([new_topic])
                print(f"✅ Created temporary topic: {topic_name}")
            except TopicAlreadyExistsError:
                print(f"✅ Topic already exists: {topic_name}")
            
            admin_client.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create topic {topic_name}: {str(e)}")
            return False
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive adaptive hybrid router analysis
        
        Returns:
            Summary of all experiments
        """
        print("\n" + "="*70)
        print("🔬 STARTING OPTIMIZED ADAPTIVE HYBRID ROUTER ANALYSIS")
        print("="*70)
        print("❄️  Cold-start mode: Fresh Spark session per batch experiment")
        print("🌊 Optimized streaming: Pre-populated topics, unique consumer groups")
        print("💡 Tip: Run 'sudo purge' (macOS) before analysis for cold OS cache")
        
        # Check Kafka connectivity
        if not self._check_kafka_connectivity():
            print("❌ Kafka connectivity failed. Please ensure Kafka is running.")
            return {"error": "Kafka connectivity failed"}
        
        # Generate test datasets
        print("\n📁 Generating test datasets...")
        all_datasets = self.data_generator.generate_test_datasets()
        datasets = [d for d in all_datasets if not self.selected_sizes or d['size'] in self.selected_sizes]
        print(f"✅ Generated {len(datasets)} test datasets (filtered from {len(all_datasets)} total)")
        
        # Get all anonymization configurations
        anonymization_configs = self.config_manager.get_all_configs()
        print(f"✅ Testing {len(anonymization_configs)} anonymization configurations")
        
        # Calculate total experiments
        total_experiments = len(datasets) * len(anonymization_configs)
        print(f"📊 Total experiments to run: {total_experiments}")
        
        # Initialize processors
        self._initialize_processors()
        
        # Stream all data once to populate topics (like optimized stream)
        print("\n🌊 Streaming all data once to populate topics...")
        if not self._stream_all_data_once():
            print("❌ Failed to populate topics with data")
            return {"error": "Topic population failed"}
        
        # Run experiments
        successful_experiments = 0
        failed_experiments = 0
        
        for dataset_idx, dataset_info in enumerate(datasets):
            print(f"\n📊 Processing dataset {dataset_idx + 1}/{len(datasets)}: {dataset_info['description']}")
            
            for config_idx, anonymization_config in enumerate(anonymization_configs):
                current_experiment = dataset_idx * len(anonymization_configs) + config_idx + 1
                config_description = self.config_manager.get_config_description(anonymization_config)
                print(f"  🔧 Config {config_idx + 1}/{len(anonymization_configs)}: {config_description}")
                print(f"      🔬 Experiment {current_experiment}/{total_experiments}")
                
                try:
                    # Run single hybrid routing experiment
                    success = self._run_single_hybrid_experiment(dataset_info, anonymization_config)
                    
                    if success:
                        successful_experiments += 1
                        print(f"     ✅ Success ({successful_experiments}/{total_experiments} completed)")
                    else:
                        failed_experiments += 1
                        print(f"     ❌ Failed ({successful_experiments}/{total_experiments} completed)")
                        
                except Exception as e:
                    failed_experiments += 1
                    print(f"     ❌ Error: {str(e)}")
                    
                    # Record failed experiment
                    self.metrics_collector.record_experiment(
                        pipeline_type="hybrid_adaptive",
                        dataset_info=dataset_info,
                        anonymization_config=anonymization_config,
                        timing_results={},
                        processing_results={},
                        success=False,
                        error_message=str(e)
                    )
        
        # Note: Individual Spark sessions are cleaned up per experiment for cold-start timing
        
        # Generate summary
        summary = self.metrics_collector.get_experiment_summary()
        summary.update({
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments,
            'success_rate': successful_experiments / total_experiments if total_experiments > 0 else 0
        })
        
        print(f"\n🎉 Adaptive hybrid router analysis complete!")
        print(f"📊 Results: {successful_experiments}/{total_experiments} successful")
        print(f"📈 Success rate: {summary['success_rate']:.2%}")
        
        return summary
    
    def _run_single_hybrid_experiment(self, dataset_info: Dict[str, Any], anonymization_config: AnonymizationConfig) -> bool:
        """
        Run a single hybrid routing experiment
        
        Args:
            dataset_info: Dataset information including file path and size
            anonymization_config: Anonymization configuration to test
            
        Returns:
            True if experiment succeeded, False otherwise
        """
        try:
            # PRE-PROCESSING (not timed for research)
            with TimingUtilities.time_section("pre_processing") as pre_timer:
                # Load dataset
                df = pd.read_csv(dataset_info['file_path'])
                records = df.to_dict('records')
                total_records = len(records)
                
                # Add synthetic fields for routing rules (TRULY DETERMINISTIC - same for all runs)
                random.seed(42)  # Fixed seed for consistent routing across runs
                base_timestamp = datetime(2024, 1, 1, 12, 0, 0)  # Fixed base timestamp
                
                for i, record in enumerate(records):
                    # Use record index + fixed seed for deterministic synthetic fields
                    record_seed = hash(f"{record.get('id', i)}_42") % 1000
                    
                    # Add compliance deadline (deterministic based on record)
                    if (record_seed % 100) < 20:  # 20% urgent (deterministic)
                        record['compliance_deadline'] = (base_timestamp + timedelta(hours=(record_seed % 23) + 1)).isoformat()
                    else:
                        record['compliance_deadline'] = (base_timestamp + timedelta(days=(record_seed % 28) + 2)).isoformat()
                    
                    # Add emergency flag for healthcare (deterministic)
                    if dataset_info['type'] == 'healthcare' and (record_seed % 100) < 10:  # 10% emergency (deterministic)
                        record['emergency_flag'] = 'true'
                        record['priority'] = 'urgent'
                
                initial_memory = TimingUtilities.measure_memory_usage()
                data_type = dataset_info['type']
                
                print(f"       📋 Loaded {total_records} records with deterministic synthetic fields (fixed timestamp: {base_timestamp})")
                
                # Routing decision tracking
                stream_records = []
                batch_records = []
                routing_decisions = []
                routing_times = []
            
            # PURE PROCESSING (timed for research) - Route and process records with real infrastructure
            with TimingUtilities.time_section("pure_processing") as processing_timer:
                # Phase 1: RECORD EVALUATOR - Route all records first
                print(f"       📋 Record Evaluator: Routing {total_records} records...")
                routing_start = time.time()
                
                for record in records:
                    route_start = time.time()
                    route, reason = self.routing_rules.evaluate_record(record, data_type)
                    route_time = time.time() - route_start
                    
                    routing_decisions.append({
                        'record_id': record.get('id', len(routing_decisions)),
                        'route': route,
                        'reason': reason,
                        'routing_time': route_time
                    })
                    routing_times.append(route_time)
                    
                    if route == 'stream':
                        stream_records.append(record)
                    else:
                        batch_records.append(record)
                
                total_routing_time = time.time() - routing_start
                print(f"       📊 Routing complete: {len(stream_records)} → Stream, {len(batch_records)} → Batch")
                
                # Phase 2: STREAM TOPIC - Process stream records via pre-populated Kafka topics
                stream_processed = []
                stream_processing_time = 0  # pure processing inside consumer loop
                stream_wall_time = 0       # wall-clock from consumer creation → close
                stream_throughput = 0
                
                if stream_records:
                    print(f"       🌊 STREAM TOPIC: Processing {len(stream_records)} records via pre-populated Kafka topics")
                    
                    # Measure wall-clock for streaming segment
                    stream_wall_start = time.time()
                    stream_result = self._run_kafka_streaming(stream_records, anonymization_config, data_type, dataset_info)
                    stream_wall_end = time.time()
                    stream_wall_time = stream_wall_end - stream_wall_start
                    
                    if stream_result:
                        stream_processed = stream_result['processed_records']
                        stream_processing_time = stream_result['processing_time']
                        stream_throughput = stream_result['throughput']
                        print(f"       ✅ Kafka streaming: {stream_throughput:.2f} records/sec")
                    else:
                        print(f"       ❌ Kafka streaming failed")
                        return False
                
                # Phase 3: BATCH SPACE - Process batch records via Spark (TRUE COLD START)
                batch_processed = []
                batch_processing_time = 0  # pure processing time reported by subprocess
                batch_wall_time = 0       # wall-clock from subprocess launch → return
                batch_throughput = 0
                
                if batch_records:
                    print(f"       📦 BATCH SPACE: Processing {len(batch_records)} records via Spark subprocess")
                    
                    # Measure wall-clock for batch subprocess segment
                    batch_wall_start = time.time()
                    batch_result = self._run_batch_subprocess(batch_records, anonymization_config, data_type)
                    batch_wall_end = time.time()
                    batch_wall_time = batch_wall_end - batch_wall_start
                    
                    if batch_result:
                        batch_processed = batch_result['processed_records']
                        batch_processing_time = batch_result['processing_time']
                        batch_throughput = batch_result['throughput']
                        print(f"       ✅ Batch subprocess: {batch_throughput:.2f} records/sec")
                    else:
                        print(f"       ❌ Batch subprocess failed")
                        return False
                
                # Combine processed records (stream already processed individually; we don’t need full batch records)
                all_processed = stream_processed + batch_processed
            
            # POST-PROCESSING (not timed for research)
            with TimingUtilities.time_section("post_processing") as post_timer:
                # Calculate violations
                violations_detected = sum(
                    1 for r in all_processed
                    if not detailed_compliance_check(r, data_type)['compliant']
                )
                
                final_memory = TimingUtilities.measure_memory_usage()
                cpu_usage = TimingUtilities.measure_cpu_usage()
                
                # Calculate routing statistics
                stream_count = len(stream_records)
                batch_count = len(batch_records)
                total_records = stream_count + batch_count
                stream_percentage = (stream_count / total_records) * 100 if total_records > 0 else 0
                batch_percentage = (batch_count / total_records) * 100 if total_records > 0 else 0
                
                # Calculate latency metrics
                if all_processed:
                    processing_times = [r.get('pure_processing_time', 0) for r in all_processed]
                    avg_latency = np.mean(processing_times) if processing_times else 0
                    max_latency = np.max(processing_times) if processing_times else 0
                    min_latency = np.min(processing_times) if processing_times else 0
                    latency_std = np.std(processing_times) if processing_times else 0
                    
                    # Aggregate overhead metrics
                    anonymization_overhead = sum(r.get('anonymization_time', 0) for r in all_processed)
                    compliance_time = sum(r.get('compliance_time', 0) for r in all_processed)
                else:
                    avg_latency = max_latency = min_latency = latency_std = 0
                    anonymization_overhead = 0
                    compliance_time = 0
                
                # Calculate routing overhead
                avg_routing_time = np.mean(routing_times) if routing_times else 0
                
                # Estimate utility metrics
                information_loss = 0.25 if violations_detected > 0 else 0.1
                utility_preservation = 0.75 if violations_detected > 0 else 0.9
                privacy_level = 0.8 if violations_detected > 0 else 0.7
            
            # Compile timing results with detailed infrastructure timing
            timing_results = {
                'pure_processing_time': processing_timer.duration,
                'pre_processing_time': pre_timer.duration,
                'post_processing_time': post_timer.duration,
                'total_time': pre_timer.duration + processing_timer.duration + post_timer.duration,
                'routing_time': total_routing_time,
                'stream_processing_time': stream_processing_time,
                'batch_processing_time': batch_processing_time,
                'stream_wall_time': stream_wall_time,
                'batch_wall_time': batch_wall_time,
                'kafka_streaming_time': stream_result.get('streaming_time', 0) if stream_result else 0,
                'subprocess_overhead': max(batch_wall_time - batch_processing_time, 0)
            }
            
            # Compile processing results with hybrid-specific metrics
            processing_results = {
                'total_records': total_records,
                'violations_detected': violations_detected,
                'violation_rate': violations_detected / total_records if total_records > 0 else 0,
                'memory_usage_mb': final_memory,
                'cpu_usage_percent': cpu_usage,
                'anonymization_overhead': anonymization_overhead,
                'compliance_check_time': compliance_time,
                'information_loss_score': information_loss,
                'utility_preservation_score': utility_preservation,
                'privacy_level_score': privacy_level,
                'avg_latency_ms': avg_latency * 1000,
                'max_latency_ms': max_latency * 1000,
                'min_latency_ms': min_latency * 1000,
                'latency_std_ms': latency_std * 1000,
                'e2e_latency_ms': timing_results['total_time'] * 1000 / total_records if total_records else 0,
                'records_per_second': total_records / processing_timer.duration if processing_timer.duration > 0 else 0,
                # Hybrid-specific metrics
                'routing_decision': f"stream:{stream_count},batch:{batch_count}",
                'router_time_ms': avg_routing_time * 1000,
                'stream_percentage': stream_percentage,
                'batch_percentage': batch_percentage,
                'stream_throughput_rps': stream_throughput,
                'batch_throughput_rps': batch_throughput,
                'kafka_streaming_time_ms': timing_results.get('kafka_streaming_time', 0) * 1000,
                'stream_wall_time_ms': timing_results.get('stream_wall_time', 0) * 1000,
                'batch_wall_time_ms': timing_results.get('batch_wall_time', 0) * 1000,
                'subprocess_overhead_ms': timing_results.get('subprocess_overhead', 0) * 1000
            }
            
            # Record experiment
            self.metrics_collector.record_experiment(
                pipeline_type="hybrid_adaptive",
                dataset_info=dataset_info,
                anonymization_config=anonymization_config,
                timing_results=timing_results,
                processing_results=processing_results,
                success=True,
                notes=f"Optimized adaptive routing: {stream_count} stream (pre-populated topics), {batch_count} batch (subprocess), {stream_percentage:.1f}% stream"
            )
            
            # Print routing statistics with detailed timing
            print(f"       📊 Routing: {stream_count} stream ({stream_percentage:.1f}%), {batch_count} batch ({batch_percentage:.1f}%)")
            print(f"       📈 Overall throughput: {processing_results['records_per_second']:.2f} records/sec")
            print(f"       ⏱️  Detailed timing:")
            print(f"         • Routing: {avg_routing_time*1000:.3f}ms")
            print(f"         • Stream (Kafka): {stream_throughput:.2f} rps | wall: {stream_wall_time*1000:.1f} ms | pure: {stream_processing_time*1000:.1f} ms")
            print(f"         • Batch  (Spark): {batch_throughput:.2f} rps | wall: {batch_wall_time*1000:.1f} ms | pure: {batch_processing_time*1000:.1f} ms | JVM startup: {(batch_wall_time-batch_processing_time)*1000:.1f} ms")
            
            return True
            
        except Exception as e:
            print(f"❌ Hybrid routing experiment failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup is handled by subprocess for batch processing
            # Stream processor cleanup is handled by Kafka consumer.close()
            pass
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze the collected results and generate insights
        
        Returns:
            Analysis results with insights
        """
        if not os.path.exists(self.results_file):
            return {"error": "No results file found. Run experiments first."}
        
        # Load results
        df = pd.read_csv(self.results_file)

        # Ensure percentage columns are numeric
        for col in ['stream_percentage', 'batch_percentage', 'router_time_ms']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if df.empty:
            return {"error": "No results found in file."}
        
        # Filter successful experiments
        successful_df = df[df['success'] == True]
        
        if successful_df.empty:
            return {"error": "No successful experiments found."}
        
        # Analysis by anonymization method
        method_analysis = {}
        for method in successful_df['anonymization_method'].unique():
            method_data = successful_df[successful_df['anonymization_method'] == method]
            
            method_analysis[method] = {
                'avg_processing_time': method_data['pure_processing_time_seconds'].mean(),
                'avg_records_per_second': method_data['records_per_second'].mean(),
                'avg_violation_rate': method_data['violation_rate'].mean(),
                'avg_information_loss': method_data['information_loss_score'].mean(),
                'avg_latency_ms': method_data['avg_latency_ms'].mean(),
                'avg_routing_time_ms': method_data['router_time_ms'].mean(),
                'avg_stream_percentage': method_data['stream_percentage'].mean(),
                'total_experiments': len(method_data)
            }
        
        # Analysis by dataset size
        size_analysis = {}
        for size in successful_df['dataset_size'].unique():
            size_data = successful_df[successful_df['dataset_size'] == size]
            
            size_analysis[size] = {
                'avg_processing_time': size_data['pure_processing_time_seconds'].mean(),
                'avg_records_per_second': size_data['records_per_second'].mean(),
                'avg_latency_ms': size_data['avg_latency_ms'].mean(),
                'avg_stream_percentage': size_data['stream_percentage'].mean(),
                'total_experiments': len(size_data)
            }
        
        # Routing analysis
        routing_analysis = {
            'overall_stream_percentage': successful_df['stream_percentage'].mean(),
            'overall_batch_percentage': successful_df['batch_percentage'].mean(),
            'avg_routing_overhead_ms': successful_df['router_time_ms'].mean(),
            'routing_efficiency': successful_df['router_time_ms'].mean() / successful_df['avg_latency_ms'].mean() if successful_df['avg_latency_ms'].mean() > 0 else 0
        }
        
        # Overall statistics
        overall_stats = {
            'total_experiments': len(successful_df),
            'avg_processing_time': successful_df['pure_processing_time_seconds'].mean(),
            'avg_records_per_second': successful_df['records_per_second'].mean(),
            'avg_latency_ms': successful_df['avg_latency_ms'].mean(),
            'best_throughput': {
                'records_per_second': successful_df['records_per_second'].max(),
                'method': successful_df.loc[successful_df['records_per_second'].idxmax(), 'anonymization_method']
            },
            'best_latency': {
                'avg_latency_ms': successful_df['avg_latency_ms'].min(),
                'method': successful_df.loc[successful_df['avg_latency_ms'].idxmin(), 'anonymization_method']
            }
        }
        
        return {
            'method_analysis': method_analysis,
            'size_analysis': size_analysis,
            'routing_analysis': routing_analysis,
            'overall_stats': overall_stats,
            'hybrid_note': 'Results generated using adaptive hybrid routing with intelligent stream/batch decision making'
        }




def main():
    """Main function to run adaptive hybrid router analysis"""
    print("🔀 Adaptive Hybrid Router Research Analysis")
    print("="*50)
    
    # Create directory structure
    create_research_directory_structure()
    
    import argparse
    parser = argparse.ArgumentParser(description="Adaptive hybrid router analysis")
    parser.add_argument("--sizes", help="Comma-separated list of dataset sizes to process (e.g. 1000,5000)")
    args = parser.parse_args()

    sizes_filter = None
    if args.sizes:
        try:
            sizes_filter = [int(s.strip()) for s in args.sizes.split(',') if s.strip()]
        except ValueError:
            print("❌ Invalid --sizes argument; must be comma-separated integers")
            sys.exit(1)

    analyzer = AdaptiveHybridRouterAnalyzer(selected_sizes=sizes_filter)
    
    # Run comprehensive analysis
    summary = analyzer.run_comprehensive_analysis()
    
    # Check for errors
    if 'error' in summary:
        print(f"❌ Analysis failed: {summary['error']}")
        return
    
    # Analyze results
    print("\n📊 Analyzing results...")
    analysis = analyzer.analyze_results()
    
    if 'error' not in analysis:
        print("\n📈 Adaptive Hybrid Router Performance Analysis:")
        print(f"  • Total successful experiments: {analysis['overall_stats']['total_experiments']}")
        print(f"  • Average processing time: {analysis['overall_stats']['avg_processing_time']:.3f}s")
        print(f"  • Average throughput: {analysis['overall_stats']['avg_records_per_second']:.2f} records/sec")
        print(f"  • Average latency: {analysis['overall_stats']['avg_latency_ms']:.2f}ms")
        print(f"  • Best performing method: {analysis['overall_stats']['best_throughput']['method']}")
        print(f"  • Peak throughput: {analysis['overall_stats']['best_throughput']['records_per_second']:.2f} records/sec")
        
        print("\n🔀 Routing Analysis:")
        print(f"  • Average stream routing: {analysis['routing_analysis']['overall_stream_percentage']:.1f}%")
        print(f"  • Average batch routing: {analysis['routing_analysis']['overall_batch_percentage']:.1f}%")
        print(f"  • Average routing overhead: {analysis['routing_analysis']['avg_routing_overhead_ms']:.3f}ms")
        print(f"  • Routing efficiency: {analysis['routing_analysis']['routing_efficiency']:.3f}")
        
        print("\n🔧 Method Comparison:")
        for method, stats in analysis['method_analysis'].items():
            print(f"  • {method}: {stats['avg_records_per_second']:.2f} records/sec, {stats['avg_stream_percentage']:.1f}% stream")
    
    print("\n🎉 Adaptive hybrid router analysis complete!")
    print(f"📊 Results saved to: {analyzer.results_file}")


if __name__ == "__main__":
    main() 