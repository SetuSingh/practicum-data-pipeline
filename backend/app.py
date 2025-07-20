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
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Suppress verbose Kafka and other third-party logging
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.ERROR)
logging.getLogger('kafka.coordinator').setLevel(logging.ERROR)
logging.getLogger('kafka.coordinator.heartbeat').setLevel(logging.ERROR)
logging.getLogger('kafka.coordinator.consumer').setLevel(logging.ERROR)
logging.getLogger('kafka.consumer').setLevel(logging.ERROR)
logging.getLogger('kafka.cluster').setLevel(logging.ERROR)
logging.getLogger('py4j').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Configure root logger for clean output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

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
    app = Flask(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://admin:password@localhost:5433/compliance_db')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data', 'uploads')
    app.config['PROCESSED_FOLDER'] = os.path.join(os.path.dirname(__file__), 'data', 'processed')
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    
    # CORS configuration
    CORS(app, origins=["http://localhost:3007", "http://localhost:3000"])
    
    # Initialize database connection
    global db_connector
    try:
        db_connector = PostgreSQLConnector()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("🔄 Continuing without database for development...")
        db_connector = None
    
    # Register original blueprints for full functionality
    from api.routes.status import bp as status_bp
    from api.routes.files import bp as files_bp
    from api.routes.database import bp as database_bp
    from api.routes.jobs import bp as jobs_bp
    from api.routes.pipeline import bp as pipeline_bp

    app.register_blueprint(status_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(database_bp) 
    app.register_blueprint(jobs_bp)
    app.register_blueprint(pipeline_bp)
    
    # Basic monitoring endpoints removed - using comprehensive monitoring blueprint
    
    # Health endpoint removed - using comprehensive monitoring blueprint
            
    # Alerts endpoint removed - using comprehensive monitoring blueprint
    
    # ------------------------------------------------------------------
    # Monitoring & Metrics
    # ------------------------------------------------------------------
    # Register the monitoring blueprint BEFORE registering duplicate endpoints to avoid conflicts
    from api.routes.monitoring import bp as monitoring_bp
    app.register_blueprint(monitoring_bp)

    # Remove duplicate basic endpoints since monitoring blueprint provides full functionality
    # The monitoring blueprint already provides /api/health, /api/metrics, /api/alerts
    
    # Only keep the metrics/summary endpoint since it's unique
    @app.route('/api/metrics/summary')
    def metrics_summary_endpoint():
        """Metrics summary for monitoring dashboard"""
        try:
            # Get actual counts from database
            job_count = 0
            violation_count = 0
            
            if db_connector:
                try:
                    # Get job statistics from database
                    stats = db_connector.get_system_statistics()
                    job_count = stats.get('total_files', 0)
                    violation_count = stats.get('open_violations', 0)
                except Exception as e:
                    print(f"Database stats error: {e}")
            
            # Fallback to processing_jobs if it's a dict
            if isinstance(processing_jobs, dict):
                job_count = max(job_count, len(processing_jobs))
            
            return jsonify({
                'status': 'success',
                'data': {
                    'data_access_operations': job_count,
                    'integrity_violations': violation_count,
                    'unauthorized_attempts': 0,
                    'compliance_violations': violation_count,
                    'encryption_operations': job_count,
                    'api_requests': job_count
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/api/encryption/status')
    def encryption_status_endpoint():
        """Encryption status for monitoring"""
        try:
            # Check if Vault is available
            vault_status = 'available'
            encryption_ops = 0
            
            try:
                from src.common.vault_client import get_vault_client
                vault_client = get_vault_client()
                health = vault_client.health_check()
                vault_status = 'available' if health.get('vault_reachable', False) else 'unavailable'
            except Exception as e:
                vault_status = 'unavailable'
                print(f"Vault check error: {e}")
            
            # Get encryption operations count
            if isinstance(processing_jobs, dict):
                encryption_ops = len(processing_jobs)
            elif db_connector:
                try:
                    stats = db_connector.get_system_statistics()
                    encryption_ops = stats.get('total_files', 0)
                except Exception:
                    pass
            
            return jsonify({
                'status': 'success',
                'data': {
                    'status': 'enabled',
                    'algorithm': 'AES-256-GCM',
                    'vault_status': vault_status,
                    'encryption_operations': encryption_ops
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    @app.route('/api/jobs/<job_id>/refresh', methods=['POST'])
    def refresh_job_stats(job_id):
        """Refresh job statistics from database"""
        try:
            from app import processing_jobs
            
            if job_id not in processing_jobs:
                return jsonify({'error': 'Job not found'}), 404
            
            job = processing_jobs[job_id]
            
            # Get file_id for this job
            if hasattr(job, 'file_id') and job.file_id:
                file_id = job.file_id
            elif hasattr(job, 'to_dict'):
                job_dict = job.to_dict()
                file_id = job_dict.get('file_id')
            else:
                file_id = None
            
            if file_id:
                # Count records from database
                try:
                    if db_connector:
                        records = db_connector.execute_query("""
                            SELECT COUNT(*) as count, 
                                   COUNT(CASE WHEN has_violations = TRUE THEN 1 END) as violations_count,
                                   COUNT(CASE WHEN has_pii = TRUE THEN 1 END) as pii_count
                            FROM data_records 
                            WHERE file_id = %s
                        """, (file_id,))
                        
                        if records and len(records) > 0:
                            record_stats = records[0]
                            records_count = record_stats['count']
                            violations_count = record_stats['violations_count']
                            pii_count = record_stats['pii_count']
                            
                            # Update job object
                            if hasattr(job, 'records_processed'):
                                job.records_processed = records_count
                                job.results = {
                                    'total_records': records_count,
                                    'compliance_violations': violations_count,
                                    'pii_records': pii_count,
                                    'processing_status': 'completed'
                                }
                            
                            return jsonify({
                                'status': 'success',
                                'records_processed': records_count,
                                'violations_found': violations_count,
                                'pii_records': pii_count
                            })
                except Exception as e:
                    print(f"Database query failed: {e}")
            
            return jsonify({'status': 'success', 'message': 'No database records found'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
 
    # ------------------------------------------------------------------
    # Monitoring & Metrics
    # ------------------------------------------------------------------
    # Replace the minimal placeholder endpoints above with the full
    # monitoring blueprint that exposes rich Prometheus metrics as well as
    # health, alert, and summary endpoints. This ensures that Prometheus
    # can collect all the series referenced by the Grafana dashboard.
    # from api.routes.monitoring import bp as monitoring_bp
    # app.register_blueprint(monitoring_bp)

    # Initialize optimized streaming if available
    try:
        from api.routes.pipeline import stream_manager
        print("🚀 Initializing streaming...")
        stream_manager.initialize_static_topics()
        stream_manager.start_persistent_consumers()
        print("✅ Streaming ready")
    except Exception as e:
        print(f"❌ Streaming init failed: {e}")
        # Continue without optimized streaming
    
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
    print(" Starting Secure Data Pipeline Dashboard (Modular API)")
    print(" Dashboard URL: http://localhost:5001")

    
    app.run(debug=True, host='0.0.0.0', port=5001) 