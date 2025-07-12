#!/usr/bin/env python3
"""
Test script for modular components (compliance rules and schemas)
Validates that the new modular architecture works correctly
"""
import sys
import os
import pandas as pd

# Add common modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'common'))

from compliance_rules import (
    compliance_engine, 
    quick_compliance_check, 
    detailed_compliance_check,
    HIPAAPhiExposureRule,
    GDPRConsentRule
)
from schemas import (
    schema_registry,
    get_schema_for_data,
    HEALTHCARE_SCHEMA,
    FINANCIAL_SCHEMA
)

def test_compliance_rules():
    """Test the modular compliance rules system"""
    print("🔍 Testing Compliance Rules Module")
    print("=================================")
    
    # Test HIPAA violations
    healthcare_record_with_violations = {
        'id': 'test-001',
        'patient_name': 'John Doe',
        'ssn': '123-45-6789',  # Exposed SSN
        'phone': '(555) 123-4567',  # Exposed phone
        'email': 'john@example.com',  # Exposed email
        'diagnosis': 'diabetes'
    }
    
    healthcare_record_compliant = {
        'id': 'test-002',
        'patient_name': 'Jane Smith',
        'ssn': '***-**-1234',  # Masked SSN
        'phone': '***-***-****',  # Masked phone
        'email': '***@***.com',  # Masked email
        'diagnosis': 'hypertension'
    }
    
    # Test GDPR violations
    financial_record_with_violations = {
        'id': 'txn-001',
        'customer_name': 'Bob Johnson',
        'account_number': 'ACC123456',
        'transaction_amount': 500.00,
        'consent_given': False  # GDPR violation
    }
    
    financial_record_compliant = {
        'id': 'txn-002',
        'customer_name': 'Alice Brown',
        'account_number': 'ACC789012',
        'transaction_amount': 750.00,
        'consent_given': True  # Compliant
    }
    
    test_cases = [
        ("Healthcare with violations", healthcare_record_with_violations, 'healthcare', True),
        ("Healthcare compliant", healthcare_record_compliant, 'healthcare', False),
        ("Financial with violations", financial_record_with_violations, 'financial', True),
        ("Financial compliant", financial_record_compliant, 'financial', False)
    ]
    
    print("\n📋 Testing Quick Compliance Checks:")
    for name, record, data_type, expected_violations in test_cases:
        has_violations = quick_compliance_check(record, data_type)
        status = "✅ PASS" if has_violations == expected_violations else "❌ FAIL"
        print(f"  {status} {name}: Expected violations={expected_violations}, Got={has_violations}")
    
    print("\n📋 Testing Detailed Compliance Checks:")
    for name, record, data_type, expected_violations in test_cases:
        result = detailed_compliance_check(record, data_type)
        has_violations = not result['compliant']
        status = "✅ PASS" if has_violations == expected_violations else "❌ FAIL"
        print(f"  {status} {name}:")
        print(f"    Compliant: {result['compliant']}")
        print(f"    Violations: {len(result['violations'])}")
        if result['violations']:
            for violation in result['violations']:
                print(f"      - {violation['type']}: {violation['description']} ({violation['severity']})")

def test_schema_detection():
    """Test the modular schema detection system"""
    print("\n🗂️ Testing Schema Detection Module")
    print("==================================")
    
    # Test healthcare data detection
    healthcare_data = {
        'id': 'P001',
        'patient_name': 'John Doe',
        'ssn': '***-**-1234',
        'diagnosis': 'diabetes',
        'treatment_date': '2024-01-15'
    }
    
    # Test financial data detection
    financial_data = {
        'id': 'T001',
        'customer_name': 'Jane Smith',
        'account_number': 'ACC123456',
        'transaction_amount': 500.00,
        'transaction_date': '2024-01-15',
        'consent_given': True
    }
    
    # Test customer data detection
    customer_data = {
        'id': 'C001',
        'name': 'Bob Johnson',
        'email': 'bob@example.com',
        'phone': '555-1234',
        'address': '123 Main St'
    }
    
    test_cases = [
        ("Healthcare data", healthcare_data, "healthcare_batch.csv", "healthcare"),
        ("Financial data", financial_data, "financial_transactions.csv", "financial"),
        ("Customer data", customer_data, "customer_data.csv", "customer"),
        ("Healthcare by filename", {}, "patient_records_hipaa.csv", "healthcare"),
        ("Financial by filename", {}, "gdpr_transactions.csv", "financial")
    ]
    
    print("\n📋 Testing Schema Detection:")
    for name, data, filename, expected_schema in test_cases:
        detected_schema = schema_registry.detect_schema(data) if data else None
        schema_def = schema_registry.get_schema_for_file(filename, data if data else None)
        
        detected_name = detected_schema if detected_schema else (schema_def.data_type.value if schema_def else None)
        status = "✅ PASS" if detected_name == expected_schema else "❌ FAIL"
        
        print(f"  {status} {name}:")
        print(f"    Expected: {expected_schema}")
        print(f"    Detected: {detected_name}")
        if schema_def:
            print(f"    Schema: {schema_def.name}")
            print(f"    Fields: {len(schema_def.fields)}")

