#!/usr/bin/env python3
"""
Quick RQ2 Experiment Runner - Updated for Integrated Anonymization
Direct integration version that uses the updated pipeline API

This script runs RQ2 experiments using the new integrated anonymization
approach where anonymization is built directly into each pipeline.
"""
import os
import sys
import json
import time
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime

# Add project paths
sys.path.append('src')

from src.common.anonymization_engine import EnhancedAnonymizationEngine, AnonymizationConfig, AnonymizationMethod

def test_anonymization_engine():
    """Test the Enhanced Anonymization Engine directly"""
    print("🧪 Testing Enhanced Anonymization Engine...")
    engine = EnhancedAnonymizationEngine()
    
    # Test record
    test_record = {
        'id': '12345',
        'patient_name': 'John Doe',
        'ssn': '123-45-6789',
        'phone': '555-123-4567',
        'email': 'john.doe@email.com',
        'age': 35,
        'diagnosis': 'diabetes'
    }
    
    print(f"Original record: {test_record}")
    print("\n📋 Testing Anonymization Methods:")
    
    # Test k-anonymity
    k_config = AnonymizationConfig(method=AnonymizationMethod.K_ANONYMITY, k_value=5)
    k_result = engine.anonymize_record(test_record, k_config)
    print(f"  K-Anonymity (k=5): {k_result}")
    
    # Test differential privacy
    dp_config = AnonymizationConfig(method=AnonymizationMethod.DIFFERENTIAL_PRIVACY, epsilon=0.5)
    dp_result = engine.anonymize_record(test_record, dp_config)
    print(f"  Differential Privacy (ε=0.5): {dp_result}")
    
    # Test tokenization
    token_config = AnonymizationConfig(method=AnonymizationMethod.TOKENIZATION, key_length=256)
    token_result = engine.anonymize_record(test_record, token_config)
    print(f"  Tokenization (256-bit): {token_result}")

def run_integrated_experiments():
    """
    Run RQ2 experiments using the integrated anonymization API
    """
    print("\n🔬 Research Question 2: Integrated Anonymization Experiments")
    print("=" * 70)
    
    # API base URL - assumes Flask app is running
    api_base = "http://localhost:5000"
    
    # Check if API is available
    try:
        health_check = requests.get(f"{api_base}/status/health")
        if health_check.status_code != 200:
            print("❌ Flask API is not running. Please start the Flask app first:")
            print("   python app.py")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask API. Please start the Flask app first:")
        print("   python app.py")
        return False
    
    print("✅ Flask API is running")
    
    # Create output directory
    results_dir = Path("rq2_integrated_results")
    results_dir.mkdir(exist_ok=True)
    
    # Focused experiment configurations
    pipelines = ['batch', 'stream', 'hybrid']
    anonymization_configs = [
        {'technique': 'k_anonymity', 'k_value': 3},
        {'technique': 'k_anonymity', 'k_value': 5},
        {'technique': 'differential_privacy', 'epsilon': 0.5},
        {'technique': 'differential_privacy', 'epsilon': 1.0},
        {'technique': 'tokenization', 'key_size': 256},
        {'technique': 'tokenization', 'key_size': 512},
    ]
    
    # Generate test data if it doesn't exist
    test_data_file = "data/uploads/test_healthcare_1000.csv"
    if not os.path.exists(test_data_file):
        print(f"📊 Generating test data: {test_data_file}")
        generate_test_data(test_data_file, 1000)
    
    results = []
    experiment_id = 0
    
    print(f"\n🚀 Running {len(pipelines)} × {len(anonymization_configs)} = {len(pipelines) * len(anonymization_configs)} experiments...")
    
    for pipeline in pipelines:
        for anon_config in anonymization_configs:
            experiment_id += 1
            
            print(f"\n📝 Experiment {experiment_id}: {pipeline.upper()} + {anon_config['technique']}")
            print(f"   Parameters: {anon_config}")
            
            # Prepare request data
            files = {'file': open(test_data_file, 'rb')}
            data = {
                'pipeline_type': pipeline,
                'data_type': 'healthcare',
                **anon_config
            }
            
            try:
                # Make API request
                start_time = time.time()
                response = requests.post(
                    f"{api_base}/pipeline/process",
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout
                )
                total_time = time.time() - start_time
                
                files['file'].close()
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract metrics
                    metrics = {
                        'experiment_id': experiment_id,
                        'timestamp': datetime.now().isoformat(),
                        'pipeline_type': pipeline,
                        'anonymization_technique': anon_config['technique'],
                        'anonymization_params': anon_config,
                        'total_time': total_time,
                        'processing_time': result.get('processing_time', 0),
                        'records_processed': result.get('records_processed', 0),
                        'job_id': result.get('job_id'),
                        'anonymization_applied': result.get('anonymization_applied', False),
                        'anonymization_details': result.get('anonymization_details', {}),
                        'status': 'success'
                    }
                    
                    print(f"   ✅ Success: {metrics['processing_time']:.3f}s, {metrics['records_processed']} records")
                    if 'anonymization_details' in result:
                        anon_details = result['anonymization_details']
                        print(f"   🔒 Anonymization: {anon_details.get('method', 'N/A')} - {anon_details.get('records_anonymized', 0)} records")
                    
                else:
                    print(f"   ❌ API Error: {response.status_code} - {response.text}")
                    metrics = {
                        'experiment_id': experiment_id,
                        'timestamp': datetime.now().isoformat(),
                        'pipeline_type': pipeline,
                        'anonymization_technique': anon_config['technique'],
                        'anonymization_params': anon_config,
                        'error': response.text,
                        'status': 'failed'
                    }
                
                results.append(metrics)
                
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
                metrics = {
                    'experiment_id': experiment_id,
                    'timestamp': datetime.now().isoformat(),
                    'pipeline_type': pipeline,
                    'anonymization_technique': anon_config['technique'],
                    'anonymization_params': anon_config,
                    'error': str(e),
                    'status': 'failed'
                }
                results.append(metrics)
            
            # Small delay between experiments
            time.sleep(2)
    
    # Save results
    results_file = results_dir / f"rq2_integrated_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Results saved to: {results_file}")
    
    # Generate summary
    generate_summary(results, results_dir)
    
    return True

