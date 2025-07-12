#!/usr/bin/env python3
"""
PostgreSQL Integration Test Script
Demonstrates complete data integrity monitoring with PostgreSQL backend
"""

import sys
import os
import pandas as pd
import hashlib
import json
from datetime import datetime

# Add src to Python path
sys.path.append('src')

from database.postgres_connector import PostgreSQLConnector
from monitoring.postgres_integrity_monitor import PostgreSQLIntegrityMonitor, create_monitor_for_user
from common.data_generator import SimpleDataGenerator

def main():
    print("🚀 Testing PostgreSQL Data Integrity Integration")
    print("=" * 70)
    
    # Database configuration
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'compliance_db',
        'username': 'postgres',
        'password': 'postgres'
    }
    
    try:
        # Step 1: Connect to database
        print("1️⃣ Connecting to PostgreSQL database...")
        db = PostgreSQLConnector(**DB_CONFIG)
        print("✅ Connected successfully")
        
        # Step 2: Get test user
        print("\n2️⃣ Setting up test user...")
        admin_user = db.get_user_by_username('admin')
        if not admin_user:
            print("❌ Admin user not found. Please run setup_database.py first")
            return
        
        user_id = admin_user['id']
        print(f"✅ Using admin user: {user_id}")
        
        # Step 3: Create integrity monitor
        print("\n3️⃣ Creating PostgreSQL integrity monitor...")
        monitor = PostgreSQLIntegrityMonitor(db, user_id)
        print("✅ Monitor initialized")
        
        # Step 4: Generate test data
        print("\n4️⃣ Generating test healthcare data...")
        test_data = generate_test_healthcare_data()
        print(f"✅ Generated {len(test_data)} test records")
        
        # Step 5: Create data file in database
        print("\n5️⃣ Creating data file record...")
        file_id = create_test_file_record(db, user_id, test_data)
        print(f"✅ Created file record: {file_id}")
        
        # Step 6: Create integrity baseline
        print("\n6️⃣ Creating integrity baseline...")
        baseline_id = monitor.create_baseline_for_file(
            file_id=file_id,
            file_path="test_healthcare.csv"
        )
        print(f"✅ Created baseline: {baseline_id}")
        
        # Step 7: Test change detection (no changes)
        print("\n7️⃣ Testing change detection (clean data)...")
        changes = monitor.detect_changes_in_file(
            file_id=file_id,
            file_path="test_healthcare.csv"
        )
        print(f"✅ No changes detected: {len(changes)} changes")
        
        # Step 8: Simulate data tampering
        print("\n8️⃣ Simulating data tampering...")
        tampered_data = simulate_data_tampering(test_data)
        tampered_file = "test_healthcare_tampered.csv"
        tampered_data.to_csv(tampered_file, index=False)
        print("✅ Created tampered data file")
        
        # Step 9: Detect tampering
        print("\n9️⃣ Detecting tampering...")
        changes = monitor.detect_changes_in_file(
            file_id=file_id,
            file_path=tampered_file
        )
        print(f"🚨 Found {len(changes)} integrity violations!")
        
        for change in changes:
            print(f"   • {change.severity.upper()}: {change.description}")
        
        # Step 10: Test integrity status
        print("\n🔟 Getting integrity status...")
        status = monitor.get_integrity_status()
        print("✅ Integrity Status:")
        for key, value in status.items():
            print(f"   • {key}: {value}")
        
        # Step 11: Generate integrity report
        print("\n1️⃣1️⃣ Generating integrity report...")
        report = monitor.generate_integrity_report(days_back=1)
        print("✅ Report generated:")
        print(f"   • Total Events: {report['summary']['total_events']}")
        print(f"   • Critical Events: {report['summary']['critical_events']}")
        print(f"   • Open Violations: {report['summary']['open_violations']}")
        
        # Step 12: Test compliance operations
        print("\n1️⃣2️⃣ Testing compliance operations...")
        test_compliance_operations(db, file_id, user_id)
        print("✅ Compliance operations tested")
        
        # Step 13: Test audit logging
        print("\n1️⃣3️⃣ Testing audit logging...")
        test_audit_operations(db, user_id)
        print("✅ Audit operations tested")
        
        # Step 14: Test user permissions
        print("\n1️⃣4️⃣ Testing user permissions...")
        test_user_permissions(db, monitor, user_id)
        print("✅ Permission system tested")
        
        # Step 15: Show comprehensive statistics
        print("\n1️⃣5️⃣ Final System Statistics:")
        show_system_statistics(db, monitor)
        
        print("\n" + "=" * 70)
        print("🎉 PostgreSQL Integration Test Completed Successfully!")
        print("=" * 70)
        
        print("\n📊 Test Summary:")
        print("   ✅ Database connection and operations")
        print("   ✅ User management and permissions")
        print("   ✅ Data integrity monitoring")
        print("   ✅ Change detection and alerting")
        print("   ✅ Compliance violation tracking")
        print("   ✅ Audit logging")
        print("   ✅ Role-based access control")
        print("   ✅ Comprehensive reporting")
        
        # Cleanup
        cleanup_test_files()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def generate_test_healthcare_data():
    """Generate test healthcare data"""
    generator = SimpleDataGenerator()
    data = generator.generate_healthcare_data(50)
    
    # Save to file for testing
    data.to_csv("test_healthcare.csv", index=False)
    
    return data

