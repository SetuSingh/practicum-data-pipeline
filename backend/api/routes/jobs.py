#!/usr/bin/env python3
"""
Job Management API Routes
Handles processing job tracking and schema operations
"""

from flask import Blueprint, jsonify
from typing import Dict, List, Any

bp = Blueprint('jobs', __name__)

@bp.route('/jobs')
def get_jobs():
    """Get all processing jobs"""
    try:
        from app import processing_jobs
        
        jobs_data = []
        for job_id, job in processing_jobs.items():
            jobs_data.append(job.to_dict())
        
        return jsonify({'jobs': jobs_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/jobs/<job_id>')
def get_job_status(job_id: str):
    """Get specific job status"""
    try:
        from app import processing_jobs
        
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_jobs[job_id]
        return jsonify(job.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/schemas')
def get_schemas():
    """Get available schemas"""
    try:
        from app import schema_registry
        
        schemas = schema_registry.list_schemas()
        return jsonify({'schemas': schemas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/users')
def get_users():
    """Get available users for role selection"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get all active users with their roles
        users = db_connector.execute_query("""
            SELECT u.id, u.username, u.full_name, u.email, 
                   r.code as role_code, r.label as role_label
            FROM data_users u
            JOIN core_user_roles r ON u.role_id = r.id
            WHERE u.is_active = TRUE
            ORDER BY r.code, u.username
        """)
        
        return jsonify({
            'status': 'success',
            'users': [dict(user) for user in users]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 