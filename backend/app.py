#!/usr/bin/env python3
"""
Flask Backend for Secure Data Pipeline Dashboard
Main application entry point with modular API structure
"""

import os
import sys
import hashlib
import json
import uuid
import pandas as pd
import numpy as np
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

# Add src to path for imports
sys.path.append('src')

# Import pipeline components
from common.data_generator import SimpleDataGenerator
from common.schemas import get_schema_for_data, SchemaRegistry
from common.compliance_rules import ComplianceRuleEngine
from batch.spark_processor import SparkBatchProcessor
from stream.storm_processor import StormStreamProcessor
from hybrid.flink_processor import FlinkHybridProcessor
from monitoring.data_integrity import DataIntegrityMonitor
from database.postgres_connector import PostgreSQLConnector

# Import API models
from api.models import ProcessingJob

def clean_record_for_json(record_dict):
    """Clean pandas record dictionary by replacing NaN values with None for JSON serialization"""
    cleaned = {}
    for key, value in record_dict.items():
        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
            cleaned[key] = None
        elif isinstance(value, (np.integer, np.floating)):
            cleaned[key] = value.item()  # Convert numpy types to Python types
        else:
            cleaned[key] = value
    return cleaned

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'data/uploads'
    app.config['PROCESSED_FOLDER'] = 'data/processed'
    
    # Enable CORS for React frontend
    CORS(app)
    
    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    
    return app

# Create Flask app
app = create_app()

# ============================================================================
# SHARED GLOBAL OBJECTS
# ============================================================================

# Global processing status tracker
processing_jobs = {}

# Pipeline components
schema_registry = SchemaRegistry()
compliance_engine = ComplianceRuleEngine()
integrity_monitor = DataIntegrityMonitor()

# Database connector
try:
    db_connector = PostgreSQLConnector(
        host="localhost",
        port=5433,
        database="compliance_db",
        username="admin",
        password="password"
    )
    
    # Test the connection
    test_query = "SELECT COUNT(*) FROM data_users"
    result = db_connector.execute_query(test_query)
    print(f"✅ Database connection established - Found {result[0]['count']} users")
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print(f"   Make sure PostgreSQL is running: docker-compose up -d postgres")
    print(f"   And that the database schema has been created")
    db_connector = None

# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================

@app.route('/')
def dashboard():
    """Serve API information"""
    return jsonify({
        'message': 'Secure Data Pipeline API',
        'version': '2.0.0',
        'api_structure': 'modular',
        'frontend_dev': 'http://localhost:3007',
        'endpoints': {
            'status': '/api/status - System health and status',
            'files': '/api/upload - File upload (routes to pipelines)',
            'jobs': '/api/jobs - Processing job tracking',
            'pipelines': '/api/pipeline/* - Pipeline processing and metrics',
            'database': '/api/database/* - Database operations',
            'integrity': '/api/integrity/* - Data integrity monitoring',
            'compliance': '/api/compliance/* - Compliance checking'
        }
    })

# ============================================================================
# REGISTER API BLUEPRINTS
# ============================================================================

from api import api_bp
app.register_blueprint(api_bp)

# ============================================================================
# BACKGROUND PROCESSING FUNCTIONS
# ============================================================================

