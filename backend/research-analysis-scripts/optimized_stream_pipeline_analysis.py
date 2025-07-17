"""
Optimized Stream Pipeline Research Analysis Script
Tests Apache Storm stream processing with all anonymization configurations using OPTIMIZED streaming infrastructure

This script optimizes the stream processing pipeline by:
- Using predefined topics for each dataset type and size
- Streaming all data once at the beginning to populate topics
- Using different consumer groups for different configurations
- Avoiding redundant data streaming for 110+ experiments
- Reusing existing CSV files from test_data directory

Usage:
    python optimized_stream_pipeline_analysis.py
    
Note: Requires Kafka to be running for stream processing tests
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic, ConfigResource, ConfigResourceType
from kafka.errors import TopicAlreadyExistsError
import threading
import queue

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

# Import for configuration only
try:
    from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
    from src.common.compliance_rules import ComplianceRuleEngine, detailed_compliance_check
except ImportError:
    from common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
    from common.compliance_rules import ComplianceRuleEngine, detailed_compliance_check

class OptimizedStreamPipelineAnalyzer:
    """Optimized stream processing pipeline analyzer with predefined topics and consumer groups"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        self.results_file = os.path.join(output_dir, "stream_pipeline_results.csv")
        
        # Initialize components
        self.data_generator = ResearchDataGenerator()
        self.config_manager = AnonymizationConfigManager()
        self.metrics_collector = ResearchMetricsCollector(self.results_file)
        self.compliance_engine = ComplianceRuleEngine()
        
        # Kafka configuration
        self.kafka_servers = ['localhost:9093']
        
        # Predefined topics for each dataset type and size
        self.topics = self._generate_predefined_topics()
        
        # Consumer groups for each configuration
        self.consumer_groups = self._generate_consumer_groups()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        print("⚡ Optimized Stream Pipeline Analyzer initialized")
        print(f"📊 Results will be saved to: {self.results_file}")
        print(f"🔌 Kafka servers: {self.kafka_servers}")
        print(f"📝 Predefined topics: {len(self.topics)}")
        print(f"👥 Consumer groups: {len(self.consumer_groups)}")
    
    def _generate_predefined_topics(self) -> Dict[str, str]:
        """Generate predefined topic names for each dataset type and size"""
        topics = {}
        dataset_types = ['healthcare', 'financial']
        dataset_sizes = [1000, 2500, 5000, 10000, 20000, 40000, 50000]
        
        for data_type in dataset_types:
            for size in dataset_sizes:
                topic_name = f"{data_type}_{size}"
                topics[f"{data_type}_{size}"] = topic_name
        
        return topics
    
    def _generate_consumer_groups(self) -> Dict[str, str]:
        """Generate consumer group names for each anonymization configuration"""
        consumer_groups = {}
        
        # Get all anonymization configurations
        configs = self.config_manager.get_all_configs()
        dataset_types = ['healthcare', 'financial']
        dataset_sizes = [1000, 2500, 5000, 10000, 20000, 40000, 50000]
        
        for config in configs:
            # Generate consumer group name based on configuration
            if config.method == AnonymizationMethod.K_ANONYMITY:
                config_suffix = f"k_{config.k_value}"
            elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
                config_suffix = f"dp_{str(config.epsilon).replace('.', '_')}"
            elif config.method == AnonymizationMethod.TOKENIZATION:
                config_suffix = f"token_{config.key_length}"
            else:
                config_suffix = "unknown"
            
            # Create consumer group for each dataset type and size
            for data_type in dataset_types:
                for size in dataset_sizes:
                    group_name = f"{config_suffix}_{data_type}_{size}"
                    consumer_groups[f"{config.method.value}_{data_type}_{size}"] = group_name
        
        return consumer_groups

    # ------------------------------------------------------------------
    # Helper method: build unique consumer group suffix for a config
    # ------------------------------------------------------------------
    def _get_config_suffix(self, config: AnonymizationConfig) -> str:
        """Return a unique, human-readable suffix for the given anonymization config"""
        if config.method == AnonymizationMethod.K_ANONYMITY:
            return f"k_{config.k_value}"
        elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
            return f"dp_{str(config.epsilon).replace('.', '_')}"
        elif config.method == AnonymizationMethod.TOKENIZATION:
            return f"token_{config.key_length}"
        return "unknown"
    
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
    
    def create_all_topics(self) -> bool:
        """Create all predefined topics"""
        print("\n📝 Creating predefined topics...")
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_servers,
                client_id="topic-creator"
            )
            
            # Create NewTopic objects for all predefined topics
            new_topics = []
            for topic_key, topic_name in self.topics.items():
                new_topics.append(NewTopic(
                    name=topic_name,
                    num_partitions=1,
                    replication_factor=1
                ))
            
            # Create topics
            try:
                admin_client.create_topics(new_topics)
                print(f"✅ Created {len(new_topics)} predefined topics")
            except TopicAlreadyExistsError:
                print(f"✅ Topics already exist ({len(new_topics)} topics)")
            
            admin_client.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create topics: {str(e)}")
            return False
    
    def stream_all_data_once(self) -> bool:
        """Stream all data once to populate all topics"""
        print("\n🌊 Streaming all data once to populate topics...")
        
        try:
            # Get all datasets
            datasets = self.data_generator.generate_test_datasets()
            
            # Create producer
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            
            # Stream each dataset to its corresponding topic
            for dataset_info in datasets:
                topic_key = f"{dataset_info['type']}_{dataset_info['size']}"
                topic_name = self.topics[topic_key]
                
                # Load and stream data
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
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive stream pipeline analysis with optimized streaming
        
        Returns:
            Summary of all experiments
        """
        print("\n" + "="*70)
        print("🔬 STARTING OPTIMIZED STREAM PIPELINE ANALYSIS")
        print("="*70)
        
        # Check Kafka connectivity
        if not self._check_kafka_connectivity():
            print("❌ Kafka connectivity failed. Please ensure Kafka is running.")
            return {"error": "Kafka connectivity failed"}
        
        # Create all predefined topics
        if not self.create_all_topics():
            print("❌ Failed to create topics.")
            return {"error": "Topic creation failed"}
        
        # Stream all data once to populate topics
        if not self.stream_all_data_once():
            print("❌ Failed to stream data.")
            return {"error": "Data streaming failed"}
        
        # Get test datasets metadata (no regeneration needed)
        datasets = self.data_generator.generate_test_datasets()
        print(f"✅ Using {len(datasets)} existing test datasets")
        
        # Get all anonymization configurations
        anonymization_configs = self.config_manager.get_all_configs()
        print(f"✅ Testing {len(anonymization_configs)} anonymization configurations")
        
        # Calculate total experiments
        total_experiments = len(datasets) * len(anonymization_configs)
        print(f"📊 Total experiments to run: {total_experiments}")
        
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
                    # Run single experiment with optimized streaming
                    success = self._run_single_optimized_experiment(dataset_info, anonymization_config)
                    
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
                        pipeline_type="stream_optimized",
                        dataset_info=dataset_info,
                        anonymization_config=anonymization_config,
                        timing_results={},
                        processing_results={},
                        success=False,
                        error_message=str(e)
                    )
        
        # Generate summary
        summary = self.metrics_collector.get_experiment_summary()
        summary.update({
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments,
            'success_rate': successful_experiments / total_experiments if total_experiments > 0 else 0
        })
        
        print(f"\n🎉 Stream pipeline analysis complete!")
        print(f"📊 Results: {successful_experiments}/{total_experiments} successful")
        print(f"📈 Success rate: {summary['success_rate']:.2%}")
        
        return summary
    
    def _run_single_optimized_experiment(self, dataset_info: Dict[str, Any], anonymization_config: AnonymizationConfig) -> bool:
        """
        Run a single optimized streaming experiment using predefined topics and consumer groups
        
        Args:
            dataset_info: Dataset information including file path and size
            anonymization_config: Anonymization configuration to test
            
        Returns:
            True if experiment succeeded, False otherwise
        """
        try:
            # PRE-PROCESSING (not timed for research)
            with TimingUtilities.time_section("pre_processing") as pre_timer:
                # Get topic and consumer group for this experiment
                topic_key = f"{dataset_info['type']}_{dataset_info['size']}"
                topic_name = self.topics[topic_key]
                
                # Generate unique consumer group name for this configuration
                config_suffix = self._get_config_suffix(anonymization_config)
                consumer_group = f"{config_suffix}_{dataset_info['type']}_{dataset_info['size']}"
                
                total_records = dataset_info['size']
                initial_memory = TimingUtilities.measure_memory_usage()
                data_type = 'healthcare' if dataset_info['type'] == 'healthcare' else 'financial'
                
                # Initialize streaming processor
                from src.stream.storm_processor import StormStreamProcessor
                processor = StormStreamProcessor(self.kafka_servers)
                
                # Setup result collection
                processed_records = []
                result_queue = queue.Queue()
                
                print(f"       🔗 Using topic: {topic_name}")
                print(f"       👥 Using consumer group: {consumer_group}")
            
            # PURE STREAMING PROCESSING (timed for research)
            with TimingUtilities.time_section("pure_streaming") as stream_timer:
                # Create consumer with specific group ID (this is the key optimization)
                consumer = KafkaConsumer(
                    topic_name,
                    bootstrap_servers=self.kafka_servers,
                    auto_offset_reset='earliest',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    consumer_timeout_ms=30000,
                    group_id=consumer_group,  # This ensures each config gets its own consumer group
                    enable_auto_commit=True,
                    auto_commit_interval_ms=1000
                )
                
                # Process messages from the predefined topic
                streaming_start = time.time()
                
                message_count = 0
                for message in consumer:
                    message_count += 1
                    record = message.value
                    
                    # Process with StormStreamProcessor
                    processed_record = processor.process_record(record, anonymization_config)
                    processed_records.append(processed_record)
                    
                    # Stop when we've processed expected number of messages
                    if message_count >= total_records:
                        break
                
                consumer.close()
                
                streaming_end = time.time()
                pure_streaming_time = streaming_end - streaming_start
                
                print(f"       ✅ Processed {message_count} messages in {pure_streaming_time:.3f}s")
            
            # POST-PROCESSING (not timed for research)
            with TimingUtilities.time_section("post_processing") as post_timer:
                # Calculate metrics
                # OPTION A — quick flag-based check (commented out for future debugging)
                # flag_detected = sum(
                #     1 for r in processed_records
                #     if str(r.get('has_violations', '')).lower() == 'true'
                # )

                # OPTION B — authoritative rule-engine check (active by default)
                from common.compliance_rules import detailed_compliance_check
                violations_detected = sum(
                    1 for r in processed_records
                    if not detailed_compliance_check(r, dataset_info['type'])['compliant']
                )
                final_memory = TimingUtilities.measure_memory_usage()
                cpu_usage = TimingUtilities.measure_cpu_usage()
                
                # Calculate streaming-specific metrics
                if processed_records:
                    processing_times = [r.get('pure_processing_time', 0) for r in processed_records]
                    avg_latency = np.mean(processing_times) if processing_times else 0
                    max_latency = np.max(processing_times) if processing_times else 0
                    min_latency = np.min(processing_times) if processing_times else 0
                    latency_std = np.std(processing_times) if processing_times else 0
                else:
                    avg_latency = max_latency = min_latency = latency_std = 0
                
                # Estimate utility metrics
                information_loss = 0.3 if violations_detected > 0 else 0
                utility_preservation = 0.7 if violations_detected > 0 else 1.0
                privacy_level = 0.8 if violations_detected > 0 else 0.5
            
            # Compile timing results
            timing_results = {
                'pure_processing_time': stream_timer.duration,
                'pre_processing_time': pre_timer.duration,
                'post_processing_time': post_timer.duration,
                'total_time': pre_timer.duration + stream_timer.duration + post_timer.duration
            }
            
            # Compile processing results
            processing_results = {
                'total_records': total_records,
                'processed_records': len(processed_records),
                'violations_detected': violations_detected,
                'violation_rate': violations_detected / total_records if total_records > 0 else 0,
                'memory_usage_mb': final_memory - initial_memory,
                'cpu_usage_percent': cpu_usage,
                'information_loss_score': information_loss,
                'utility_preservation_score': utility_preservation,
                'privacy_level_score': privacy_level,
                'avg_latency_ms': avg_latency * 1000,
                'max_latency_ms': max_latency * 1000,
                'min_latency_ms': min_latency * 1000,
                'latency_std_ms': latency_std * 1000,
                'records_per_second': total_records / stream_timer.duration if stream_timer.duration > 0 else 0
            }
            
            # Record experiment
            self.metrics_collector.record_experiment(
                pipeline_type="stream_optimized",
                dataset_info=dataset_info,
                anonymization_config=anonymization_config,
                timing_results=timing_results,
                processing_results=processing_results,
                success=True,
                notes=f"Optimized streaming - Topic: {topic_name}, Consumer Group: {consumer_group}, Throughput: {processing_results['records_per_second']:.0f} rec/sec"
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Optimized streaming experiment failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_topics_and_consumer_groups(self) -> Dict[str, Any]:
        """Get comprehensive list of all topics and consumer groups"""
        return {
            'topics': self.topics,
            'total_topics': len(self.topics),
            'total_consumer_groups': 110  # 11 configs × 10 datasets
        }
    
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
                'total_experiments': len(size_data)
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
            'overall_stats': overall_stats,
            'optimization_note': 'Results generated using optimized streaming with predefined topics and consumer groups'
        }


def main():
    """Main function to run optimized stream pipeline analysis"""
    print("🔬 Optimized Stream Pipeline Research Analysis")
    print("="*50)
    
    # Create directory structure
    create_research_directory_structure()
    
    # Initialize analyzer
    analyzer = OptimizedStreamPipelineAnalyzer()
    
    # Print topics and consumer groups
    print("\n📝 Topics and Consumer Groups:")
    topics_info = analyzer.get_topics_and_consumer_groups()
    print(f"  • Total topics: {topics_info['total_topics']}")
    print(f"  • Total consumer groups: {topics_info['total_consumer_groups']}")
    
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
        print("\n📈 Optimized Stream Performance Analysis:")
        print(f"  • Total successful experiments: {analysis['overall_stats']['total_experiments']}")
        print(f"  • Average processing time: {analysis['overall_stats']['avg_processing_time']:.3f}s")
        print(f"  • Average throughput: {analysis['overall_stats']['avg_records_per_second']:.2f} records/sec")
        print(f"  • Average latency: {analysis['overall_stats']['avg_latency_ms']:.2f}ms")
        print(f"  • Best performing method: {analysis['overall_stats']['best_throughput']['method']}")
        print(f"  • Peak throughput: {analysis['overall_stats']['best_throughput']['records_per_second']:.2f} records/sec")
        print(f"  • Best latency method: {analysis['overall_stats']['best_latency']['method']}")
        print(f"  • Lowest latency: {analysis['overall_stats']['best_latency']['avg_latency_ms']:.2f}ms")
        
        print("\n🔧 Method Comparison:")
        for method, stats in analysis['method_analysis'].items():
            print(f"  • {method}: {stats['avg_records_per_second']:.2f} records/sec, {stats['avg_latency_ms']:.2f}ms latency")
    
    # Print topics and consumer groups for documentation
    print("\n📋 Generated Topics and Consumer Groups:")
    print(f"Topics: {list(topics_info['topics'].values())}")
    print(f"Consumer Groups: {list(topics_info['consumer_groups'].values())}")
    
    print("\n🎉 Optimized stream pipeline analysis complete!")
    print(f"📊 Results saved to: {analyzer.results_file}")


if __name__ == "__main__":
    main() 