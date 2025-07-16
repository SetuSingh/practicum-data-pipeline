"""
Batch Pipeline Research Analysis Script
Tests Apache Spark batch processing with all anonymization configurations

This script performs comprehensive research analysis of the batch processing pipeline:
- Tests multiple dataset sizes (500, 1000, 2500, 5000, 10000 records)
- Tests all anonymization configurations (K-anonymity, Differential Privacy, Tokenization)
- Measures pure processing time (excluding I/O operations)
- Uses subprocess for TRUE COLD STARTS (fresh JVM each time)
- Collects research-grade metrics for performance comparison
- Outputs results to CSV for analysis

Usage:
    python batch_pipeline_analysis.py
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add PySpark imports for distributed processing
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import IntegerType, BooleanType

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import research utilities
from research_utils import (
    ResearchDataGenerator,
    AnonymizationConfigManager,
    ResearchMetricsCollector,
    TimingUtilities,
    create_research_directory_structure
)

# Import batch processor
from src.batch.spark_processor import SparkBatchProcessor
from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
from src.common.compliance_rules import ComplianceRuleEngine, detailed_compliance_check

class BatchPipelineAnalyzer:
    """Analyze batch processing pipeline performance with different anonymization configurations"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        self.results_file = os.path.join(output_dir, "batch_pipeline_results.csv")
        
        # Initialize components
        self.data_generator = ResearchDataGenerator()
        self.config_manager = AnonymizationConfigManager()
        self.metrics_collector = ResearchMetricsCollector(self.results_file)
        self.compliance_engine = ComplianceRuleEngine()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        print("🚀 Batch Pipeline Analyzer initialized")
        print(f"📊 Results will be saved to: {self.results_file}")
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive batch pipeline analysis
        
        Returns:
            Summary of all experiments
        """
        print("\n" + "="*70)
        print("🔬 STARTING COMPREHENSIVE BATCH PIPELINE ANALYSIS")
        print("="*70)
        
        # Generate test datasets
        print("\n📁 Generating test datasets...")
        datasets = self.data_generator.generate_test_datasets()
        print(f"✅ Generated {len(datasets)} test datasets")
        
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
                config_description = self.config_manager.get_config_description(anonymization_config)
                print(f"  🔧 Config {config_idx + 1}/{len(anonymization_configs)}: {config_description}")
                
                try:
                    # Run single experiment with TRUE COLD START (subprocess)
                    success = self._run_single_experiment_subprocess(dataset_info, anonymization_config)
                    
                    if success:
                        successful_experiments += 1
                        print(f"     ✅ Success")
                    else:
                        failed_experiments += 1
                        print(f"     ❌ Failed")
                        
                except Exception as e:
                    failed_experiments += 1
                    print(f"     ❌ Error: {str(e)}")
                    
                    # Record failed experiment
                    self.metrics_collector.record_experiment(
                        pipeline_type="batch",
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
            'total_datasets': len(datasets),
            'total_anonymization_configs': len(anonymization_configs),
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments
        })
        
        print("\n" + "="*70)
        print("🎉 BATCH PIPELINE ANALYSIS COMPLETE")
        print("="*70)
        print(f"📊 Total experiments: {total_experiments}")
        print(f"✅ Successful: {successful_experiments}")
        print(f"❌ Failed: {failed_experiments}")
        print(f"📈 Success rate: {successful_experiments/total_experiments*100:.1f}%")
        print(f"📁 Results saved to: {self.results_file}")
        
        return summary
    
    def _run_single_experiment_subprocess(self, dataset_info: Dict[str, Any], anonymization_config: AnonymizationConfig) -> bool:
        """
        Run a single batch processing experiment in a subprocess for TRUE COLD START
        
        Args:
            dataset_info: Dataset information including file path and size
            anonymization_config: Anonymization configuration to test
            
        Returns:
            True if experiment succeeded, False otherwise
        """
        try:
            # Prepare config data for subprocess
            config_data = {
                'method': anonymization_config.method.value,
                'k_value': anonymization_config.k_value,
                'epsilon': anonymization_config.epsilon,
                'key_length': anonymization_config.key_length
            }
            
            # Create the subprocess script
            subprocess_script = f"""
import sys
import os
import time
import pandas as pd
import json
from datetime import datetime

# Add PySpark imports for distributed processing
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import IntegerType, BooleanType

# Add paths for imports
sys.path.append('{os.path.join(os.path.dirname(__file__), '..')}')
sys.path.append('{os.path.join(os.path.dirname(__file__), '..', 'src')}')

from src.batch.spark_processor import SparkBatchProcessor
from src.common.anonymization_engine import AnonymizationConfig, AnonymizationMethod
from src.common.compliance_rules import detailed_compliance_check
from src.common.anonymization_engine import EnhancedAnonymizationEngine

