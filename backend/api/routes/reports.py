#!/usr/bin/env python3
"""
Reports API Routes
Provides comprehensive reporting endpoints querying database for dashboard
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any
from datetime import datetime, timedelta

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/summary')
def get_reports_summary():
    """Get overall reports summary for dashboard"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get comprehensive statistics
        system_stats = db_connector.get_system_statistics()
        integrity_stats = db_connector.get_integrity_statistics()
        
        # Get recent processing jobs
        recent_jobs = db_connector.execute_query("""
            SELECT j.*, f.filename, f.status as file_status,
                   u.username as created_by_username
            FROM data_processing_jobs j
            JOIN data_files f ON j.file_id = f.id
            LEFT JOIN data_users u ON j.created_by = u.id
            ORDER BY j.created_at DESC
            LIMIT 10
        """)
        
        # Get recent violations
        recent_violations = db_connector.execute_query("""
            SELECT cv.*, f.filename
            FROM data_compliance_violations cv
            JOIN data_files f ON cv.file_id = f.id
            WHERE cv.created_at >= NOW() - INTERVAL '7 days'
            ORDER BY cv.created_at DESC
            LIMIT 20
        """)
        
        # Calculate violation trends
        violation_trends = db_connector.execute_query("""
            SELECT 
                DATE(cv.created_at) as date,
                COUNT(*) as violations_count,
                COUNT(DISTINCT cv.file_id) as files_affected
            FROM data_compliance_violations cv
            WHERE cv.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(cv.created_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        
        return jsonify({
            'status': 'success',
            'summary': {
                'system_statistics': dict(system_stats),
                'integrity_statistics': dict(integrity_stats),
                'recent_jobs': [dict(job) for job in recent_jobs],
                'recent_violations': [dict(violation) for violation in recent_violations],
                'violation_trends': [dict(trend) for trend in violation_trends],
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/processing-jobs')
def get_processing_jobs_report():
    """Get detailed processing jobs report"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get query parameters
        status = request.args.get('status')
        pipeline_type = request.args.get('pipeline_type')
        days_back = request.args.get('days_back', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Build query with filters
        where_conditions = ["j.created_at >= NOW() - INTERVAL '%s days'" % days_back]
        params = []
        
        if status:
            where_conditions.append("j.status = %s")
            params.append(status)
        
        if pipeline_type:
            where_conditions.append("j.pipeline_type = %s")
            params.append(pipeline_type)
        
        query = f"""
            SELECT j.*, f.filename, f.file_size, f.total_records,
                   f.valid_records, f.invalid_records, f.compliance_report,
                   u.username as created_by_username,
                   ft.label as file_type_label
            FROM data_processing_jobs j
            JOIN data_files f ON j.file_id = f.id
            LEFT JOIN data_users u ON j.created_by = u.id
            LEFT JOIN data_file_types ft ON f.file_type_id = ft.id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY j.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        jobs = db_connector.execute_query(query, tuple(params))
        
        # Calculate summary statistics
        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j['status'] == 'completed'])
        failed_jobs = len([j for j in jobs if j['status'] == 'failed'])
        total_records_processed = sum(j['records_processed'] or 0 for j in jobs)
        
        return jsonify({
            'status': 'success',
            'report': {
                'jobs': [dict(job) for job in jobs],
                'summary': {
                    'total_jobs': total_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                    'total_records_processed': total_records_processed
                },
                'filters': {
                    'status': status,
                    'pipeline_type': pipeline_type,
                    'days_back': days_back
                },
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/compliance-violations')
def get_compliance_violations_report():
    """Get detailed compliance violations report"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        # Get query parameters
        file_id = request.args.get('file_id')
        severity = request.args.get('severity')
        violation_type = request.args.get('violation_type')
        days_back = request.args.get('days_back', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Build query with filters
        where_conditions = ["cv.created_at >= NOW() - INTERVAL '%s days'" % days_back]
        params = []
        
        if file_id:
            where_conditions.append("cv.file_id = %s")
            params.append(file_id)
        
        if severity:
            where_conditions.append("cv.severity = %s")
            params.append(severity)
        
        if violation_type:
            where_conditions.append("cv.violation_type = %s")
            params.append(violation_type)
        
        query = f"""
            SELECT cv.*, f.filename, f.file_size,
                   u.username as created_by_username,
                   dr.record_id, dr.row_number
            FROM data_compliance_violations cv
            JOIN data_files f ON cv.file_id = f.id
            LEFT JOIN data_users u ON cv.created_by = u.id
            LEFT JOIN data_records dr ON cv.record_id = dr.id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY cv.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        violations = db_connector.execute_query(query, tuple(params))
        
        # Calculate violation statistics
        violation_stats = db_connector.execute_query(f"""
            SELECT 
                violation_type,
                severity,
                COUNT(*) as count,
                COUNT(DISTINCT file_id) as files_affected
            FROM data_compliance_violations cv
            WHERE {' AND '.join(where_conditions[:-1]) if len(where_conditions) > 1 else where_conditions[0]}
            GROUP BY violation_type, severity
            ORDER BY count DESC
        """, tuple(params[:-1]))
        
        # Get top affected files
        top_files = db_connector.execute_query(f"""
            SELECT f.filename, f.id as file_id,
                   COUNT(cv.id) as violation_count,
                   COUNT(DISTINCT cv.violation_type) as violation_types_count
            FROM data_compliance_violations cv
            JOIN data_files f ON cv.file_id = f.id
            WHERE {' AND '.join(where_conditions[:-1]) if len(where_conditions) > 1 else where_conditions[0]}
            GROUP BY f.id, f.filename
            ORDER BY violation_count DESC
            LIMIT 10
        """, tuple(params[:-1]))
        
        return jsonify({
            'status': 'success',
            'report': {
                'violations': [dict(violation) for violation in violations],
                'statistics': [dict(stat) for stat in violation_stats],
                'top_affected_files': [dict(file) for file in top_files],
                'summary': {
                    'total_violations': len(violations),
                    'unique_files_affected': len(set(v['file_id'] for v in violations)),
                    'violation_types': len(set(v['violation_type'] for v in violations))
                },
                'filters': {
                    'file_id': file_id,
                    'severity': severity,
                    'violation_type': violation_type,
                    'days_back': days_back
                },
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/data-records')
def get_data_records_report():
    """Get data records report for specific file"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        file_id = request.args.get('file_id')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if not file_id:
            return jsonify({'error': 'file_id parameter is required'}), 400
        
        # Get records for the file
        records = db_connector.execute_query("""
            SELECT dr.*, 
                   COUNT(cv.id) as violation_count,
                   ARRAY_AGG(cv.violation_type) FILTER (WHERE cv.violation_type IS NOT NULL) as violation_types
            FROM data_records dr
            LEFT JOIN data_compliance_violations cv ON dr.id = cv.record_id
            WHERE dr.file_id = %s
            GROUP BY dr.id
            ORDER BY dr.row_number
            LIMIT %s OFFSET %s
        """, (file_id, limit, offset))
        
        # Get total count for pagination
        total_count = db_connector.execute_query("""
            SELECT COUNT(*) as count FROM data_records WHERE file_id = %s
        """, (file_id,))[0]['count']
        
        # Get file information
        file_info = db_connector.get_file_by_id(file_id)
        
        return jsonify({
            'status': 'success',
            'report': {
                'file_info': dict(file_info) if file_info else None,
                'records': [dict(record) for record in records],
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                },
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/performance-metrics')
def get_performance_metrics():
    """Get performance metrics for different pipeline types"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        days_back = request.args.get('days_back', 30, type=int)
        
        # Get performance metrics by pipeline type
        performance_metrics = db_connector.execute_query("""
            SELECT 
                pipeline_type,
                COUNT(*) as total_jobs,
                AVG(records_processed) as avg_records_processed,
                AVG(throughput_per_second) as avg_throughput,
                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time_seconds,
                MAX(throughput_per_second) as max_throughput,
                MIN(throughput_per_second) as min_throughput
            FROM data_processing_jobs
            WHERE status = 'completed' 
            AND started_at IS NOT NULL 
            AND completed_at IS NOT NULL
            AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY pipeline_type
            ORDER BY avg_throughput DESC
        """ % days_back)
        
        # Get processing trends over time
        processing_trends = db_connector.execute_query("""
            SELECT 
                DATE(created_at) as date,
                pipeline_type,
                COUNT(*) as jobs_count,
                AVG(records_processed) as avg_records,
                AVG(throughput_per_second) as avg_throughput
            FROM data_processing_jobs
            WHERE status = 'completed'
            AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at), pipeline_type
            ORDER BY date DESC, pipeline_type
        """ % days_back)
        
        return jsonify({
            'status': 'success',
            'report': {
                'performance_by_pipeline': [dict(metric) for metric in performance_metrics],
                'processing_trends': [dict(trend) for trend in processing_trends],
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/audit-trail')
def get_audit_trail():
    """Get audit trail report"""
    try:
        from app import db_connector
        
        if not db_connector:
            return jsonify({'error': 'Database not connected'}), 500
        
        action_type = request.args.get('action_type')
        user_id = request.args.get('user_id')
        hours_back = request.args.get('hours_back', 24, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Get audit log entries
        audit_entries = db_connector.get_audit_log(user_id, action_type, hours_back, limit)
        
        # Get audit statistics
        audit_stats = db_connector.execute_query("""
            SELECT 
                action_type,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users
            FROM system_audit_log
            WHERE created_at >= NOW() - INTERVAL '%s hours'
            GROUP BY action_type
            ORDER BY count DESC
        """ % hours_back)
        
        return jsonify({
            'status': 'success',
            'report': {
                'audit_entries': [dict(entry) for entry in audit_entries],
                'audit_statistics': [dict(stat) for stat in audit_stats],
                'filters': {
                    'action_type': action_type,
                    'user_id': user_id,
                    'hours_back': hours_back
                },
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 