def process_file_async(job_id: str, filepath: str, pipeline_type: str):
    """Process file asynchronously with database integration"""
    job = processing_jobs[job_id]
    
    try:
        job.status = 'processing'
        job.progress = 10
        
        # Update job status in database
        if db_connector and hasattr(job, 'db_job_id'):
            db_connector.update_job_status(
                job.db_job_id, 
                'processing', 
                progress=10, 
                updated_by=job.user_id
            )
        
        # Read and analyze file
        df = pd.read_csv(filepath)
        job.progress = 20
        
        # Auto-detect schema
        detected_schema = get_schema_for_data(df.head(10))
        schema_name = detected_schema.name if detected_schema else 'unknown'
        
        # Determine data type for compliance rules
        from api.utils import detect_data_type
        data_type = detect_data_type(df)
        
        job.progress = 30
        
        # Process each record and insert into database
        total_records = len(df)
        valid_records = 0
        invalid_records = 0
        violations = 0
        compliance_details = []
        
        print(f"📊 Processing {total_records} records...")
        
        for row_index, record in df.iterrows():
            try:
                # Convert record to dictionary and clean NaN values
                record_dict = record.to_dict()
                clean_record_dict = clean_record_for_json(record_dict)
                
                # Generate unique record ID
                record_id = str(uuid.uuid4())
                
                # Calculate record hash
                record_hash = hashlib.sha256(
                    json.dumps(clean_record_dict, sort_keys=True).encode()
                ).hexdigest()
                
                # Check compliance
                record_violations = compliance_engine.check_compliance(clean_record_dict, data_type)
                has_violations = len(record_violations) > 0
                
                if has_violations:
                    violations += len(record_violations)
                    invalid_records += 1
                    
                    # Store first 10 violations for summary
                    if len(compliance_details) < 10:
                        compliance_details.extend([{
                            'type': v.violation_type.value,
                            'field': v.field_name,
                            'description': v.description,
                            'severity': v.severity,
                            'record_id': record_id
                        } for v in record_violations])
                            
                    job.compliance_violations.append({
                        'record_id': record_id,
                        'violations': record_violations
                    })
                else:
                    valid_records += 1
                
                # Insert record into database FIRST (required for foreign key constraints)
                data_record_db_id = None
                if db_connector and job.file_id:
                    try:
                        data_record_db_id = db_connector.create_data_record(
                            file_id=job.file_id,
                            record_id=record_id,
                            original_data=clean_record_dict,
                            record_hash=record_hash,
                            job_id=getattr(job, 'db_job_id', None),
                            row_number=row_index + 1,
                            has_pii=data_type in ['healthcare', 'financial'],
                            has_violations=has_violations,
                            violation_types=[v.violation_type.value for v in record_violations],
                            compliance_score=1.0 - (len(record_violations) / 5.0),
                            created_by=job.user_id
                        )
                        
                        # Debug: Print first few records
                        if row_index < 3:
                            print(f"✅ Record {row_index + 1} inserted to database")
                            
                    except Exception as record_db_error:
                        print(f"❌ Failed to insert record {row_index + 1} to database: {record_db_error}")
                        continue
                
                # Create compliance violations AFTER record is inserted (for foreign key constraints)
                if has_violations and db_connector and job.file_id and data_record_db_id:
                    for violation in record_violations:
                        try:
                            db_connector.create_compliance_violation(
                                file_id=job.file_id,
                                violation_type=violation.violation_type.value,
                                violation_category=violation.regulation,
                                severity=violation.severity,
                                description=violation.description,
                                affected_columns=[violation.field_name],
                                affected_records_count=1,
                                data_classification=data_type,
                                record_id=data_record_db_id,  # Use the database ID, not the business record_id
                                created_by=job.user_id
                            )
                        except Exception as violation_db_error:
                            print(f"❌ Failed to insert compliance violation for record {row_index + 1}: {violation_db_error}")
                            continue
                
                job.records_processed += 1
                
                # Update progress
                if row_index % 100 == 0:
                    progress = 30 + int((row_index / total_records) * 50)
                    job.progress = progress
                    
                    # Update database progress
                    if db_connector and hasattr(job, 'db_job_id'):
                        db_connector.update_job_status(
                            job.db_job_id,
                            'processing',
                            progress=progress,
                            records_processed=job.records_processed,
                            updated_by=job.user_id
                        )
                    
                    print(f"📈 Processed {row_index + 1}/{total_records} records...")
                
            except Exception as record_error:
                print(f"❌ Error processing record {row_index}: {record_error}")
                invalid_records += 1
                continue
        
        job.progress = 80
        
        # Create integrity baseline
        if db_connector and job.file_id:
            try:
                from api.utils import calculate_file_hash
                baseline_id = db_connector.create_integrity_baseline(
                    file_id=job.file_id,
                    baseline_name=f"Baseline for {job.filename}",
                    baseline_type='file_upload',
                    content_hash=calculate_file_hash(filepath),
                    record_hashes={str(i): hashlib.sha256(
                        json.dumps(clean_record_for_json(df.iloc[i].to_dict()), sort_keys=True).encode()
                    ).hexdigest() for i in range(min(len(df), 1000))},
                    schema_hash=hashlib.sha256(
                        json.dumps(list(df.columns), sort_keys=True).encode()
                    ).hexdigest(),
                    total_records=total_records,
                    column_definitions={col: str(df[col].dtype) for col in df.columns},
                    created_by=job.user_id
                )
                print(f"✅ Integrity baseline created: {baseline_id}")
            except Exception as e:
                print(f"❌ Failed to create integrity baseline: {e}")
        
        # Calculate processing statistics
        processing_time = (datetime.now() - job.start_time).total_seconds()
        throughput = total_records / processing_time if processing_time > 0 else 0
        
        job.results = {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': invalid_records,
            'schema_detected': schema_name,
            'data_type': data_type,
            'violations_found': violations,
            'compliance_details': compliance_details,
            'processing_time': processing_time,
            'throughput': throughput,
            'violation_rate': violations / total_records if total_records > 0 else 0
        }
        
        # Update file processing status in database
        if db_connector and job.file_id:
            db_connector.update_file_processing_status(
                file_id=job.file_id,
                status='completed',
                total_records=total_records,
                valid_records=valid_records,
                invalid_records=invalid_records,
                compliance_report={
                    'violations_found': violations,
                    'violation_rate': violations / total_records if total_records > 0 else 0,
                    'data_type': data_type,
                    'schema_detected': schema_name
                },
                updated_by=job.user_id
            )
        
        # Save processed results
        processed_filename = f"processed_{job.filename}"
        processed_filepath = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        
        # Add compliance results to dataframe
        df['compliance_checked'] = True
        df['processing_timestamp'] = datetime.now().isoformat()
        df['has_violations'] = df.index.isin([v['record_id'] for v in job.compliance_violations])
        df.to_csv(processed_filepath, index=False)
        
        job.progress = 100
        job.status = 'completed'
        job.end_time = datetime.now()
        
        # Update final job status in database
        if db_connector and hasattr(job, 'db_job_id'):
            db_connector.update_job_status(
                job.db_job_id,
                'completed',
                progress=100,
                records_processed=job.records_processed,
                throughput_per_second=throughput,
                updated_by=job.user_id
            )
        
        # Log completion audit event
        if db_connector:
            db_connector.log_audit_event(
                action_type='file_processing_completed',
                resource_type='processing_job',
                resource_id=getattr(job, 'db_job_id', None),
                user_id=job.user_id,
                details={
                    'total_records': total_records,
                    'valid_records': valid_records,
                    'invalid_records': invalid_records,
                    'violations_found': violations,
                    'processing_time': processing_time,
                    'throughput': throughput
                }
            )
        
        print(f"✅ File processing completed: {job.filename}")
        print(f"📊 Statistics: {total_records} total, {valid_records} valid, {invalid_records} invalid")
        print(f"⚠️  Violations found: {violations}")
        
    except Exception as e:
        job.status = 'failed'
        job.error = str(e)
        job.end_time = datetime.now()
        
        # Update job status in database
        if db_connector and hasattr(job, 'db_job_id'):
            db_connector.update_job_status(
                job.db_job_id,
                'failed',
                error_message=str(e),
                updated_by=job.user_id
            )
        
        # Log error audit event
        if db_connector:
            db_connector.log_audit_event(
                action_type='file_processing_failed',
                resource_type='processing_job',
                resource_id=getattr(job, 'db_job_id', None),
                user_id=job.user_id,
                details={
                    'error': str(e),
                    'filepath': filepath,
                    'pipeline_type': pipeline_type
                }
            )
        
        print(f"❌ File processing failed: {job.filename} - {str(e)}")

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting Secure Data Pipeline Dashboard (Modular API)")
    print("📊 Dashboard URL: http://localhost:5001")
    print("🔧 API Structure:")
    print("   📈 GET  /api/status           - System status")
    print("   📁 POST /api/upload           - Upload file (now routes to pipelines)")
    print("   ⚙️  GET  /api/jobs            - List all jobs")
    print("   📋 GET  /api/jobs/<id>        - Get job status")
    print("   🧪 POST /api/generate-sample  - Generate sample data")
    print("   📚 GET  /api/schemas          - List schemas")
    print("   👥 GET  /api/users            - Get available users")
    print("   🚀 Pipeline Processing:")
    print("      POST /api/pipeline/process        - Process file through pipeline")
    print("      GET  /api/pipeline/metrics        - Get research metrics")
    print("      GET  /api/pipeline/metrics/comparison - Comparative analysis")
    print("      GET  /api/pipeline/processors/status   - Processor status")
    print("   🔍 Integrity Endpoints:")
    print("      GET  /api/integrity/status   - Get integrity status")
    print("      GET  /api/integrity/changes  - Get change history")
    print("      POST /api/integrity/baseline - Create baseline")
    print("      POST /api/integrity/check    - Check file integrity")
    print("   🗄️  Database Endpoints:")
    print("      GET  /api/database/files       - Get all files from database")
    print("      GET  /api/database/records/<id> - Get records for a file")
    print("      GET  /api/database/violations  - Get compliance violations")
    print("      GET  /api/database/audit-log   - Get audit log")
    print("      GET  /api/database/statistics  - Get system statistics")
    print("   ✅ Compliance Endpoints:")
    print("      GET  /api/compliance/rules     - Get compliance rules")
    print("      POST /api/compliance/check     - Check compliance")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5001) 