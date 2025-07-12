#!/usr/bin/env python3
"""
PostgreSQL-based Data Integrity Monitor
Enhanced version that integrates with PostgreSQL database for enterprise-grade monitoring
"""

import hashlib
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import sys
import os

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.postgres_connector import PostgreSQLConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IntegrityChangeEvent:
    """Enhanced data change event with PostgreSQL integration"""
    timestamp: str
    change_type: str  # 'record_modified', 'record_added', 'record_deleted', 'schema_changed'
    record_id: str
    old_hash: Optional[str]
    new_hash: Optional[str]
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    affected_fields: Optional[Dict] = None
    compliance_impact: Optional[str] = None

class PostgreSQLIntegrityMonitor:
    """
    Advanced Data Integrity Monitor with PostgreSQL backend
    
    This class provides enterprise-grade data integrity monitoring with:
    - PostgreSQL database backend for scalability
    - Role-based access control integration
    - Comprehensive audit trails
    - Real-time change detection
    - Compliance violation tracking
    """
    
    def __init__(self, db_connector: PostgreSQLConnector, user_id: str = None):
        """
        Initialize PostgreSQL-based integrity monitor
        
        Args:
            db_connector: PostgreSQL database connector
            user_id: ID of the user performing operations
        """
        self.db = db_connector
        self.user_id = user_id
        
        logger.info("PostgreSQL Integrity Monitor initialized")
    
    def compute_record_hash(self, record: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash for a single data record
        
        Args:
            record: Dictionary containing record data
            
        Returns:
            SHA256 hash string
        """
        # Convert record to consistent string representation
        record_string = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(record_string.encode()).hexdigest()
    
    def compute_file_hash(self, file_path: str) -> str:
        """
        Compute SHA256 hash for entire file
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash string
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def create_baseline_for_file(self, file_id: str, file_path: str, 
                                record_id_column: str = 'id') -> str:
        """
        Create integrity baseline for a data file
        
        Args:
            file_id: UUID of the file in database
            file_path: Path to the CSV file
            record_id_column: Column name to use as record identifier
            
        Returns:
            Baseline ID
        """
        logger.info(f"Creating integrity baseline for file: {file_id}")
        
        try:
            # Read the file
            df = pd.read_csv(file_path)
            
            # Compute file-level hash
            file_hash = self.compute_file_hash(file_path)
            
            # Compute record hashes
            record_hashes = {}
            for index, row in df.iterrows():
                record_dict = row.to_dict()
                record_id = str(record_dict.get(record_id_column, f"row_{index}"))
                record_hash = self.compute_record_hash(record_dict)
                record_hashes[record_id] = record_hash
                
                # Store individual record in database
                self.db.create_data_record(
                    file_id=file_id,
                    record_id=record_id,
                    original_data=record_dict,
                    record_hash=record_hash,
                    row_number=index + 1,
                    created_by=self.user_id
                )
            
            # Compute schema hash
            schema_info = {
                'columns': list(df.columns),
                'dtypes': df.dtypes.to_dict().__str__()
            }
            schema_hash = hashlib.sha256(
                json.dumps(schema_info, sort_keys=True).encode()
            ).hexdigest()
            
            # Store baseline in database
            baseline_id = self.db.create_integrity_baseline(
                file_id=file_id,
                baseline_name=f"Baseline for {file_path}",
                baseline_type='file',
                content_hash=file_hash,
                record_hashes=record_hashes,
                schema_hash=schema_hash,
                total_records=len(df),
                column_definitions=schema_info,
                created_by=self.user_id
            )
            
            logger.info(f"Baseline created successfully: {baseline_id}")
            return baseline_id
            
        except Exception as e:
            logger.error(f"Failed to create baseline: {e}")
            raise
    
    def detect_changes_in_file(self, file_id: str, file_path: str, 
                              record_id_column: str = 'id') -> List[IntegrityChangeEvent]:
        """
        Detect changes in a file against stored baseline
        
        Args:
            file_id: UUID of the file in database
            file_path: Path to the current CSV file
            record_id_column: Column name to use as record identifier
            
        Returns:
            List of detected changes
        """
        logger.info(f"Detecting changes in file: {file_id}")
        
        changes = []
        
        try:
            # Read current file
            df = pd.read_csv(file_path)
            
            # Get baseline data from database
            baselines = self.db.execute_query("""
                SELECT * FROM data_integrity_baselines 
                WHERE file_id = %s AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            """, (file_id,))
            
            if not baselines:
                logger.warning(f"No baseline found for file {file_id}")
                return changes
            
            baseline = baselines[0]
            stored_record_hashes = baseline['record_hashes']
            
            # Check schema changes first
            schema_changes = self._detect_schema_changes(file_id, df, baseline)
            changes.extend(schema_changes)
            
            # Get stored records from database
            stored_records = self.db.get_records_by_file(file_id)
            stored_record_ids = {record['record_id'] for record in stored_records}
            stored_record_map = {record['record_id']: record for record in stored_records}
            
            # Check each current record
            current_record_ids = set()
            
            for index, row in df.iterrows():
                record_dict = row.to_dict()
                record_id = str(record_dict.get(record_id_column, f"row_{index}"))
                current_hash = self.compute_record_hash(record_dict)
                
                current_record_ids.add(record_id)
                
                if record_id in stored_record_map:
                    stored_record = stored_record_map[record_id]
                    stored_hash = stored_record['record_hash']
                    
                    if current_hash != stored_hash:
                        # Record was modified
                        change = IntegrityChangeEvent(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            change_type='record_modified',
                            record_id=record_id,
                            old_hash=stored_hash,
                            new_hash=current_hash,
                            description=f"Record {record_id} was modified",
                            severity='high',
                            affected_fields=self._identify_changed_fields(
                                stored_record['original_data'], record_dict
                            ),
                            compliance_impact='medium'
                        )
                        changes.append(change)
                        
                        # Log to database
                        self._log_integrity_event(change, file_id)
                        
                else:
                    # New record added
                    change = IntegrityChangeEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        change_type='record_added',
                        record_id=record_id,
                        old_hash=None,
                        new_hash=current_hash,
                        description=f"New record {record_id} was added",
                        severity='medium',
                        compliance_impact='low'
                    )
                    changes.append(change)
                    self._log_integrity_event(change, file_id)
            
            # Check for deleted records
            for stored_id in stored_record_ids:
                if stored_id not in current_record_ids:
                    stored_record = stored_record_map[stored_id]
                    change = IntegrityChangeEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        change_type='record_deleted',
                        record_id=stored_id,
                        old_hash=stored_record['record_hash'],
                        new_hash=None,
                        description=f"Record {stored_id} was deleted",
                        severity='critical',
                        compliance_impact='high'
                    )
                    changes.append(change)
                    self._log_integrity_event(change, file_id)
            
            if changes:
                logger.warning(f"Found {len(changes)} integrity changes")
                for change in changes:
                    logger.warning(f"  {change.severity.upper()}: {change.description}")
            else:
                logger.info("No unauthorized changes detected")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            return []
    
    def _detect_schema_changes(self, file_id: str, current_df: pd.DataFrame, 
                              baseline: Dict) -> List[IntegrityChangeEvent]:
        """Detect schema and metadata changes"""
        changes = []
        
        try:
            stored_columns = baseline['column_definitions']['columns']
            current_columns = list(current_df.columns)
            
            # Check column changes
            if current_columns != stored_columns:
                change = IntegrityChangeEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    change_type='schema_changed',
                    record_id='schema',
                    old_hash=None,
                    new_hash=None,
                    description=f"Schema changed: columns went from {stored_columns} to {current_columns}",
                    severity='critical',
                    affected_fields={
                        'old_columns': stored_columns,
                        'new_columns': current_columns,
                        'added': list(set(current_columns) - set(stored_columns)),
                        'removed': list(set(stored_columns) - set(current_columns))
                    },
                    compliance_impact='critical'
                )
                changes.append(change)
                self._log_integrity_event(change, file_id)
            
            # Check significant row count changes (>10% difference)
            stored_count = baseline['total_records']
            current_count = len(current_df)
            
            if stored_count > 0 and abs(current_count - stored_count) / stored_count > 0.1:
                change = IntegrityChangeEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    change_type='metadata_changed',
                    record_id='row_count',
                    old_hash=None,
                    new_hash=None,
                    description=f"Significant row count change: {stored_count} → {current_count}",
                    severity='high',
                    affected_fields={
                        'old_count': stored_count,
                        'new_count': current_count,
                        'change_percentage': abs(current_count - stored_count) / stored_count * 100
                    },
                    compliance_impact='medium'
                )
                changes.append(change)
                self._log_integrity_event(change, file_id)
                
        except Exception as e:
            logger.error(f"Error detecting schema changes: {e}")
        
        return changes
    
    def _identify_changed_fields(self, old_data: Dict, new_data: Dict) -> Dict:
        """Identify which fields changed between two records"""
        changed_fields = {}
        
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            
            if old_value != new_value:
                changed_fields[key] = {
                    'old': old_value,
                    'new': new_value
                }
        
        return changed_fields
    
    def _log_integrity_event(self, change: IntegrityChangeEvent, file_id: str):
        """Log integrity event to database"""
        try:
            self.db.create_integrity_event(
                event_type=change.change_type,
                severity=change.severity,
                file_id=file_id,
                expected_hash=change.old_hash,
                actual_hash=change.new_hash,
                affected_fields=change.affected_fields,
                change_description=change.description,
                created_by=self.user_id
            )
            
            # Also log as compliance violation if critical
            if change.severity in ['critical', 'high'] and change.compliance_impact in ['high', 'critical']:
                self.db.create_compliance_violation(
                    file_id=file_id,
                    violation_type='integrity',
                    violation_category='unauthorized_change',
                    severity=change.severity,
                    description=f"Data integrity violation: {change.description}",
                    affected_columns=list(change.affected_fields.keys()) if change.affected_fields else None,
                    affected_records_count=1,
                    data_classification='restricted',
                    created_by=self.user_id
                )
            
        except Exception as e:
            logger.error(f"Failed to log integrity event: {e}")
    
    def get_integrity_status(self, file_id: str = None) -> Dict[str, Any]:
        """
        Get comprehensive integrity monitoring status
        
        Args:
            file_id: Optional file ID to filter by
            
        Returns:
            Dictionary with integrity statistics
        """
        try:
            if file_id:
                # File-specific statistics
                events = self.db.get_integrity_events()
                file_events = [e for e in events if e.get('file_id') == file_id]
                
                return {
                    'file_id': file_id,
                    'total_events': len(file_events),
                    'critical_events': len([e for e in file_events if e['severity'] == 'critical']),
                    'high_events': len([e for e in file_events if e['severity'] == 'high']),
                    'open_events': len([e for e in file_events if e['status'] == 'open']),
                    'last_check': max([e['created_at'] for e in file_events]) if file_events else None
                }
            else:
                # System-wide statistics
                stats = self.db.get_integrity_statistics()
                return {
                    'total_events': stats.get('total_events', 0),
                    'critical_events': stats.get('critical_events', 0),
                    'high_events': stats.get('high_events', 0),
                    'open_events': stats.get('open_events', 0),
                    'recent_events_24h': stats.get('recent_events_24h', 0),
                    'monitoring_active': True
                }
                
        except Exception as e:
            logger.error(f"Failed to get integrity status: {e}")
            return {'monitoring_active': False, 'error': str(e)}
    
    def get_change_history(self, file_id: str = None, record_id: str = None, 
                          limit: int = 100) -> List[Dict]:
        """
        Get change history from database
        
        Args:
            file_id: Optional file ID to filter by
            record_id: Optional record ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of change events
        """
        try:
            if record_id:
                # Get changes for specific record
                return self.db.get_record_changes(record_id)
            else:
                # Get general integrity events
                return self.db.get_integrity_events(limit=limit)
                
        except Exception as e:
            logger.error(f"Failed to get change history: {e}")
            return []
    
    def resolve_integrity_event(self, event_id: str, resolution_notes: str):
        """
        Resolve an integrity monitoring event
        
        Args:
            event_id: ID of the event to resolve
            resolution_notes: Notes about the resolution
        """
        try:
            query = """
                UPDATE data_integrity_events 
                SET status = 'resolved',
                    resolution_notes = %s,
                    resolved_by = %s,
                    resolved_at = NOW()
                WHERE id = %s
            """
            self.db.execute_update(query, (resolution_notes, self.user_id, event_id))
            logger.info(f"Resolved integrity event: {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to resolve integrity event: {e}")
            raise
    
    def check_user_permissions(self, user_id: str, action: str) -> bool:
        """
        Check if user has permissions for integrity monitoring actions
        
        Args:
            user_id: User ID to check
            action: Action to check ('read', 'write', 'admin')
            
        Returns:
            True if user has permission
        """
        return self.db.check_user_permission(user_id, 'integrity', action)
    
    def generate_integrity_report(self, file_id: str = None, 
                                 days_back: int = 30) -> Dict:
        """
        Generate comprehensive integrity monitoring report
        
        Args:
            file_id: Optional file ID to focus on
            days_back: Number of days to include in report
            
        Returns:
            Dictionary with report data
        """
        try:
            # Get recent events
            events = self.db.execute_query("""
                SELECT * FROM data_integrity_events 
                WHERE (%s IS NULL OR file_id = %s)
                AND created_at >= NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (file_id, file_id, days_back))
            
            # Get compliance violations
            violations = self.db.get_compliance_violations(
                file_id=file_id, 
                severity=None, 
                status='open'
            )
            
            # Generate summary
            report = {
                'report_date': datetime.now(timezone.utc).isoformat(),
                'scope': f"File {file_id}" if file_id else "System-wide",
                'period_days': days_back,
                'summary': {
                    'total_events': len(events),
                    'critical_events': len([e for e in events if e['severity'] == 'critical']),
                    'high_events': len([e for e in events if e['severity'] == 'high']),
                    'medium_events': len([e for e in events if e['severity'] == 'medium']),
                    'low_events': len([e for e in events if e['severity'] == 'low']),
                    'open_violations': len(violations),
                    'event_types': {}
                },
                'events': events,
                'violations': violations,
                'recommendations': []
            }
            
            # Count event types
            for event in events:
                event_type = event['event_type']
                if event_type not in report['summary']['event_types']:
                    report['summary']['event_types'][event_type] = 0
                report['summary']['event_types'][event_type] += 1
            
            # Generate recommendations
            if report['summary']['critical_events'] > 0:
                report['recommendations'].append(
                    "Critical integrity events detected - immediate investigation required"
                )
            
            if report['summary']['open_violations'] > 0:
                report['recommendations'].append(
                    f"{report['summary']['open_violations']} open compliance violations need resolution"
                )
            
            if len(events) == 0:
                report['recommendations'].append(
                    "No integrity events detected - monitoring system is functioning normally"
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate integrity report: {e}")
            return {'error': str(e)}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_monitor_for_user(user_id: str, 
                           db_host: str = 'localhost',
                           db_port: int = 5433,
                           db_name: str = 'compliance_db',
                           db_user: str = 'postgres',
                           db_password: str = 'postgres') -> PostgreSQLIntegrityMonitor:
    """
    Factory function to create a PostgreSQL integrity monitor for a user
    
    Args:
        user_id: ID of the user
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database username
        db_password: Database password
        
    Returns:
        Configured PostgreSQL integrity monitor
    """
    db_connector = PostgreSQLConnector(
        host=db_host,
        port=db_port,
        database=db_name,
        username=db_user,
        password=db_password
    )
    
    return PostgreSQLIntegrityMonitor(db_connector, user_id) 