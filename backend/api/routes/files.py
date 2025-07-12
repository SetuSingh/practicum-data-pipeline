#!/usr/bin/env python3
"""
File Management API Routes
Handles file uploads, validation, and sample data generation
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ..models import ProcessingJob
from ..utils import calculate_file_hash, generate_unique_filename, run_async_task

bp = Blueprint('files', __name__)

@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing"""
    try:
        # Import shared objects from app
        from app import processing_jobs, db_connector
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        pipeline_type = request.form.get('pipeline', 'batch')
        user_role = request.form.get('user_role', 'admin')
        
        # Map role to actual user ID from database
        user_id = _get_user_id_for_role(db_connector, user_role)
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400
        
        # Save uploaded file
        unique_filename = generate_unique_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Calculate file hash and size
        file_size = os.path.getsize(filepath)
        file_hash = calculate_file_hash(filepath)
        
        # Auto-detect data type for proper file_type_code
        from ..utils import detect_data_type_from_file
        data_type = detect_data_type_from_file(filepath)
        
        # Create database record for the file
        file_id = _create_file_database_record(
            db_connector, user_id, file.filename, unique_filename, 
            filepath, file_size, file_hash, pipeline_type, data_type
        )
        
        # Create processing job
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, unique_filename, pipeline_type, user_id, file_id)
        processing_jobs[job_id] = job
        
        # Create processing job in database (get processed folder path before background thread)
        processed_folder = current_app.config['PROCESSED_FOLDER']
        _create_processing_job_database_record(
            db_connector, job, file.filename, filepath, pipeline_type, user_id, processed_folder
        )
        
        # Start processing through pipeline orchestrator in background thread
        from .pipeline import orchestrator
        def pipeline_process_async():
            try:
                orchestrator.process_file(job_id, filepath, pipeline_type, processed_folder, job)
            except Exception as e:
                job.status = 'failed'
                job.error = str(e)
                print(f"❌ Pipeline processing failed: {str(e)}")
        
        run_async_task(pipeline_process_async)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'job_id': job_id,
            'file_id': file_id,
            'filename': unique_filename,
            'pipeline': pipeline_type,
            'file_size': file_size,
            'file_hash': file_hash
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/generate-sample', methods=['POST'])
def generate_sample_data():
    """Generate sample data for testing"""
    try:
        from common.data_generator import SimpleDataGenerator
        
        data_type = request.json.get('type', 'healthcare')
        size = request.json.get('size', 1000)
        
        generator = SimpleDataGenerator()
        
        if data_type == 'healthcare':
            df = generator.generate_healthcare_data(size)
        elif data_type == 'financial':
            df = generator.generate_financial_data(size)
        elif data_type == 'ecommerce':
            df = generator.generate_ecommerce_data(size)
        elif data_type == 'iot':
            df = generator.generate_iot_data(size)
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        # Save sample file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sample_{data_type}_{timestamp}.csv"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        df.to_csv(filepath, index=False)
        
        return jsonify({
            'message': f'Sample {data_type} data generated',
            'filename': filename,
            'records': int(len(df)),
            'violations': int(df['has_violation'].sum())
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_user_id_for_role(db_connector, user_role: str) -> str:
    """Get user ID for the given role, with fallbacks"""
    if db_connector:
        try:
            user_data = db_connector.get_user_by_username(user_role)
            user_id = user_data['id'] if user_data else None
            if not user_id:
                # Fallback to admin user if role not found
                admin_user = db_connector.get_user_by_username('admin')
                user_id = admin_user['id'] if admin_user else str(uuid.uuid4())
        except Exception as e:
            print(f"Warning: Could not get user for role {user_role}: {e}")
            user_id = str(uuid.uuid4())
    else:
        user_id = str(uuid.uuid4())
    
    return user_id

def _create_file_database_record(db_connector, user_id: str, original_filename: str, 
                               unique_filename: str, filepath: str, file_size: int, 
                               file_hash: str, pipeline_type: str, data_type: str) -> str:
    """Create file record in database"""
    file_id = None
    
    if db_connector:
        try:
            print(f"🔍 Creating file record for user_id: {user_id}")
            file_id = db_connector.create_data_file(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=filepath,
                file_size=file_size,
                file_hash=file_hash,
                mime_type='text/csv',
                file_type_code=data_type,
                created_by=user_id
            )
            
            # Log audit event
            db_connector.log_audit_event(
                action_type='file_upload',
                resource_type='data_file',
                resource_id=file_id,
                user_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details={
                    'filename': original_filename,
                    'file_size': file_size,
                    'pipeline_type': pipeline_type
                }
            )
            
            print(f"✅ File record created in database: {file_id}")
            
        except Exception as e:
            print(f"❌ Failed to create file record in database: {e}")
    
    return file_id

def _create_processing_job_database_record(db_connector, job, original_filename: str, 
                                         filepath: str, pipeline_type: str, user_id: str, 
                                         processed_folder: str):
    """Create processing job record in database"""
    if db_connector and job.file_id:
        try:
            db_job_id = db_connector.create_processing_job(
                job_name=f"Process {original_filename}",
                file_id=job.file_id,
                pipeline_type=pipeline_type,
                processor_config={
                    'input_path': filepath,
                    'output_path': processed_folder,
                    'pipeline_type': pipeline_type
                },
                created_by=user_id
            )
            job.db_job_id = db_job_id
            print(f"✅ Processing job created in database: {db_job_id}")
            
        except Exception as e:
            print(f"❌ Failed to create processing job in database: {e}") 