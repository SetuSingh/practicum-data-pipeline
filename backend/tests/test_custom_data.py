#!/usr/bin/env python3
"""
Example: Processing Custom Data Types with the Flexible Pipeline
This demonstrates how to process e-commerce and IoT data using the extensible framework
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from common.data_generator import SimpleDataGenerator
from common.schemas import SchemaRegistry, get_schema_for_data
from common.compliance_rules import ComplianceRuleEngine

def generate_custom_datasets():
    """Generate sample datasets for different data types"""
    generator = SimpleDataGenerator()
    
    print("🛒 Generating E-commerce dataset...")
    ecommerce_df = generator.generate_ecommerce_data(1000)
    generator.save_to_csv(ecommerce_df, "ecommerce_data.csv")
    
    print("📡 Generating IoT sensor dataset...")
    iot_df = generator.generate_iot_data(1000)
    generator.save_to_csv(iot_df, "iot_data.csv")
    
    print("📊 Dataset Summary:")
    print(f"  E-commerce violations: {ecommerce_df['has_violation'].sum()}")
    print(f"  IoT violations: {iot_df['has_violation'].sum()}")
    
    return ecommerce_df, iot_df

def test_schema_detection(ecommerce_df, iot_df):
    """Test automatic schema detection on custom data"""
    print("\n🔍 Testing Schema Detection...")
    
    registry = SchemaRegistry()
    
    # Test e-commerce schema detection
    ecommerce_schema = get_schema_for_data(ecommerce_df.head(5))
    print(f"  E-commerce schema detected: {ecommerce_schema.name if ecommerce_schema else 'None'}")
    
    # Test IoT schema detection
    iot_schema = get_schema_for_data(iot_df.head(5))
    print(f"  IoT schema detected: {iot_schema.name if iot_schema else 'None'}")
    
    # Show available schemas
    print(f"  Available schemas: {registry.list_schemas()}")

def test_compliance_rules(ecommerce_df, iot_df):
    """Test compliance rules on custom data"""
    print("\n🔐 Testing Compliance Rules...")
    
    compliance_engine = ComplianceRuleEngine()
    
    # Test e-commerce compliance
    ecommerce_violations = 0
    for _, record in ecommerce_df.head(100).iterrows():
        violations = compliance_engine.check_compliance(record.to_dict(), 'ecommerce')
        ecommerce_violations += len(violations)
        
        if violations:
            print(f"  E-commerce violation found: {violations[0].description}")
            break
    
    # Test IoT compliance
    iot_violations = 0
    for _, record in iot_df.head(100).iterrows():
        violations = compliance_engine.check_compliance(record.to_dict(), 'iot')
        iot_violations += len(violations)
        
        if violations:
            print(f"  IoT violation found: {violations[0].description}")
            break
    
    print(f"  Total violations in sample:")
    print(f"    E-commerce: {ecommerce_violations}")
    print(f"    IoT: {iot_violations}")

def show_data_samples(ecommerce_df, iot_df):
    """Show sample data from each dataset"""
    print("\n📋 Sample Data Preview:")
    
    print("\n🛒 E-commerce Sample:")
    print(ecommerce_df[['order_id', 'customer_name', 'credit_card', 'has_violation']].head(3))
    
    print("\n📡 IoT Sample:")
    print(iot_df[['device_id', 'location_lat', 'location_lng', 'has_violation']].head(3))

if __name__ == "__main__":
    print("🚀 Custom Data Type Processing Demo")
    print("===================================")
    
    # Step 1: Generate sample data
    ecommerce_df, iot_df = generate_custom_datasets()
    
    # Step 2: Test schema detection
    test_schema_detection(ecommerce_df, iot_df)
    
    # Step 3: Test compliance rules
    test_compliance_rules(ecommerce_df, iot_df)
    
    # Step 4: Show sample data
    show_data_samples(ecommerce_df, iot_df)
    
    print("\n✅ Demo complete! Check data/ directory for results.")
    print("\n💡 This demonstrates the pipeline's flexibility:")
    print("   • ✅ E-commerce data (PCI-DSS compliance)")
    print("   • ✅ IoT sensor data (location privacy)")
    print("   • ✅ Auto-schema detection")
    print("   • ✅ Extensible compliance rules")
    print("   • ✅ Support for any custom data type")
    print("\n🔧 To process with Spark (batch processing):")
    print("   python src/batch/spark_processor.py")
    print("   # (Note: May require Java configuration on newer JVMs)") 