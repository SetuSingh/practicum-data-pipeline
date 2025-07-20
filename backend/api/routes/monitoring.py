#!/usr/bin/env python3
"""
Monitoring API Routes
Provides Prometheus metrics, system health, and monitoring endpoints
"""

import os
import sys
import psutil
from flask import Blueprint, Response, jsonify, request
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

bp = Blueprint('monitoring', __name__, url_prefix='/api')

@bp.route('/metrics')
def prometheus_metrics():
    """Expose Prometheus metrics endpoint"""
    try:
        from src.monitoring.prometheus_metrics import metrics_collector
        from app import db_connector
        
        # Check for system authentication (API key or system role)
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if api_key:
            # System authentication via API key
            if api_key not in ['prometheus_key_2024', 'grafana_key_2024']:
                return Response("# Access denied: Invalid API key\n", mimetype='text/plain'), 403
        else:
            # User-based authentication
            user_role = request.headers.get('X-User-Role', 'anonymous')
            if db_connector and user_role != 'anonymous':
                try:
                    from api.routes.files import _get_user_id_for_role
                    user_id = _get_user_id_for_role(db_connector, user_role)
                    has_permission = db_connector.check_user_permission(user_id, 'metrics', 'read')
                    if not has_permission:
                        return Response("# Access denied: Insufficient permissions\n", mimetype='text/plain'), 403
                except Exception as e:
                    print(f"Permission check failed for metrics: {e}")
                    # Allow system monitoring tools to continue
                    pass
        
        # Update system resource metrics
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        metrics_collector.update_resource_usage(
            component='api_server',
            memory_bytes=memory_info.rss,
            cpu_percent=cpu_percent
        )
        
        # Update system health
        metrics_collector.update_system_health('api_server', True)
        metrics_collector.update_system_health('database', True)  # TODO: Check actual DB health
        
        # Return metrics in Prometheus format
        metrics_data = metrics_collector.get_metrics()
        return Response(metrics_data, mimetype='text/plain')
        
    except Exception as e:
        return Response(f"# Error generating metrics: {str(e)}\n", mimetype='text/plain'), 500

@bp.route('/health')
def health_check():
    """System health check endpoint"""
    try:
        from src.monitoring.prometheus_metrics import metrics_collector
        from app import db_connector
        
        # Check database connection
        db_healthy = False
        try:
            if db_connector:
                test_result = db_connector.execute_query("SELECT 1 as test")
                db_healthy = len(test_result) > 0
        except Exception as e:
            db_healthy = False
        
        # Get system resource usage
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        # Get disk usage
        disk_usage = psutil.disk_usage('/')
        
        health_status = {
            'status': 'healthy' if db_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': {
                    'status': 'healthy' if db_healthy else 'unhealthy',
                    'details': 'Connection successful' if db_healthy else 'Connection failed'
                },
                'api_server': {
                    'status': 'healthy',
                    'memory_usage_mb': round(memory_info.rss / 1024 / 1024, 2),
                    'cpu_usage_percent': cpu_percent
                },
                'disk': {
                    'status': 'healthy' if disk_usage.percent < 90 else 'warning',
                    'usage_percent': disk_usage.percent,
                    'free_gb': round(disk_usage.free / 1024**3, 2)
                }
            },
            'metrics_summary': metrics_collector.get_metrics_summary()
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@bp.route('/alerts')
def get_alerts():
    """Get current system alerts"""
    try:
        from src.monitoring.prometheus_metrics import metrics_collector
        
        # Get metrics summary to determine alerts
        summary = metrics_collector.get_metrics_summary()
        
        alerts = []
        
        # Check for integrity violations
        if summary.get('integrity_violations', 0) > 0:
            alerts.append({
                'type': 'integrity_violation',
                'severity': 'high',
                'message': f"{summary['integrity_violations']} integrity violations detected",
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Check for unauthorized access attempts
        if summary.get('unauthorized_attempts', 0) > 0:
            alerts.append({
                'type': 'unauthorized_access',
                'severity': 'critical',
                'message': f"{summary['unauthorized_attempts']} unauthorized access attempts",
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Check for compliance violations
        if summary.get('compliance_violations', 0) > 0:
            alerts.append({
                'type': 'compliance_violation',
                'severity': 'high',
                'message': f"{summary['compliance_violations']} compliance violations detected",
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Check for breach events
        if summary.get('breach_events', 0) > 0:
            alerts.append({
                'type': 'security_breach',
                'severity': 'critical',
                'message': f"{summary['breach_events']} potential security breach events",
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Check system health
        if summary.get('system_health') != 'healthy':
            alerts.append({
                'type': 'system_health',
                'severity': 'medium',
                'message': f"System health is {summary['system_health']}",
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'alert_count': len(alerts),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/metrics/summary')
def metrics_summary():
    """Get metrics summary for dashboard"""
    try:
        from src.monitoring.prometheus_metrics import metrics_collector
        
        summary = metrics_collector.get_metrics_summary()
        
        return jsonify({
            'status': 'success',
            'data': summary,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/integrity/check', methods=['POST'])
def trigger_integrity_check():
    """Trigger manual integrity check"""
    try:
        from src.monitoring.prometheus_metrics import metrics_collector
        from common.encryption_engine import change_monitor
        
        # Trigger integrity check
        metrics_collector.track_integrity_check('manual', 'triggered')
        
        # Get change history
        changes = change_monitor.get_change_history()
        
        return jsonify({
            'status': 'success',
            'message': 'Integrity check triggered',
            'changes_detected': len(changes),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/encryption/status')
def encryption_status():
    """Get encryption system status"""
    try:
        from common.encryption_engine import encryption_engine
        from src.monitoring.prometheus_metrics import metrics_collector
        
        # Track encryption status check
        metrics_collector.track_encryption_operation('status_check', 'system', 'success')
        
        status = {
            'status': 'active',
            'algorithm': 'AES-256-GCM',
            'key_rotation_status': 'scheduled',
            'vault_integration': 'disabled',  # TODO: Check actual Vault status
            'encryption_operations': metrics_collector.get_metrics_summary().get('encryption_operations', 0)
        }
        
        return jsonify({
            'status': 'success',
            'data': status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500 