# Parse configuration
import json
config_data = json.loads('''{json.dumps(config_data)}''')
dataset_info = json.loads('''{json.dumps(dataset_info)}''')

# Create anonymization config
method = AnonymizationMethod(config_data['method'])
anonymization_config = AnonymizationConfig(
    method=method,
    k_value=config_data.get('k_value'),
    epsilon=config_data.get('epsilon'),
    key_length=config_data.get('key_length')
)

# Initialize processor (fresh Spark session)
processor = SparkBatchProcessor()

# **CRITICAL: Initialize Spark session before timing starts**
processor._initialize_spark()

# Load dataset (pre-processing, before timing)
input_file = dataset_info['file_path']
df = pd.read_csv(input_file)
records = df.to_dict('records')
total_records = len(records)

# Determine data type for compliance
data_type = 'healthcare' if dataset_info['type'] == 'healthcare' else 'financial'

# PURE PROCESSING (timed for research) - Spark operations start here
start_time = time.time()

# **CRITICAL FIX: Use Spark's distributed processing with proper serialization**
print(f"Processing {{total_records}} records with Spark distributed operations...")

# Load data into Spark DataFrame for distributed processing
spark_df = processor.spark.createDataFrame(df)
total_records = spark_df.count()

# **SOLUTION: Use Spark DataFrame operations instead of RDD with complex closures**
# This avoids serialization issues while still using Spark's distributed processing

# Broadcast the anonymization config data to all workers
config_broadcast = processor.spark.sparkContext.broadcast({{
    'method': config_data['method'],
    'k_value': config_data.get('k_value'),
    'epsilon': config_data.get('epsilon'),
    'key_length': config_data.get('key_length')
}})

# Create a function that can be serialized (no SparkContext references)
def process_record_distributed(row):
    import sys
    import os
    
    # Re-import modules in worker process
    sys.path.append('{os.path.join(os.path.dirname(__file__), '..')}')
    sys.path.append('{os.path.join(os.path.dirname(__file__), '..', 'src')}')
    
    from src.common.anonymization_engine import EnhancedAnonymizationEngine, AnonymizationConfig, AnonymizationMethod
    from src.common.compliance_rules import detailed_compliance_check
    
    # Convert Spark Row to dict
    record_dict = row.asDict()
    
    # Create anonymization config from broadcast data
    broadcast_config = config_broadcast.value
    method = AnonymizationMethod(broadcast_config['method'])
    anonymization_config = AnonymizationConfig(
        method=method,
        k_value=broadcast_config.get('k_value'),
        epsilon=broadcast_config.get('epsilon'),
        key_length=broadcast_config.get('key_length')
    )
    
    # Create engine in worker process
    engine = EnhancedAnonymizationEngine()
    
    # Apply compliance checking
    compliance_result = detailed_compliance_check(record_dict, data_type)
    violations = len(compliance_result['violations'])
    
    # Apply anonymization
    anonymized_record = engine.anonymize_record(record_dict, anonymization_config)
    
    # Add metadata
    anonymized_record['compliance_violations'] = violations
    anonymized_record['is_compliant'] = compliance_result['compliant']
    
    return anonymized_record

# Convert DataFrame to RDD and process with distributed function
rdd = spark_df.rdd
processed_rdd = rdd.map(process_record_distributed)

# Force execution with collect() - this triggers distributed processing
processed_records = processed_rdd.collect()

# Count violations from processed results
violations_detected = sum(1 for record in processed_records if record.get('compliance_violations', 0) > 0)

end_time = time.time()
pure_processing_time = end_time - start_time

# Calculate utility metrics from results
sample_original = records[0] if records else {{}}
sample_anonymized = processed_records[0] if processed_records else {{}}

# Create anonymization config for utility calculation
method = AnonymizationMethod(config_data['method'])
anonymization_config = AnonymizationConfig(
    method=method,
    k_value=config_data.get('k_value'),
    epsilon=config_data.get('epsilon'),
    key_length=config_data.get('key_length')
)

# Create engine for utility calculation
engine = EnhancedAnonymizationEngine()
utility_metrics = engine.calculate_utility_metrics(
    sample_original, sample_anonymized, anonymization_config
)

# Calculate throughput
records_per_second = total_records / pure_processing_time if pure_processing_time > 0 else 0

# Stop Spark session
if processor.spark:
    processor.spark.stop()

# Output results as JSON
result = {{
    'pure_processing_time': pure_processing_time,
    'total_records': total_records,
    'violations_detected': violations_detected,
    'violation_rate': violations_detected / total_records if total_records > 0 else 0,
    'anonymization_overhead': 0,  # Not measured separately in this approach
    'compliance_check_time': 0,   # Not measured separately in this approach
    'information_loss_score': utility_metrics.get('information_loss', 0),
    'utility_preservation_score': utility_metrics.get('utility_preservation', 0),
    'privacy_level_score': utility_metrics.get('privacy_level_score', 0.5),
    'records_per_second': records_per_second
}}