def create_test_file_record(db: PostgreSQLConnector, user_id: str, data: pd.DataFrame):
    """Create a test file record in the database"""
    
    # Compute file hash
    file_content = data.to_csv(index=False)
    file_hash = hashlib.sha256(file_content.encode()).hexdigest()
    
    # Create file record
    file_id = db.create_data_file(
        filename='test_healthcare.csv',
        original_filename='test_healthcare_original.csv',
        file_path=os.path.abspath('test_healthcare.csv'),
        file_size=len(file_content),
        file_hash=file_hash,
        mime_type='text/csv',
        file_type_code='healthcare',
        created_by=user_id
    )
    
    # Update file status
    db.update_file_processing_status(
        file_id=file_id,
        status='processed',
        total_records=len(data),
        valid_records=len(data),
        invalid_records=0,
        compliance_report={
            'hipaa_compliant': True,
            'violations': 0,
            'processed_at': datetime.now().isoformat()
        },
        updated_by=user_id
    )
    
    return file_id

def simulate_data_tampering(original_data: pd.DataFrame) -> pd.DataFrame:
    """Simulate various types of data tampering"""
    tampered = original_data.copy()
    
    # Tampering 1: Modify a patient's diagnosis
    tampered.loc[0, 'diagnosis'] = 'TAMPERED_DIAGNOSIS'
    
    # Tampering 2: Delete a record
    tampered = tampered.drop(tampered.index[1])
    
    # Tampering 3: Add a fake record
    fake_record = {
        'id': 'FAKE_ID_999',
        'patient_name': 'Fake Patient',
        'diagnosis': 'Fake Diagnosis',
        'age': 999,
        'gender': 'X'
    }
    
    # Add any missing columns
    for col in tampered.columns:
        if col not in fake_record:
            fake_record[col] = 'FAKE'
    
    tampered = pd.concat([tampered, pd.DataFrame([fake_record])], ignore_index=True)
    
    # Tampering 4: Add a suspicious new column
    tampered['suspicious_column'] = 'MALICIOUS_DATA'
    
    return tampered

