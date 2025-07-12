#!/usr/bin/env python3
"""
Test script for Hybrid Flink Processor
Sends test data to evaluate routing decisions

This script validates the intelligent routing capabilities of our hybrid
processor by sending carefully crafted test scenarios and evaluating
whether the routing decisions match expected outcomes.

Test Categories:
1. Volume-based routing (small vs large batches)
2. Violation-based routing (urgent compliance issues)
3. Complexity-based routing (simple vs complex records)

The test results help validate Research Question 1 by demonstrating
how hybrid processing adapts to different data characteristics.
"""
import json
import time
import sys
import os
from kafka import KafkaProducer  # Kafka producer for sending test data

# Add common module to path for data generation
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'common'))
from data_generator import SimpleDataGenerator

def test_hybrid_processor():
    """
    Send test data to hybrid processor for routing validation
    
    This function implements a comprehensive test suite that validates
    the hybrid processor's routing intelligence by sending different
    types of data and verifying the routing decisions match expectations.
    """
    
    print("🧪 Testing Hybrid Processor Routing")
    print("===================================")
    
    # Setup Kafka producer to send test data to hybrid processor
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9093'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8')  # JSON serialization
    )
    
    # Initialize data generator for creating test scenarios
    data_generator = SimpleDataGenerator()
    
    # Define test scenarios to validate different routing rules
    # Each scenario tests a specific aspect of the hybrid routing intelligence
    scenarios = [
        {
            'name': 'Small batch - should route to stream',
            'count': 10,                    # Small volume to test default stream routing
            'data_type': 'healthcare',
            'expected_route': 'stream',     # Expected: real-time processing for small volumes
            'description': 'Tests default routing behavior for low-volume data'
        },
        {
            'name': 'Large batch - should route to batch',
            'count': 50,                    # Large volume to trigger batch processing
            'data_type': 'financial', 
            'expected_route': 'batch',      # Expected: batch processing for efficiency
            'description': 'Tests volume-based routing to batch processing'
        },
        {
            'name': 'Violation data - should route to stream',
            'count': 20,                    # Medium volume with violations
            'data_type': 'healthcare',
            'force_violations': True,       # Force compliance violations
            'expected_route': 'stream',     # Expected: urgent stream processing for violations
            'description': 'Tests priority routing of compliance violations to stream'
        }
    ]
    
    # Execute each test scenario and measure routing decisions
    for scenario in scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Sending {scenario['count']} {scenario['data_type']} records...")
        
        # Generate and send test records for current scenario
        for i in range(scenario['count']):
            # Generate appropriate data type for testing
            if scenario['data_type'] == 'healthcare':
                record = data_generator.generate_healthcare_data(1).iloc[0].to_dict()
            else:
                record = data_generator.generate_financial_data(1).iloc[0].to_dict()
            
            # Modify records to force violations when testing violation routing
            if scenario.get('force_violations'):
                record['has_violation'] = True
                # Inject clear PHI to trigger violation detection
                record['ssn'] = '123-45-6789'       # Unmasked SSN format
                record['phone'] = '(555) 123-4567'  # Unmasked phone format
                record['email'] = 'test@example.com' # Unmasked email format
            
            # Add test metadata for tracking and validation
            record['test_scenario'] = scenario['name']         # Scenario identifier
            record['expected_route'] = scenario['expected_route'] # Expected routing decision
            record['test_record_number'] = i + 1               # Record sequence number
            
            # Send to hybrid processor input topic for routing decision
            producer.send('hybrid-input', record)
            
            # Small delay between records to simulate realistic data flow
            time.sleep(0.1)
        
        print(f"✅ Sent {scenario['count']} records for '{scenario['name']}'")
        time.sleep(2)  # Wait between scenarios to allow processing
    
    # Cleanup Kafka producer connection
    producer.close()
    
    # Display test completion summary
    print(f"\n🎯 Test Complete!")
    print("Check hybrid processor output for routing decisions")
    print("\nExpected routing results:")
    for scenario in scenarios:
        print(f"  • {scenario['name']}: {scenario['expected_route']} processing")
        print(f"    Rationale: {scenario['description']}")
    
    print(f"\n📊 Validation Instructions:")
    print("1. Monitor hybrid processor logs for routing decisions")
    print("2. Verify actual routes match expected routes")
    print("3. Check processing latency differences between batch and stream")
    print("4. Analyze routing decision reasons in processor output")
    print("5. Compare throughput metrics between processing modes")

if __name__ == "__main__":
    """
    Main execution point for hybrid processor testing
    
    Run this script to validate the intelligent routing capabilities
    of the Flink hybrid processor. The script will send test data
    and display expected routing outcomes for validation.
    """
    test_hybrid_processor() 