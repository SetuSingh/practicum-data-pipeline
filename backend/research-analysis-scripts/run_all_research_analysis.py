"""
Master Research Analysis Script
Orchestrates all pipeline analysis scripts and generates consolidated results

This script runs comprehensive analysis across all three pipeline types:
- Batch Processing (Apache Spark)
- Stream Processing (Apache Storm)  
- Hybrid Processing (Apache Flink)

It tests all anonymization configurations and dataset sizes, then generates:
- Consolidated CSV with all results
- Comparative analysis report
- Research-grade metrics for paper publication
- Performance benchmarks for each pipeline type

Usage:
    python run_all_research_analysis.py [--batch-only] [--stream-only] [--hybrid-only] [--skip-kafka-check]
"""

import sys
import os
import time
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import matplotlib.pyplot as plt
import seaborn as sns

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import research utilities
from research_utils import (
    ResearchDataGenerator,
    AnonymizationConfigManager,
    create_research_directory_structure
)

# Import individual analyzers
from batch_pipeline_analysis import BatchPipelineAnalyzer
from stream_pipeline_analysis import StreamPipelineAnalyzer
from hybrid_pipeline_analysis import HybridPipelineAnalyzer

class MasterResearchAnalyzer:
    """Master analyzer that orchestrates all pipeline analysis scripts"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        self.consolidated_results_file = os.path.join(output_dir, "consolidated_research_results.csv")
        self.comparison_report_file = os.path.join(output_dir, "pipeline_comparison_report.json")
        self.research_summary_file = os.path.join(output_dir, "research_summary.md")
        
        # Initialize components
        self.data_generator = ResearchDataGenerator()
        self.config_manager = AnonymizationConfigManager()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Analysis results storage
        self.batch_results = None
        self.stream_results = None
        self.hybrid_results = None
        
        print("🔬 Master Research Analyzer initialized")
        print(f"📊 Consolidated results will be saved to: {self.consolidated_results_file}")
        print(f"📋 Comparison report will be saved to: {self.comparison_report_file}")
        print(f"📄 Research summary will be saved to: {self.research_summary_file}")
    
    def run_comprehensive_analysis(self, 
                                 run_batch: bool = True,
                                 run_stream: bool = True,
                                 run_hybrid: bool = True,
                                 skip_kafka_check: bool = False) -> Dict[str, Any]:
        """
        Run comprehensive analysis across all pipeline types
        
        Args:
            run_batch: Whether to run batch analysis
            run_stream: Whether to run stream analysis
            run_hybrid: Whether to run hybrid analysis
            skip_kafka_check: Whether to skip Kafka connectivity check
            
        Returns:
            Summary of all analyses
        """
        print("\n" + "="*80)
        print("🚀 STARTING COMPREHENSIVE MULTI-PIPELINE RESEARCH ANALYSIS")
        print("="*80)
        
        start_time = datetime.now()
        
        # Pre-analysis setup
        print("\n📋 Pre-analysis setup...")
        create_research_directory_structure()
        
        # Generate test datasets once (shared across all pipelines)
        print("📁 Generating shared test datasets...")
        datasets = self.data_generator.generate_test_datasets()
        print(f"✅ Generated {len(datasets)} datasets")
        
        # Get anonymization configurations
        configs = self.config_manager.get_all_configs()
        print(f"✅ Testing {len(configs)} anonymization configurations")
        
        total_experiments = len(datasets) * len(configs)
        print(f"📊 Total experiments per pipeline: {total_experiments}")
        
        # Analysis results
        analysis_results = {}
        
        # Run Batch Analysis
        if run_batch:
            print("\n" + "="*60)
            print("🚀 RUNNING BATCH PIPELINE ANALYSIS")
            print("="*60)
            
            try:
                batch_analyzer = BatchPipelineAnalyzer(self.output_dir)
                batch_summary = batch_analyzer.run_comprehensive_analysis()
                batch_analysis = batch_analyzer.analyze_results()
                
                analysis_results['batch'] = {
                    'summary': batch_summary,
                    'analysis': batch_analysis,
                    'results_file': batch_analyzer.results_file
                }
                
                print("✅ Batch pipeline analysis completed")
                
            except Exception as e:
                print(f"❌ Batch pipeline analysis failed: {str(e)}")
                analysis_results['batch'] = {'error': str(e)}
        
        # Run Stream Analysis
        if run_stream:
            print("\n" + "="*60)
            print("⚡ RUNNING STREAM PIPELINE ANALYSIS")
            print("="*60)
            
            try:
                stream_analyzer = StreamPipelineAnalyzer(self.output_dir)
                stream_summary = stream_analyzer.run_comprehensive_analysis()
                
                if 'error' in stream_summary:
                    if not skip_kafka_check:
                        print(f"❌ Stream pipeline analysis failed: {stream_summary['error']}")
                        analysis_results['stream'] = {'error': stream_summary['error']}
                    else:
                        print("⚠️  Skipping stream analysis due to Kafka connectivity issues")
                        analysis_results['stream'] = {'skipped': 'Kafka connectivity issues'}
                else:
                    stream_analysis = stream_analyzer.analyze_results()
                    analysis_results['stream'] = {
                        'summary': stream_summary,
                        'analysis': stream_analysis,
                        'results_file': stream_analyzer.results_file
                    }
                    print("✅ Stream pipeline analysis completed")
                    
            except Exception as e:
                print(f"❌ Stream pipeline analysis failed: {str(e)}")
                analysis_results['stream'] = {'error': str(e)}
        
        # Run Hybrid Analysis
        if run_hybrid:
            print("\n" + "="*60)
            print("🧠 RUNNING HYBRID PIPELINE ANALYSIS")
            print("="*60)
            
            try:
                hybrid_analyzer = HybridPipelineAnalyzer(self.output_dir)
                hybrid_summary = hybrid_analyzer.run_comprehensive_analysis()
                
                if 'error' in hybrid_summary:
                    if not skip_kafka_check:
                        print(f"❌ Hybrid pipeline analysis failed: {hybrid_summary['error']}")
                        analysis_results['hybrid'] = {'error': hybrid_summary['error']}
                    else:
                        print("⚠️  Skipping hybrid analysis due to Kafka connectivity issues")
                        analysis_results['hybrid'] = {'skipped': 'Kafka connectivity issues'}
                else:
                    hybrid_analysis = hybrid_analyzer.analyze_results()
                    analysis_results['hybrid'] = {
                        'summary': hybrid_summary,
                        'analysis': hybrid_analysis,
                        'results_file': hybrid_analyzer.results_file
                    }
                    print("✅ Hybrid pipeline analysis completed")
                    
            except Exception as e:
                print(f"❌ Hybrid pipeline analysis failed: {str(e)}")
                analysis_results['hybrid'] = {'error': str(e)}
        
        # Generate consolidated results
        print("\n" + "="*60)
        print("📊 GENERATING CONSOLIDATED RESULTS")
        print("="*60)
        
        consolidated_results = self._consolidate_results(analysis_results)
        comparison_report = self._generate_comparison_report(analysis_results)
        research_summary = self._generate_research_summary(analysis_results, start_time)
        
        # Save results
        self._save_consolidated_results(consolidated_results)
        self._save_comparison_report(comparison_report)
        self._save_research_summary(research_summary)
        
        # Generate visualizations
        if consolidated_results is not None:
            self._generate_visualizations(consolidated_results)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("🎉 COMPREHENSIVE MULTI-PIPELINE ANALYSIS COMPLETE")
        print("="*80)
        print(f"⏱️  Total analysis duration: {total_duration:.2f} seconds")
        print(f"📁 Consolidated results: {self.consolidated_results_file}")
        print(f"📋 Comparison report: {self.comparison_report_file}")
        print(f"📄 Research summary: {self.research_summary_file}")
        
        return {
            'analysis_results': analysis_results,
            'consolidated_results': consolidated_results,
            'comparison_report': comparison_report,
            'total_duration': total_duration,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def _consolidate_results(self, analysis_results: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Consolidate results from all pipeline analyses into a single DataFrame
        
        Args:
            analysis_results: Results from all pipeline analyses
            
        Returns:
            Consolidated DataFrame or None if no valid results
        """
        print("📊 Consolidating results from all pipelines...")
        
        consolidated_data = []
        
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                print(f"⚠️  Skipping {pipeline_type} pipeline (error or skipped)")
                continue
            
            results_file = results.get('results_file')
            if not results_file or not os.path.exists(results_file):
                print(f"⚠️  No results file found for {pipeline_type} pipeline")
                continue
            
            try:
                df = pd.read_csv(results_file)
                df['pipeline_type'] = pipeline_type
                consolidated_data.append(df)
                print(f"✅ Consolidated {len(df)} records from {pipeline_type} pipeline")
                
            except Exception as e:
                print(f"❌ Error consolidating {pipeline_type} results: {str(e)}")
                continue
        
        if not consolidated_data:
            print("❌ No valid results to consolidate")
            return None
        
        consolidated_df = pd.concat(consolidated_data, ignore_index=True)
        print(f"✅ Consolidated {len(consolidated_df)} total records")
        
        return consolidated_df
    
    def _generate_comparison_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive comparison report
        
        Args:
            analysis_results: Results from all pipeline analyses
            
        Returns:
            Comparison report dictionary
        """
        print("📋 Generating comparison report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'pipeline_comparison': {},
            'anonymization_comparison': {},
            'performance_metrics': {},
            'research_insights': {}
        }
        
        # Compare pipeline performance
        pipeline_performance = {}
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                continue
            
            analysis = results.get('analysis', {})
            if 'overall_stats' in analysis:
                stats = analysis['overall_stats']
                pipeline_performance[pipeline_type] = {
                    'avg_processing_time': stats.get('avg_processing_time', 0),
                    'avg_records_per_second': stats.get('avg_records_per_second', 0),
                    'total_experiments': stats.get('total_experiments', 0)
                }
        
        report['pipeline_comparison'] = pipeline_performance
        
        # Compare anonymization methods
        anonymization_performance = {}
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                continue
            
            analysis = results.get('analysis', {})
            if 'method_analysis' in analysis:
                anonymization_performance[pipeline_type] = analysis['method_analysis']
        
        report['anonymization_comparison'] = anonymization_performance
        
        # Performance metrics summary
        if pipeline_performance:
            best_throughput = max(pipeline_performance.values(), key=lambda x: x['avg_records_per_second'])
            best_latency = min(pipeline_performance.values(), key=lambda x: x['avg_processing_time'])
            
            report['performance_metrics'] = {
                'best_throughput_pipeline': next(k for k, v in pipeline_performance.items() if v == best_throughput),
                'best_throughput_value': best_throughput['avg_records_per_second'],
                'best_latency_pipeline': next(k for k, v in pipeline_performance.items() if v == best_latency),
                'best_latency_value': best_latency['avg_processing_time']
            }
        
        # Research insights
        report['research_insights'] = {
            'total_pipelines_tested': len([k for k, v in analysis_results.items() if 'error' not in v and 'skipped' not in v]),
            'total_anonymization_methods': len(self.config_manager.get_all_configs()),
            'total_dataset_sizes': len(self.data_generator.generate_test_datasets()) // 2,  # Divide by 2 (healthcare + financial)
            'key_findings': self._extract_key_findings(analysis_results)
        }
        
        return report
    
    def _extract_key_findings(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Extract key research findings from analysis results"""
        findings = []
        
        # Performance comparison findings
        throughput_values = {}
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                continue
            
            analysis = results.get('analysis', {})
            if 'overall_stats' in analysis:
                throughput_values[pipeline_type] = analysis['overall_stats'].get('avg_records_per_second', 0)
        
        if throughput_values:
            best_pipeline = max(throughput_values.keys(), key=lambda k: throughput_values[k])
            findings.append(f"Best performing pipeline: {best_pipeline} with {throughput_values[best_pipeline]:.2f} records/second average throughput")
        
        # Anonymization method findings
        anonymization_performance = {}
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                continue
            
            analysis = results.get('analysis', {})
            if 'method_analysis' in analysis:
                for method, stats in analysis['method_analysis'].items():
                    if method not in anonymization_performance:
                        anonymization_performance[method] = []
                    anonymization_performance[method].append(stats.get('avg_records_per_second', 0))
        
        for method, performance_list in anonymization_performance.items():
            avg_performance = np.mean(performance_list)
            findings.append(f"{method} anonymization: {avg_performance:.2f} records/second average across all pipelines")
        
        return findings
    
    def _generate_research_summary(self, analysis_results: Dict[str, Any], start_time: datetime) -> str:
        """
        Generate research summary in Markdown format
        
        Args:
            analysis_results: Results from all pipeline analyses
            start_time: Analysis start time
            
        Returns:
            Research summary as Markdown string
        """
        print("📄 Generating research summary...")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        md_content = f"""# Comprehensive Pipeline Research Analysis Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Duration:** {duration:.2f} seconds  
**Total Pipelines Tested:** {len([k for k, v in analysis_results.items() if 'error' not in v and 'skipped' not in v])}

## Executive Summary

This comprehensive analysis evaluates three data processing pipeline architectures for compliance violation detection effectiveness:

"""
        
        # Add pipeline-specific summaries
        for pipeline_type, results in analysis_results.items():
            if 'error' in results:
                md_content += f"### {pipeline_type.title()} Pipeline\n\n❌ **Status:** Analysis failed - {results['error']}\n\n"
            elif 'skipped' in results:
                md_content += f"### {pipeline_type.title()} Pipeline\n\n⚠️ **Status:** Skipped - {results['skipped']}\n\n"
            else:
                analysis = results.get('analysis', {})
                if 'overall_stats' in analysis:
                    stats = analysis['overall_stats']
                    md_content += f"""### {pipeline_type.title()} Pipeline

✅ **Status:** Completed successfully  
📊 **Total Experiments:** {stats.get('total_experiments', 0)}  
⏱️ **Average Processing Time:** {stats.get('avg_processing_time', 0):.3f} seconds  
🚀 **Average Throughput:** {stats.get('avg_records_per_second', 0):.2f} records/second  

"""
        
        # Add anonymization method comparison
        md_content += """## Anonymization Method Comparison

| Method | Pipeline | Avg Throughput (records/sec) | Avg Information Loss |
|--------|----------|------------------------------|---------------------|
"""
        
        for pipeline_type, results in analysis_results.items():
            if 'error' in results or 'skipped' in results:
                continue
            
            analysis = results.get('analysis', {})
            if 'method_analysis' in analysis:
                for method, stats in analysis['method_analysis'].items():
                    throughput = stats.get('avg_records_per_second', 0)
                    info_loss = stats.get('avg_information_loss', 0)
                    md_content += f"| {method} | {pipeline_type} | {throughput:.2f} | {info_loss:.3f} |\n"
        
        # Add research insights
        md_content += """
## Key Research Insights

"""
        
        comparison_report = self._generate_comparison_report(analysis_results)
        insights = comparison_report.get('research_insights', {})
        
        for finding in insights.get('key_findings', []):
            md_content += f"- {finding}\n"
        
        # Add methodology
        md_content += """
## Methodology

### Test Configuration
- **Dataset Sizes:** 500, 1000, 2500, 5000, 10000 records
- **Data Types:** Healthcare (HIPAA), Financial (GDPR)
- **Anonymization Methods:** K-anonymity (k=3,5,10,15), Differential Privacy (ε=0.1,0.5,1.0,2.0), Tokenization (128,256,512-bit)

### Pipeline Architectures Tested
1. **Batch Processing:** Apache Spark with microflow architecture
2. **Stream Processing:** Apache Storm with real-time processing
3. **Hybrid Processing:** Apache Flink with intelligent routing

### Metrics Collected
- Pure processing time (excluding I/O)
- Throughput (records/second)
- Compliance violation detection rate
- Information loss and utility preservation
- Memory usage and CPU utilization

## Files Generated
- `consolidated_research_results.csv` - All experimental results
- `pipeline_comparison_report.json` - Detailed comparison metrics
- Individual pipeline result files for detailed analysis

---

*This analysis was conducted using the Secure Data Pipeline Research Framework with clean timing separation for research-grade metrics.*
"""
        
        return md_content
    
    def _save_consolidated_results(self, consolidated_df: Optional[pd.DataFrame]):
        """Save consolidated results to CSV"""
        if consolidated_df is not None:
            consolidated_df.to_csv(self.consolidated_results_file, index=False)
            print(f"✅ Consolidated results saved to {self.consolidated_results_file}")
        else:
            print("⚠️  No consolidated results to save")
    
    def _save_comparison_report(self, report: Dict[str, Any]):
        """Save comparison report to JSON"""
        with open(self.comparison_report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✅ Comparison report saved to {self.comparison_report_file}")
    
    def _save_research_summary(self, summary: str):
        """Save research summary to Markdown"""
        with open(self.research_summary_file, 'w') as f:
            f.write(summary)
        print(f"✅ Research summary saved to {self.research_summary_file}")
    
    def _generate_visualizations(self, consolidated_df: pd.DataFrame):
        """Generate performance visualization charts"""
        print("📊 Generating performance visualizations...")
        
        try:
            # Set up plotting style
            plt.style.use('seaborn-v0_8')
            
            # Performance comparison by pipeline
            plt.figure(figsize=(12, 8))
            
            # Throughput comparison
            plt.subplot(2, 2, 1)
            successful_df = consolidated_df[consolidated_df['success'] == True]
            if not successful_df.empty:
                pipeline_throughput = successful_df.groupby('pipeline_type')['records_per_second'].mean()
                pipeline_throughput.plot(kind='bar', color=['#1f77b4', '#ff7f0e', '#2ca02c'])
                plt.title('Average Throughput by Pipeline Type')
                plt.ylabel('Records/Second')
                plt.xticks(rotation=45)
            
            # Processing time comparison
            plt.subplot(2, 2, 2)
            if not successful_df.empty:
                pipeline_time = successful_df.groupby('pipeline_type')['pure_processing_time_seconds'].mean()
                pipeline_time.plot(kind='bar', color=['#1f77b4', '#ff7f0e', '#2ca02c'])
                plt.title('Average Processing Time by Pipeline Type')
                plt.ylabel('Seconds')
                plt.xticks(rotation=45)
            
            # Anonymization method comparison
            plt.subplot(2, 2, 3)
            if not successful_df.empty:
                method_throughput = successful_df.groupby('anonymization_method')['records_per_second'].mean()
                method_throughput.plot(kind='bar', color='skyblue')
                plt.title('Average Throughput by Anonymization Method')
                plt.ylabel('Records/Second')
                plt.xticks(rotation=45)
            
            # Dataset size scaling
            plt.subplot(2, 2, 4)
            if not successful_df.empty:
                size_throughput = successful_df.groupby('dataset_size')['records_per_second'].mean()
                size_throughput.plot(kind='line', marker='o', color='green')
                plt.title('Throughput Scaling by Dataset Size')
                plt.xlabel('Dataset Size (records)')
                plt.ylabel('Records/Second')
            
            plt.tight_layout()
            
            # Save visualization
            viz_file = os.path.join(self.output_dir, 'performance_comparison.png')
            plt.savefig(viz_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Performance visualizations saved to {viz_file}")
            
        except Exception as e:
            print(f"⚠️  Visualization generation failed: {str(e)}")

def main():
    """Main function to run comprehensive research analysis"""
    parser = argparse.ArgumentParser(description='Comprehensive Pipeline Research Analysis')
    parser.add_argument('--batch-only', action='store_true', help='Run only batch pipeline analysis')
    parser.add_argument('--stream-only', action='store_true', help='Run only stream pipeline analysis')
    parser.add_argument('--hybrid-only', action='store_true', help='Run only hybrid pipeline analysis')
    parser.add_argument('--skip-kafka-check', action='store_true', help='Skip Kafka connectivity check')
    parser.add_argument('--output-dir', default='results', help='Output directory for results')
    
    args = parser.parse_args()
    
    # Determine which analyses to run
    run_batch = not (args.stream_only or args.hybrid_only)
    run_stream = not (args.batch_only or args.hybrid_only)
    run_hybrid = not (args.batch_only or args.stream_only)
    
    if args.batch_only:
        run_batch, run_stream, run_hybrid = True, False, False
    elif args.stream_only:
        run_batch, run_stream, run_hybrid = False, True, False
    elif args.hybrid_only:
        run_batch, run_stream, run_hybrid = False, False, True
    
    print("🔬 Comprehensive Pipeline Research Analysis")
    print("="*80)
    print(f"🚀 Batch Analysis: {'✅ Enabled' if run_batch else '❌ Disabled'}")
    print(f"⚡ Stream Analysis: {'✅ Enabled' if run_stream else '❌ Disabled'}")
    print(f"🧠 Hybrid Analysis: {'✅ Enabled' if run_hybrid else '❌ Disabled'}")
    print(f"📁 Output Directory: {args.output_dir}")
    
    # Initialize and run master analyzer
    master_analyzer = MasterResearchAnalyzer(args.output_dir)
    
    results = master_analyzer.run_comprehensive_analysis(
        run_batch=run_batch,
        run_stream=run_stream,
        run_hybrid=run_hybrid,
        skip_kafka_check=args.skip_kafka_check
    )
    
    print("\n🎉 Comprehensive research analysis complete!")
    print("📊 Check the results directory for detailed analysis outputs.")

if __name__ == "__main__":
    main() 