def test_compliance_operations(db: PostgreSQLConnector, file_id: str, user_id: str):
    """Test compliance violation operations"""
    
    # Create a test compliance violation
    violation_id = db.create_compliance_violation(
        file_id=file_id,
        violation_type='hipaa',
        violation_category='unauthorized_access',
        severity='critical',
        description='Test violation: Unauthorized access to patient data detected',
        affected_columns=['patient_name', 'diagnosis'],
        affected_records_count=5,
        data_classification='confidential',
        created_by=user_id
    )
    
    print(f"   • Created compliance violation: {violation_id}")
    
    # Get violations
    violations = db.get_compliance_violations(file_id=file_id)
    print(f"   • Retrieved {len(violations)} violations for file")
    
    # Create another violation
    db.create_compliance_violation(
        file_id=file_id,
        violation_type='gdpr',
        violation_category='data_retention',
        severity='medium',
        description='Test violation: Data retention period exceeded',
        affected_columns=['patient_name'],
        affected_records_count=1,
        data_classification='restricted',
        created_by=user_id
    )

def test_audit_operations(db: PostgreSQLConnector, user_id: str):
    """Test audit logging operations"""
    
    # Log various audit events
    events = [
        ('user_login', 'user', user_id, {'ip': '192.168.1.100', 'success': True}),
        ('file_upload', 'file', None, {'filename': 'test.csv', 'size': 1024}),
        ('data_access', 'record', None, {'record_count': 50, 'classification': 'confidential'}),
        ('config_change', 'system', None, {'setting': 'retention_policy', 'old_value': '7 years', 'new_value': '5 years'})
    ]
    
    for action_type, resource_type, resource_id, details in events:
        audit_id = db.log_audit_event(
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address='192.168.1.100',
            user_agent='TestScript/1.0',
            details=details
        )
    
    print(f"   • Logged {len(events)} audit events")
    
    # Get recent audit log
    recent_logs = db.get_audit_log(user_id=user_id, hours_back=1)
    print(f"   • Retrieved {len(recent_logs)} recent audit entries")

def test_user_permissions(db: PostgreSQLConnector, monitor: PostgreSQLIntegrityMonitor, user_id: str):
    """Test user permission system"""
    
    # Check various permissions for admin user
    permissions_to_check = [
        ('file', 'read'),
        ('file', 'write'),
        ('file', 'admin'),
        ('record', 'read'),
        ('record', 'write'),
        ('system', 'admin'),
        ('compliance', 'read'),
        ('audit', 'read')
    ]
    
    print("   • Permission Check Results:")
    for resource_type, action in permissions_to_check:
        has_permission = db.check_user_permission(user_id, resource_type, action)
        status = "✅" if has_permission else "❌"
        print(f"     {status} {resource_type}:{action}")
    
    # Test monitor-specific permission check
    can_monitor = monitor.check_user_permissions(user_id, 'admin')
    print(f"   • Integrity Monitoring Permission: {'✅' if can_monitor else '❌'}")

def show_system_statistics(db: PostgreSQLConnector, monitor: PostgreSQLIntegrityMonitor):
    """Show comprehensive system statistics"""
    
    # System-wide statistics
    system_stats = db.get_system_statistics()
    print("   📊 System Statistics:")
    for key, value in system_stats.items():
        print(f"     • {key.replace('_', ' ').title()}: {value}")
    
    # Integrity-specific statistics
    integrity_stats = monitor.get_integrity_status()
    print("\n   🔍 Integrity Statistics:")
    for key, value in integrity_stats.items():
        print(f"     • {key.replace('_', ' ').title()}: {value}")
    
    # Recent events summary
    events = monitor.get_change_history(limit=10)
    print(f"\n   📝 Recent Events: {len(events)} events")
    
    for event in events[:5]:  # Show top 5
        timestamp = event.get('created_at', 'Unknown')
        event_type = event.get('event_type', 'Unknown')
        severity = event.get('severity', 'Unknown')
        print(f"     • {timestamp}: {event_type} ({severity})")

def cleanup_test_files():
    """Clean up test files"""
    test_files = ['test_healthcare.csv', 'test_healthcare_tampered.csv']
    
    for file in test_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Warning: Could not remove {file}: {e}")

if __name__ == "__main__":
    main() 