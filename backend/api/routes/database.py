#!/usr/bin/env python3
"""
Database API Routes
Handles database operations for files, records, audit logs, and statistics
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any

bp = Blueprint('database', __name__, url_prefix='/database')

@bp.route('/files')
def get_database_files():
    """Get all files stored in database"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get files from database
        files = db_connector.execute_query("""
            SELECT f.*, ft.label as file_type_label, u.username as created_by_username
            FROM data_files f
            JOIN data_file_types ft ON f.file_type_id = ft.id
            LEFT JOIN data_users u ON f.created_by = u.id
            ORDER BY f.created_at DESC
            LIMIT 50
        """)
        
        return jsonify({
            'status': 'success',
            'files': [dict(file) for file in files]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/records/<file_id>')
def get_database_records(file_id: str):
    """Get records for a specific file from database"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        limit = request.args.get('limit', 100, type=int)
        
        # Get records from database
        records = db_connector.get_records_by_file(file_id, limit)
        
        return jsonify({
            'status': 'success',
            'file_id': file_id,
            'records': [dict(record) for record in records]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/violations')
def get_compliance_violations():
    """Get compliance violations from database"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        file_id = request.args.get('file_id')
        severity = request.args.get('severity')
        
        # Get violations from database
        violations = db_connector.get_compliance_violations(file_id, severity)
        
        return jsonify({
            'status': 'success',
            'violations': [dict(violation) for violation in violations]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/audit-log')
def get_audit_log():
    """Get audit log from database"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        action_type = request.args.get('action_type')
        hours_back = request.args.get('hours_back', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Get audit log from database
        audit_log = db_connector.get_audit_log(None, action_type, hours_back, limit)
        
        return jsonify({
            'status': 'success',
            'audit_log': [dict(log) for log in audit_log]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/statistics')
def get_database_statistics():
    """Get comprehensive system statistics from database"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get comprehensive statistics
        stats = db_connector.get_system_statistics()
        integrity_stats = db_connector.get_integrity_statistics()
        
        return jsonify({
            'status': 'success',
            'system_statistics': dict(stats),
            'integrity_statistics': dict(integrity_stats)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 