print("RESULT_JSON:" + json.dumps(result))
"""
            
            # Run the test in a separate process for TRUE COLD START
            process = subprocess.Popen(
                [sys.executable, '-c', subprocess_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), '..')
            )
            
            stdout, stderr = process.communicate()
            
            # Extract result from stdout
            result = None
            for line in stdout.split('\n'):
                if line.startswith('RESULT_JSON:'):
                    result = json.loads(line[12:])
                    break
            
            if result is None:
                print(f"❌ Failed to extract results from subprocess")
                if stderr:
                    print(f"Error: {stderr}")
                return False
            
            # Compile timing results
            timing_results = {
                'pure_processing_time': result['pure_processing_time'],
                'pre_processing_time': 0,  # Not measured in subprocess
                'post_processing_time': 0,  # Not measured in subprocess
                'total_time': result['pure_processing_time']
            }
            
            # Compile processing results
            processing_results = {
                'total_records': result['total_records'],
                'violations_detected': result['violations_detected'],
                'violation_rate': result['violation_rate'],
                'memory_usage_mb': 0,  # Not measured in subprocess
                'cpu_usage_percent': 0,  # Not measured in subprocess
                'anonymization_overhead': result['anonymization_overhead'],
                'compliance_check_time': result['compliance_check_time'],
                'information_loss_score': result['information_loss_score'],
                'utility_preservation_score': result['utility_preservation_score'],
                'privacy_level_score': result['privacy_level_score']
            }
            
            # Record experiment
            self.metrics_collector.record_experiment(
                pipeline_type="batch",
                dataset_info=dataset_info,
                anonymization_config=anonymization_config,
                timing_results=timing_results,
                processing_results=processing_results,
                success=True,
                notes=f"TRUE COLD START: Batch processing with {anonymization_config.method.value}"
            )
            
            # Print performance metrics
            print(f"📊 Recorded experiment: {dataset_info['type']}_{dataset_info['size']}_{anonymization_config.method.value}_{int(time.time())}")
            print(f"   📈 Processing rate: {result['records_per_second']:.2f} records/second")
            print(f"   ⏱️  Pure processing time: {result['pure_processing_time']:.3f}s")
            print(f"   🔍 Violations detected: {result['violations_detected']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Subprocess experiment failed: {str(e)}")
            return False
    
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
                'total_experiments': len(method_data)
            }
        
        # Analysis by dataset size
        size_analysis = {}
        for size in successful_df['dataset_size'].unique():
            size_data = successful_df[successful_df['dataset_size'] == size]
            
            size_analysis[size] = {
                'avg_processing_time': size_data['pure_processing_time_seconds'].mean(),
                'avg_records_per_second': size_data['records_per_second'].mean(),
                'scaling_efficiency': size_data['records_per_second'].mean() / size
            }
        
        # Overall statistics
        overall_stats = {
            'total_experiments': len(successful_df),
            'avg_processing_time': successful_df['pure_processing_time_seconds'].mean(),
            'avg_records_per_second': successful_df['records_per_second'].mean(),
            'best_performance': {
                'method': successful_df.loc[successful_df['records_per_second'].idxmax(), 'anonymization_method'],
                'records_per_second': successful_df['records_per_second'].max()
            }
        }
        
        return {
            'method_analysis': method_analysis,
            'size_analysis': size_analysis,
            'overall_stats': overall_stats,
            'results_file': self.results_file
        }

def main():
    """Main function to run batch pipeline analysis"""
    print("🔬 Batch Pipeline Research Analysis")
    print("="*50)
    
    # Create directory structure
    create_research_directory_structure()
    
    # Initialize analyzer
    analyzer = BatchPipelineAnalyzer()
    
    # Run comprehensive analysis
    summary = analyzer.run_comprehensive_analysis()
    
    # Analyze results
    print("\n📊 Analyzing results...")
    analysis = analyzer.analyze_results()
    
    if 'error' not in analysis:
        print("\n📈 Performance Analysis:")
        print(f"  • Total successful experiments: {analysis['overall_stats']['total_experiments']}")
        print(f"  • Average processing time: {analysis['overall_stats']['avg_processing_time']:.3f}s")
        print(f"  • Average throughput: {analysis['overall_stats']['avg_records_per_second']:.2f} records/sec")
        print(f"  • Best performing method: {analysis['overall_stats']['best_performance']['method']}")
        print(f"  • Peak throughput: {analysis['overall_stats']['best_performance']['records_per_second']:.2f} records/sec")
        
        print("\n🔧 Method Comparison:")
        for method, stats in analysis['method_analysis'].items():
            print(f"  • {method}: {stats['avg_records_per_second']:.2f} records/sec")
    
    print(f"\n📁 Detailed results saved to: {analyzer.results_file}")
    print("🎉 Batch pipeline analysis complete!")

if __name__ == "__main__":
    main() 