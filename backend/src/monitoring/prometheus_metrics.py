#!/usr/bin/env python3
"""
Prometheus Metrics for Secure Data Pipeline
Comprehensive monitoring of data access, modifications, integrity, and performance
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from functools import wraps

logger = logging.getLogger(__name__)

# Create custom registry for better control
REGISTRY = CollectorRegistry()

# ============================================================================
# DATA ACCESS AND MODIFICATION METRICS
# ============================================================================

# Data access tracking
data_access_total = Counter(
    'data_access_total',
    'Total number of data access operations',
    ['user_id', 'user_role', 'resource_type', 'action'],
    registry=REGISTRY
)

data_modification_total = Counter(
    'data_modification_total',
    'Total number of data modification operations',
    ['user_id', 'user_role', 'operation_type', 'table_name'],
    registry=REGISTRY
)

# Data integrity monitoring
integrity_check_total = Counter(
    'integrity_check_total',
    'Total number of integrity checks performed',
    ['check_type', 'status'],
    registry=REGISTRY
)

integrity_violations_total = Counter(
    'integrity_violations_total',
    'Total number of integrity violations detected',
    ['violation_type', 'severity', 'resource_id'],
    registry=REGISTRY
)

unauthorized_access_attempts = Counter(
    'unauthorized_access_attempts_total',
    'Total number of unauthorized access attempts',
    ['user_id', 'resource_type', 'attempted_action'],
    registry=REGISTRY
)

# ============================================================================
# PROCESSING PIPELINE METRICS
# ============================================================================

# Processing performance
processing_duration_seconds = Histogram(
    'processing_duration_seconds',
    'Time spent processing data records',
    ['pipeline_type', 'anonymization_method'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=REGISTRY
)

records_processed_total = Counter(
    'records_processed_total',
    'Total number of records processed',
    ['pipeline_type', 'status'],
    registry=REGISTRY
)

processing_throughput = Gauge(
    'processing_throughput_records_per_second',
    'Current processing throughput in records per second',
    ['pipeline_type'],
    registry=REGISTRY
)

# Memory and resource usage
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Current memory usage in bytes',
    ['component'],
    registry=REGISTRY
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'Current CPU usage percentage',
    ['component'],
    registry=REGISTRY
)

# ============================================================================
# COMPLIANCE AND ANONYMIZATION METRICS
# ============================================================================

compliance_violations_total = Counter(
    'compliance_violations_total',
    'Total number of compliance violations',
    ['regulation', 'violation_type', 'severity'],
    registry=REGISTRY
)

anonymization_operations_total = Counter(
    'anonymization_operations_total',
    'Total number of anonymization operations',
    ['method', 'status'],
    registry=REGISTRY
)

anonymization_quality_score = Histogram(
    'anonymization_quality_score',
    'Quality score of anonymization (0-1)',
    ['method'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=REGISTRY
)

privacy_level_score = Histogram(
    'privacy_level_score',
    'Privacy level achieved by anonymization (0-1)',
    ['method'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=REGISTRY
)

# ============================================================================
# ENCRYPTION AND SECURITY METRICS
# ============================================================================

encryption_operations_total = Counter(
    'encryption_operations_total',
    'Total number of encryption/decryption operations',
    ['operation', 'context', 'status'],
    registry=REGISTRY
)

encryption_key_rotations_total = Counter(
    'encryption_key_rotations_total',
    'Total number of encryption key rotations',
    ['key_type', 'status'],
    registry=REGISTRY
)

tls_connections_total = Counter(
    'tls_connections_total',
    'Total number of TLS connections',
    ['endpoint', 'status'],
    registry=REGISTRY
)

# ============================================================================
# SYSTEM HEALTH METRICS
# ============================================================================

system_health_status = Gauge(
    'system_health_status',
    'Overall system health status (0=unhealthy, 1=healthy)',
    ['component'],
    registry=REGISTRY
)

database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections',
    ['database_name'],
    registry=REGISTRY
)

api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

# ============================================================================
# ALERTING METRICS
# ============================================================================

alert_notifications_total = Counter(
    'alert_notifications_total',
    'Total number of alert notifications sent',
    ['alert_type', 'severity', 'channel'],
    registry=REGISTRY
)

breach_detection_events = Counter(
    'breach_detection_events_total',
    'Total number of potential security breach events',
    ['event_type', 'severity'],
    registry=REGISTRY
)

# ============================================================================
# METRIC COLLECTION HELPERS
# ============================================================================

class MetricsCollector:
    """Centralized collector for all metrics"""
    def __init__(self):
        self.start_time = time.time()

        # Initialize gauges/counters with zero so they appear immediately in Prometheus
        # ---------------------------------------------------
        # System health default
        system_health_status.labels(component='api_server').set(1)

        # Counters with zero baseline so 'sum(...)' queries return 0 instead of no data
        data_access_total.labels(user_id='system', user_role='system', resource_type='init', action='init').inc(0)
        integrity_violations_total.labels(violation_type='init', severity='low', resource_id='init').inc(0)
        unauthorized_access_attempts.labels(user_id='system', resource_type='init', attempted_action='init').inc(0)
        compliance_violations_total.labels(regulation='init', violation_type='init', severity='low').inc(0)
        breach_detection_events.labels(event_type='init', severity='low').inc(0)
        encryption_operations_total.labels(operation='init', context='init', status='init').inc(0)
        api_requests_total.labels(method='INIT', endpoint='init', status_code='200').inc(0)
        processing_throughput.labels(pipeline_type='init').set(0)
        memory_usage_bytes.labels(component='api_server').set(0)
        cpu_usage_percent.labels(component='api_server').set(0)

        logger.info("MetricsCollector initialized")

    def track_data_access(self, user_id: str, user_role: str, resource_type: str, action: str):
        """Track data access operation"""
        data_access_total.labels(
            user_id=user_id,
            user_role=user_role,
            resource_type=resource_type,
            action=action
        ).inc()
        logger.debug(f"Tracked data access: {user_role} {action} {resource_type}")

    def track_data_modification(self, user_id: str, user_role: str, operation_type: str, table_name: str):
        """Track data modification operation"""
        data_modification_total.labels(
            user_id=user_id,
            user_role=user_role,
            operation_type=operation_type,
            table_name=table_name
        ).inc()
        logger.debug(f"Tracked data modification: {user_role} {operation_type} {table_name}")

    def track_integrity_check(self, check_type: str, status: str):
        """Track integrity check operation"""
        integrity_check_total.labels(
            check_type=check_type,
            status=status
        ).inc()
        logger.debug(f"Tracked integrity check: {check_type} - {status}")

    def track_integrity_violation(self, violation_type: str, severity: str, resource_id: str):
        """Track integrity violation"""
        integrity_violations_total.labels(
            violation_type=violation_type,
            severity=severity,
            resource_id=resource_id
        ).inc()

        # Also trigger breach detection if critical
        if severity == 'critical':
            breach_detection_events.labels(
                event_type='integrity_violation',
                severity='critical'
            ).inc()

        logger.warning(f"Tracked integrity violation: {violation_type} ({severity}) - {resource_id}")

    def track_unauthorized_access(self, user_id: str, resource_type: str, attempted_action: str):
        """Track unauthorized access attempt"""
        unauthorized_access_attempts.labels(
            user_id=user_id,
            resource_type=resource_type,
            attempted_action=attempted_action
        ).inc()

        # Trigger breach detection
        breach_detection_events.labels(
            event_type='unauthorized_access',
            severity='high'
        ).inc()

        logger.warning(f"Tracked unauthorized access: {user_id} attempted {attempted_action} on {resource_type}")

    def track_processing_performance(self, pipeline_type: str, duration: float,
                                   records_count: int, anonymization_method: str = "none"):
        """Track processing performance metrics"""
        # Record duration
        processing_duration_seconds.labels(
            pipeline_type=pipeline_type,
            anonymization_method=anonymization_method
        ).observe(duration)

        # Record throughput
        if duration > 0:
            throughput = records_count / duration
            processing_throughput.labels(pipeline_type=pipeline_type).set(throughput)

        # Record processed records
        records_processed_total.labels(
            pipeline_type=pipeline_type,
            status='completed'
        ).inc(records_count)

        logger.info(f"Tracked processing: {pipeline_type} - {records_count} records in {duration:.3f}s")

    def track_compliance_violation(self, regulation: str, violation_type: str, severity: str):
        """Track compliance violation"""
        compliance_violations_total.labels(
            regulation=regulation,
            violation_type=violation_type,
            severity=severity
        ).inc()

        if severity in ['critical', 'high']:
            breach_detection_events.labels(
                event_type='compliance_violation',
                severity=severity
            ).inc()

        logger.warning(f"Tracked compliance violation: {regulation} - {violation_type} ({severity})")

    def track_anonymization_quality(self, method: str, quality_score: float, privacy_level: float):
        """Track anonymization quality metrics"""
        anonymization_quality_score.labels(method=method).observe(quality_score)
        privacy_level_score.labels(method=method).observe(privacy_level)

        anonymization_operations_total.labels(
            method=method,
            status='completed'
        ).inc()

        logger.debug(f"Tracked anonymization quality: {method} - Q:{quality_score:.3f} P:{privacy_level:.3f}")

    def track_encryption_operation(self, operation: str, context: str, status: str):
        """Track encryption/decryption operation"""
        encryption_operations_total.labels(
            operation=operation,
            context=context,
            status=status
        ).inc()
        logger.debug(f"Tracked encryption operation: {operation} {context} - {status}")

    def track_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Track API request metrics"""
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def update_system_health(self, component: str, is_healthy: bool):
        """Update system health status"""
        system_health_status.labels(component=component).set(1 if is_healthy else 0)

    def update_resource_usage(self, component: str, memory_bytes: int, cpu_percent: float):
        """Update resource usage metrics"""
        memory_usage_bytes.labels(component=component).set(memory_bytes)
        cpu_usage_percent.labels(component=component).set(cpu_percent)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(REGISTRY).decode('utf-8')

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary for dashboard"""
        uptime = time.time() - self.start_time

        return {
            'uptime_seconds': uptime,
            'data_access_operations': sum(
                child._value.get() for child in data_access_total._metrics.values()
            ),
            'integrity_violations': sum(
                child._value.get() for child in integrity_violations_total._metrics.values()
            ),
            'unauthorized_attempts': sum(
                child._value.get() for child in unauthorized_access_attempts._metrics.values()
            ),
            'compliance_violations': sum(
                child._value.get() for child in compliance_violations_total._metrics.values()
            ),
            'breach_events': sum(
                child._value.get() for child in breach_detection_events._metrics.values()
            ),
            'encryption_operations': sum(
                child._value.get() for child in encryption_operations_total._metrics.values()
            ),
            'api_requests': sum(
                child._value.get() for child in api_requests_total._metrics.values()
            ),
            'system_health': 'healthy' if all(
                child._value.get() == 1 for child in system_health_status._metrics.values()
            ) else 'degraded'
        }


# ============================================================================
# DECORATORS FOR AUTOMATIC METRIC COLLECTION
# ============================================================================

def track_api_metrics(endpoint: str):
    """Decorator to automatically track API metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.track_api_request(
                    method='POST',  # Default, should be extracted from request
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration
                )
        return wrapper
    return decorator

def track_processing_metrics(pipeline_type: str):
    """Decorator to automatically track processing metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Extract record count from result if available
                records_count = 0
                if isinstance(result, dict) and 'records_processed' in result:
                    records_count = result['records_processed']

                metrics_collector.track_processing_performance(
                    pipeline_type=pipeline_type,
                    duration=duration,
                    records_count=records_count
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                records_processed_total.labels(
                    pipeline_type=pipeline_type,
                    status='failed'
                ).inc()
                raise
        return wrapper
    return decorator


# Global metrics collector instance
metrics_collector = MetricsCollector() 