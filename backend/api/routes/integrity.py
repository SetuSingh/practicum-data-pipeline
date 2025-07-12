#!/usr/bin/env python3
"""
Data Integrity API Routes
Handles data integrity monitoring, baselines, and change detection
"""

import os
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any

bp = Blueprint('integrity', __name__, url_prefix='/integrity')

@bp.route('/status', methods=['GET'])
def get_integrity_status():
    """Get overall data integrity monitoring status"""
    try:
        from app import integrity_monitor
        
        status = integrity_monitor.get_integrity_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/changes', methods=['GET'])
def get_change_history():
    """Get history of detected changes"""
    try:
        from app import integrity_monitor
        
        file_path = request.args.get('file_path')
        limit = int(request.args.get('limit', 50))
        
        changes = integrity_monitor.get_change_history(file_path, limit)
        return jsonify({
            'status': 'success',
            'data': changes
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/baseline', methods=['POST'])
def create_baseline():
    """Create integrity baseline for uploaded file"""
    try:
        from app import integrity_monitor
        
        data = request.json
        file_path = data.get('file_path')
        record_id_column = data.get('record_id_column', 'id')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 400
        
        success = integrity_monitor.baseline_file(file_path, record_id_column)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Baseline created successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create baseline'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/check', methods=['POST'])
def check_integrity():
    """Check file integrity against baseline"""
    try:
        from app import integrity_monitor
        
        data = request.json
        file_path = data.get('file_path')
        record_id_column = data.get('record_id_column', 'id')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': 'File not found'
            }), 400
        
        changes = integrity_monitor.detect_changes(file_path, record_id_column)
        
        return jsonify({
            'status': 'success',
            'data': {
                'changes_detected': len(changes),
                'changes': [
                    {
                        'timestamp': change.timestamp,
                        'type': change.change_type,
                        'record_id': change.record_id,
                        'description': change.description,
                        'severity': change.severity
                    } for change in changes
                ]
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 