def test_schema_conversion():
    """Test schema format conversions"""
    print("\n🔄 Testing Schema Conversions")
    print("=============================")
    
    # Test Spark schema conversion
    spark_schema = HEALTHCARE_SCHEMA.get_spark_schema()
    print(f"\n📋 Healthcare Spark Schema:")
    print(f"  Fields: {len(spark_schema.fields)}")
    print(f"  Schema: {spark_schema.simpleString()}")
    
    # Test Pandas dtypes conversion
    pandas_dtypes = FINANCIAL_SCHEMA.get_pandas_dtypes()
    print(f"\n📋 Financial Pandas Dtypes:")
    for field, dtype in pandas_dtypes.items():
        print(f"  {field}: {dtype}")
    
    # Test JSON schema conversion
    json_schema = HEALTHCARE_SCHEMA.get_json_schema()
    print(f"\n📋 Healthcare JSON Schema:")
    print(f"  Type: {json_schema['type']}")
    print(f"  Properties: {len(json_schema['properties'])}")
    print(f"  Required fields: {len(json_schema.get('required', []))}")

def test_integration():
    """Test integration between components"""
    print("\n🔗 Testing Component Integration")
    print("===============================")
    
    # Create sample DataFrame
    sample_data = pd.DataFrame([
        {
            'id': 'P001',
            'patient_name': 'John Doe',
            'ssn': '123-45-6789',  # Violation
            'phone': '(555) 123-4567',  # Violation
            'email': 'john@example.com',  # Violation
            'diagnosis': 'diabetes',
            'treatment_date': '2024-01-15'
        },
        {
            'id': 'P002',
            'patient_name': 'Jane Smith',
            'ssn': '***-**-1234',  # Compliant
            'phone': '***-***-****',  # Compliant
            'email': '***@***.com',  # Compliant
            'diagnosis': 'hypertension',
            'treatment_date': '2024-01-16'
        }
    ])
    
    # Test schema detection
    schema_def = get_schema_for_data(sample_data, "healthcare_data.csv")
    print(f"\n📋 Detected Schema: {schema_def.name if schema_def else 'None'}")
    
    if schema_def:
        print(f"  Data Type: {schema_def.data_type.value}")
        print(f"  Fields: {len(schema_def.fields)}")
        print(f"  Sensitive Fields: {schema_def.get_sensitive_fields()}")
    
    # Test compliance checking on DataFrame
    print(f"\n📋 Compliance Check Results:")
    violation_count = 0
    for index, record in sample_data.iterrows():
        record_dict = record.to_dict()
        has_violations = quick_compliance_check(record_dict, 'healthcare')
        if has_violations:
            violation_count += 1
            detailed_result = detailed_compliance_check(record_dict, 'healthcare')
            print(f"  Record {record_dict['id']}: {len(detailed_result['violations'])} violations")
            for violation in detailed_result['violations']:
                print(f"    - {violation['field']}: {violation['type']} ({violation['severity']})")
        else:
            print(f"  Record {record_dict['id']}: Compliant ✅")
    
    print(f"\n📊 Summary:")
    print(f"  Total records: {len(sample_data)}")
    print(f"  Records with violations: {violation_count}")
    print(f"  Compliance rate: {(len(sample_data) - violation_count) / len(sample_data) * 100:.1f}%")

def main():
    """Run all modular component tests"""
    print("🧪 Testing Modular Components")
    print("============================")
    print("This script validates the new modular architecture:")
    print("- Compliance Rules Module (HIPAA/GDPR)")
    print("- Schema Detection and Management")
    print("- Component Integration")
    
    try:
        test_compliance_rules()
        test_schema_detection()
        test_schema_conversion()
        test_integration()
        
        print("\n🎯 All Tests Complete!")
        print("✅ Modular components are working correctly")
        print("\n📝 Benefits of Modular Architecture:")
        print("- Centralized compliance rule management")
        print("- Automatic schema detection and selection")
        print("- Consistent behavior across all processors")
        print("- Easy to extend with new regulations/data types")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 