def generate_test_data(filepath, num_records):
    """Generate test healthcare data"""
    from src.common.data_generator import HealthcareDataGenerator
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    generator = HealthcareDataGenerator()
    data = generator.generate_healthcare_data(num_records)
    data.to_csv(filepath, index=False)
    
    print(f"   Generated {num_records} records in {filepath}")

def generate_summary(results, output_dir):
    """Generate experiment summary"""
    print("\n📈 Experiment Summary:")
    print("=" * 50)
    
    success_count = len([r for r in results if r.get('status') == 'success'])
    total_count = len(results)
    
    print(f"Total experiments: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    
    if success_count > 0:
        successful_results = [r for r in results if r.get('status') == 'success']
        
        # Performance by pipeline
        print("\n⚡ Performance by Pipeline:")
        for pipeline in ['batch', 'stream', 'hybrid']:
            pipeline_results = [r for r in successful_results if r['pipeline_type'] == pipeline]
            if pipeline_results:
                avg_time = sum(r['processing_time'] for r in pipeline_results) / len(pipeline_results)
                avg_records = sum(r['records_processed'] for r in pipeline_results) / len(pipeline_results)
                print(f"  {pipeline.upper()}: {avg_time:.3f}s avg, {avg_records:.0f} records avg")
        
        # Performance by anonymization technique
        print("\n🔒 Performance by Anonymization Technique:")
        for technique in ['k_anonymity', 'differential_privacy', 'tokenization']:
            technique_results = [r for r in successful_results if r['anonymization_technique'] == technique]
            if technique_results:
                avg_time = sum(r['processing_time'] for r in technique_results) / len(technique_results)
                print(f"  {technique}: {avg_time:.3f}s avg")
    
    # Save summary CSV
    if results:
        df = pd.DataFrame(results)
        summary_file = output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(summary_file, index=False)
        print(f"\n📋 Detailed results saved to: {summary_file}")

def main():
    """Main function"""
    print("🎯 RQ2 Integrated Anonymization Experiment Runner")
    print("=" * 60)
    
    # Test anonymization engine first
    test_anonymization_engine()
    
    # Run integrated experiments
    success = run_integrated_experiments()
    
    if success:
        print("\n✅ All experiments completed successfully!")
        print("\nNext steps:")
        print("  - Review results in rq2_integrated_results/")
        print("  - Check CSV outputs in data/processed/")
        print("  - Analyze performance metrics")
    else:
        print("\n❌ Experiments failed. Please check the Flask API and try again.")

if __name__ == "__main__":
    main() 