#!/usr/bin/env python3
"""
Cold Start Testing Script for Research Benchmarking

This script runs each test in a separate Python process to ensure
true cold starts without JVM caching effects.
"""

import subprocess
import sys
import os
import time
import json

def run_single_test(test_file, output_file, run_number):
    """Run a single test in a separate process"""
    test_script = f"""
import sys
sys.path.append('/Users/mylo/Documents/Developer/practicum/backend')

from src.batch.spark_processor import SparkBatchProcessor
import time

# Run single test
processor = SparkBatchProcessor()
start_time = time.time()

result = processor.process_batch_microflow(
    '{test_file}', 
    '{output_file}', 
    batch_size=1000
)

end_time = time.time()
total_time = end_time - start_time

# Output results as JSON
import json
output = {{
    'run_number': {run_number},
    'pure_processing_time': result.get('pure_processing_time', 0),
    'total_time': total_time,
    'records_per_second': result.get('processing_metrics', {{}}).get('records_per_second', 0),
    'records_processed': result.get('processing_metrics', {{}}).get('total_records', 0),
    'violations_found': result.get('processing_metrics', {{}}).get('violations_found', 0)
}}

print("RESULT_JSON:" + json.dumps(output))
processor.stop()
"""
    
    # Run the test in a separate process
    process = subprocess.Popen(
        [sys.executable, '-c', test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd='/Users/mylo/Documents/Developer/practicum/backend'
    )
    
    stdout, stderr = process.communicate()
    
    # Extract result from stdout
    result = None
    for line in stdout.split('\n'):
        if line.startswith('RESULT_JSON:'):
            result = json.loads(line[12:])
            break
    
    if result is None:
        print(f"❌ Run {run_number} failed to produce results")
        if stderr:
            print(f"Error: {stderr}")
        return None
    
    return result

def main():
    """Run cold start consistency tests"""
    test_file = 'rq2_focused_results/test_data/healthcare_1000_records.csv'
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    print("=== TRUE COLD START TESTING (SEPARATE PROCESSES) ===")
    print("Each run executes in a separate Python process to avoid JVM caching")
    print()
    
    results = []
    num_runs = 3
    
    for i in range(1, num_runs + 1):
        output_file = f'/tmp/cold_start_process_run{i}.csv'
        print(f"--- RUN {i} (separate process) ---")
        
        result = run_single_test(test_file, output_file, i)
        if result:
            results.append(result)
            print(f"Run {i}: {result['pure_processing_time']:.3f}s, {result['records_per_second']:.0f} records/sec")
        else:
            print(f"Run {i}: FAILED")
        print()
    
    if len(results) >= 2:
        print("=== COLD START ANALYSIS ===")
        times = [r['pure_processing_time'] for r in results]
        avg_time = sum(times) / len(times)
        time_variance = max(times) - min(times)
        variance_percent = (time_variance / avg_time) * 100 if avg_time > 0 else 0
        
        print(f"Average time: {avg_time:.3f}s")
        print(f"Time variance: {time_variance:.3f}s ({variance_percent:.1f}%)")
        print(f"Consistency: {'✅ Excellent' if variance_percent < 10 else '✅ Good' if variance_percent < 20 else '⚠️ High variance'}")
        
        print("\nDetailed Results:")
        for i, result in enumerate(results, 1):
            print(f"  Run {i}: {result['pure_processing_time']:.3f}s | {result['records_per_second']:.0f} rec/sec | {result['violations_found']} violations")
    else:
        print("❌ Not enough successful runs for analysis")

if __name__ == "__main__":
    main() 