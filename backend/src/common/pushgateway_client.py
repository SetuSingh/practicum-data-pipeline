#!/usr/bin/env python3
"""
Pushgateway Client for Prometheus Metrics
Allows batch jobs to push metrics to Prometheus Pushgateway
"""

import requests
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PushgatewayClient:
    """Client for pushing metrics to Prometheus Pushgateway"""
    
    def __init__(self, pushgateway_url: str = "http://localhost:9092"):
        """
        Initialize pushgateway client
        
        Args:
            pushgateway_url: URL of the pushgateway service
        """
        self.pushgateway_url = pushgateway_url.rstrip('/')
        self.job_name = "batch_processing"
        
    def push_batch_metrics(self, metrics: Dict[str, Any], instance: str = "spark_batch") -> bool:
        """
        Push batch processing metrics to pushgateway
        
        Args:
            metrics: Dictionary containing processing metrics
            instance: Instance identifier for the metrics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert metrics to Prometheus format
            prometheus_metrics = self._convert_to_prometheus_format(metrics, instance)
            
            # Push to pushgateway
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{instance}"
            
            response = requests.post(
                url,
                data=prometheus_metrics,
                headers={'Content-Type': 'text/plain'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully pushed metrics to pushgateway: {len(metrics)} metrics")
                return True
            else:
                logger.error(f"Failed to push metrics: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error pushing metrics to pushgateway: {e}")
            return False
    
    def _convert_to_prometheus_format(self, metrics: Dict[str, Any], instance: str) -> str:
        """
        Convert metrics dictionary to Prometheus exposition format
        
        Args:
            metrics: Dictionary containing processing metrics
            instance: Instance identifier
            
        Returns:
            String in Prometheus exposition format
        """
        lines = []
        
        # Get pipeline type for labels
        pipeline_type = metrics.get('pipeline_type', 'batch')
        anonymization_method = metrics.get('anonymization_method', 'k_anonymity')
        
        # Processing duration
        if 'processing_time' in metrics:
            lines.append(f'# HELP processing_duration_seconds Time spent processing data records')
            lines.append(f'# TYPE processing_duration_seconds gauge')
            lines.append(f'processing_duration_seconds{{pipeline_type="{pipeline_type}",anonymization_method="{anonymization_method}"}} {metrics["processing_time"]}')
        
        # Throughput
        if 'throughput' in metrics:
            lines.append(f'# HELP processing_throughput_records_per_second Processing throughput in records per second')
            lines.append(f'# TYPE processing_throughput_records_per_second gauge')
            lines.append(f'processing_throughput_records_per_second{{pipeline_type="{pipeline_type}"}} {metrics["throughput"]}')
        
        # Records processed
        if 'total_records' in metrics:
            lines.append(f'# HELP records_processed_total Total number of records processed')
            lines.append(f'# TYPE records_processed_total counter')
            lines.append(f'records_processed_total{{pipeline_type="{pipeline_type}",status="completed"}} {metrics["total_records"]}')
        
        # Violations detected
        if 'violations' in metrics:
            lines.append(f'# HELP integrity_violations_total Total number of integrity violations detected')
            lines.append(f'# TYPE integrity_violations_total counter')
            lines.append(f'integrity_violations_total{{violation_type="compliance",severity="medium",resource_id="{pipeline_type}_job"}} {metrics["violations"]}')
        
        # Violation rate
        if 'violation_rate' in metrics:
            lines.append(f'# HELP compliance_violation_rate Rate of compliance violations')
            lines.append(f'# TYPE compliance_violation_rate gauge')
            lines.append(f'compliance_violation_rate{{pipeline_type="{pipeline_type}"}} {metrics["violation_rate"]}')
        
        # Anonymization methods used
        if 'anonymization_method' in metrics:
            lines.append(f'# HELP anonymization_operations_total Total number of anonymization operations')
            lines.append(f'# TYPE anonymization_operations_total counter')
            lines.append(f'anonymization_operations_total{{method="{anonymization_method}",pipeline_type="{pipeline_type}"}} {metrics.get("total_records", 1)}')
        
        # Processing rate
        if 'records_per_second' in metrics:
            lines.append(f'# HELP data_processing_rate_records_per_second Current data processing rate')
            lines.append(f'# TYPE data_processing_rate_records_per_second gauge')
            pipeline_type = metrics.get('pipeline_type', 'batch')
            lines.append(f'data_processing_rate_records_per_second{{pipeline_type="{pipeline_type}"}} {metrics["records_per_second"]}')
        
        # Average latency (for stream and hybrid)
        if 'average_latency_ms' in metrics:
            lines.append(f'# HELP average_processing_latency_ms Average processing latency in milliseconds')
            lines.append(f'# TYPE average_processing_latency_ms gauge')
            pipeline_type = metrics.get('pipeline_type', 'stream')
            lines.append(f'average_processing_latency_ms{{pipeline_type="{pipeline_type}"}} {metrics["average_latency_ms"]}')
        
        # Routing stats (for hybrid)
        if 'batch_routed' in metrics:
            lines.append(f'# HELP hybrid_batch_routed_total Records routed to batch processing')
            lines.append(f'# TYPE hybrid_batch_routed_total counter')
            lines.append(f'hybrid_batch_routed_total{{pipeline_type="hybrid"}} {metrics["batch_routed"]}')
            
        if 'stream_routed' in metrics:
            lines.append(f'# HELP hybrid_stream_routed_total Records routed to stream processing')
            lines.append(f'# TYPE hybrid_stream_routed_total counter')
            lines.append(f'hybrid_stream_routed_total{{pipeline_type="hybrid"}} {metrics["stream_routed"]}')
            
        return '\n'.join(lines) + '\n'
    
    def test_connection(self) -> bool:
        """
        Test connection to pushgateway
        
        Returns:
            True if pushgateway is reachable, False otherwise
        """
        try:
            url = f"{self.pushgateway_url}/metrics"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Pushgateway connection test failed: {e}")
            return False


# Global instance for easy access
pushgateway_client = PushgatewayClient() 