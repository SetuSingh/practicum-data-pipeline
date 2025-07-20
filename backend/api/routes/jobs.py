#!/usr/bin/env python3
"""
Job Management API Routes
Handles job status tracking, metrics, and user management
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

bp = Blueprint('jobs', __name__, url_prefix='/api')

@bp.route('/jobs')
def get_jobs():
    """Get all processing jobs"""
    try:
        from app import processing_jobs, db_connector
        
        # Convert processing_jobs dict to list
        jobs_list = []
        for job_id, job in processing_jobs.items():
            if hasattr(job, 'to_dict'):
                # ProcessingJob object - enhance with database stats
                job_dict = job.to_dict()
                
                # Try to get actual record count from database
                if job_dict.get('file_id') and db_connector:
                    try:
                        record_count = db_connector.execute_query("""
                            SELECT COUNT(*) as count FROM data_records WHERE file_id = %s
                        """, (job_dict['file_id'],))
                        
                        if record_count and len(record_count) > 0:
                            actual_count = record_count[0]['count']
                            job_dict['records_processed'] = actual_count
                            if not job_dict.get('results'):
                                job_dict['results'] = {}
                            job_dict['results']['total_records'] = actual_count
                    except Exception as e:
                        print(f"Failed to get record count: {e}")
                
                jobs_list.append(job_dict)
            else:
                # Dictionary fallback
                jobs_list.append({
                    'job_id': job_id,
                    'filename': job.get('filename', 'Unknown'),
                    'pipeline_type': job.get('pipeline_type', 'batch'),
                    'status': job.get('status', 'pending'),
                    'progress': job.get('progress', 0),
                    'start_time': job.get('start_time', datetime.now().isoformat()),
                    'end_time': job.get('end_time'),
                    'records_processed': job.get('records_processed', 0),
                    'results': job.get('results', {}),
                    'compliance_violations': job.get('compliance_violations', []),
                    'error': job.get('error'),
                    'user_id': job.get('user_id', 'unknown'),
                    'file_id': job.get('file_id')
                })
        
        # Sort by start_time (most recent first)
        jobs_list.sort(key=lambda x: x['start_time'], reverse=True)
        
        return jsonify(jobs_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/jobs/<job_id>')
def get_job_status(job_id):
    """Get specific job status"""
    try:
        from app import processing_jobs, db_connector
        
        if job_id not in processing_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = processing_jobs[job_id]
        if hasattr(job, 'to_dict'):
            # ProcessingJob object - enhance with database stats
            job_dict = job.to_dict()
            
            # Try to get actual record count from database
            if job_dict.get('file_id') and db_connector:
                try:
                    record_count = db_connector.execute_query("""
                        SELECT COUNT(*) as count FROM data_records WHERE file_id = %s
                    """, (job_dict['file_id'],))
                    
                    if record_count and len(record_count) > 0:
                        actual_count = record_count[0]['count']
                        job_dict['records_processed'] = actual_count
                        if not job_dict.get('results'):
                            job_dict['results'] = {}
                        job_dict['results']['total_records'] = actual_count
                except Exception as e:
                    print(f"Failed to get record count: {e}")
            
            return jsonify(job_dict)
        else:
            # Dictionary fallback
            return jsonify({
                'job_id': job_id,
                'filename': job.get('filename', 'Unknown'),
                'pipeline_type': job.get('pipeline_type', 'batch'),
                'status': job.get('status', 'pending'),
                'progress': job.get('progress', 0),
                'start_time': job.get('start_time', datetime.now().isoformat()),
                'end_time': job.get('end_time'),
                'records_processed': job.get('records_processed', 0),
                'results': job.get('results', {}),
                'compliance_violations': job.get('compliance_violations', []),
                'error': job.get('error'),
            'user_id': job.get('user_id', 'unknown'),
            'file_id': job.get('file_id')
        })
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

@bp.route('/roles')
def get_roles():
    """Get available user roles with permissions"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get all active roles with their permissions
        roles = db_connector.execute_query("""
            SELECT r.id, r.code, r.label, r.description,
                   COALESCE(
                       JSON_AGG(
                           JSON_BUILD_OBJECT(
                               'permission_code', p.code,
                               'permission_label', p.label,
                               'resource_type', p.resource_type,
                               'action', p.action
                           )
                       ) FILTER (WHERE p.code IS NOT NULL), 
                       '[]'::json
                   ) as permissions
            FROM core_user_roles r
            LEFT JOIN data_role_permissions rp ON r.id = rp.role_id
            LEFT JOIN data_permissions p ON rp.permission_id = p.id
            WHERE r.is_active = TRUE
            GROUP BY r.id, r.code, r.label, r.description
            ORDER BY r.code
        """)
        
        return jsonify({
            'status': 'success',
            'roles': [dict(role) for role in roles]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/user-permissions/<user_id>')
def get_user_permissions(user_id):
    """Get permissions for a specific user"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get user permissions
        permissions = db_connector.get_user_permissions(user_id)
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'permissions': [dict(perm) for perm in permissions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 