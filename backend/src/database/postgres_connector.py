#!/usr/bin/env python3
"""
PostgreSQL Database Connector for Data Integrity Monitoring System
Provides comprehensive database operations for all schema tables
"""

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import logging
from contextlib import contextmanager
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLConnector:
    """
    PostgreSQL database connector with comprehensive operations
    for data integrity monitoring system
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 5432,
                 database: str = "compliance_db",
                 username: str = "postgres",
                 password: str = "postgres"):
        """
        Initialize PostgreSQL connector
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        
        # Connection pool for performance
        self._connection = None
        
        # Initialize connection
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            logger.info(f"Connected to PostgreSQL database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursors"""
        if not self._connection or self._connection.closed:
            self._connect()
        
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple = None) -> str:
        """Execute an insert query and return the ID"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an update query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    # ============================================================================
    # USER MANAGEMENT OPERATIONS
    # ============================================================================
    
    def create_user(self, username: str, email: str, full_name: str, 
                   role_code: str, password_hash: str = None,
                   created_by: str = None) -> str:
        """Create a new user"""
        query = """
            INSERT INTO data_users (username, email, full_name, role_id, password_hash, created_by)
            SELECT %s, %s, %s, r.id, %s, %s
            FROM core_user_roles r
            WHERE r.code = %s
            RETURNING id
        """
        params = (username, email, full_name, password_hash, created_by, role_code)
        return self.execute_insert(query, params)
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        query = """
            SELECT u.*, r.code as role_code, r.label as role_label
            FROM data_users u
            JOIN core_user_roles r ON u.role_id = r.id
            WHERE u.username = %s AND u.is_active = TRUE
        """
        results = self.execute_query(query, (username,))
        return results[0] if results else None
    
    def get_user_permissions(self, user_id: str) -> List[Dict]:
        """Get all permissions for a user"""
        query = """
            SELECT p.code, p.label, p.resource_type, p.action
            FROM user_permissions 
            WHERE user_id = %s
        """
        return self.execute_query(query, (user_id,))
    
    def update_user_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        query = """
            UPDATE data_users 
            SET last_login = NOW()
            WHERE id = %s
        """
        self.execute_update(query, (user_id,))
    
    # ============================================================================
    # FILE MANAGEMENT OPERATIONS
    # ============================================================================
    
    def create_data_file(self, filename: str, original_filename: str, 
                        file_path: str, file_size: int, file_hash: str,
                        mime_type: str, file_type_code: str,
                        created_by: str) -> str:
        """Create a new data file record"""
        query = """
            INSERT INTO data_files (
                filename, original_filename, file_path, file_size, 
                file_hash, mime_type, file_type_id, created_by
            )
            SELECT %s, %s, %s, %s, %s, %s, ft.id, %s
            FROM data_file_types ft
            WHERE ft.code = %s
            RETURNING id
        """
        params = (filename, original_filename, file_path, file_size, 
                 file_hash, mime_type, created_by, file_type_code)
        return self.execute_insert(query, params)
    
    def update_file_processing_status(self, file_id: str, status: str, 
                                    total_records: int = None,
                                    valid_records: int = None,
                                    invalid_records: int = None,
                                    compliance_report: Dict = None,
                                    updated_by: str = None):
        """Update file processing status"""
        query = """
            UPDATE data_files 
            SET status = %s,
                total_records = COALESCE(%s, total_records),
                valid_records = COALESCE(%s, valid_records),
                invalid_records = COALESCE(%s, invalid_records),
                compliance_report = COALESCE(%s, compliance_report),
                updated_by = %s
            WHERE id = %s
        """
        params = (status, total_records, valid_records, invalid_records,
                 json.dumps(compliance_report) if compliance_report else None,
                 updated_by, file_id)
        self.execute_update(query, params)
    
    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        """Get file by ID"""
        query = """
            SELECT f.*, ft.code as file_type_code, ft.label as file_type_label,
                   u.username as uploaded_by_username
            FROM data_files f
            LEFT JOIN data_file_types ft ON f.file_type_id = ft.id
            LEFT JOIN data_users u ON f.created_by = u.id
            WHERE f.id = %s
        """
        results = self.execute_query(query, (file_id,))
        return results[0] if results else None
    
    def get_files_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get files uploaded by a user"""
        query = """
            SELECT f.*, ft.code as file_type_code
            FROM data_files f
            LEFT JOIN data_file_types ft ON f.file_type_id = ft.id
            WHERE f.created_by = %s
            ORDER BY f.created_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    # ============================================================================
    # PROCESSING JOB OPERATIONS
    # ============================================================================
    
    def create_processing_job(self, job_name: str, file_id: str, 
                            pipeline_type: str, processor_config: Dict,
                            created_by: str) -> str:
        """Create a new processing job"""
        query = """
            INSERT INTO data_processing_jobs (
                job_name, file_id, pipeline_type, processor_config, created_by
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (job_name, file_id, pipeline_type, 
                 json.dumps(processor_config), created_by)
        return self.execute_insert(query, params)
    
    def update_job_status(self, job_id: str, status: str, progress: int = None,
                         error_message: str = None, records_processed: int = None,
                         throughput_per_second: float = None, updated_by: str = None):
        """Update processing job status"""
        query = """
            UPDATE data_processing_jobs 
            SET status = %s,
                progress = COALESCE(%s, progress),
                error_message = COALESCE(%s, error_message),
                records_processed = COALESCE(%s, records_processed),
                throughput_per_second = COALESCE(%s, throughput_per_second),
                updated_by = %s,
                started_at = CASE WHEN %s = 'running' AND started_at IS NULL THEN NOW() ELSE started_at END,
                completed_at = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE completed_at END
            WHERE id = %s
        """
        params = (status, progress, error_message, records_processed,
                 throughput_per_second, updated_by, status, status, job_id)
        self.execute_update(query, params)
    
    def get_active_jobs(self) -> List[Dict]:
        """Get all active processing jobs"""
        query = """
            SELECT j.*, f.filename, u.username as created_by_username
            FROM data_processing_jobs j
            JOIN data_files f ON j.file_id = f.id
            LEFT JOIN data_users u ON j.created_by = u.id
            WHERE j.status IN ('pending', 'running')
            ORDER BY j.created_at DESC
        """
        return self.execute_query(query)
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict]:
        """Get processing job by ID"""
        query = """
            SELECT j.*, f.filename, u.username as created_by_username
            FROM data_processing_jobs j
            JOIN data_files f ON j.file_id = f.id
            LEFT JOIN data_users u ON j.created_by = u.id
            WHERE j.id = %s
        """
        results = self.execute_query(query, (job_id,))
        return results[0] if results else None
    
    # ============================================================================
    # DATA RECORD OPERATIONS
    # ============================================================================
    
    def create_data_record(self, file_id: str, record_id: str, 
                          original_data: Dict, record_hash: str,
                          job_id: str = None, row_number: int = None,
                          has_pii: bool = False, has_violations: bool = False,
                          violation_types: List[str] = None,
                          compliance_score: float = None,
                          created_by: str = None) -> str:
        """Create a new data record"""
        query = """
            INSERT INTO data_records (
                file_id, record_id, original_data, record_hash, job_id,
                row_number, has_pii, has_violations, violation_types,
                compliance_score, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (file_id, record_id, json.dumps(original_data), record_hash,
                 job_id, row_number, has_pii, has_violations, violation_types,
                 compliance_score, created_by)
        return self.execute_insert(query, params)
    
    def update_data_record(self, record_id: str, new_data: Dict, 
                          changed_fields: Dict, change_reason: str,
                          updated_by: str) -> str:
        """Update a data record and log the change"""
        # First update the record
        new_hash = hashlib.sha256(json.dumps(new_data, sort_keys=True).encode()).hexdigest()
        
        with self.get_cursor() as cursor:
            # Get current record
            cursor.execute("""
                SELECT id, record_hash, original_data 
                FROM data_records 
                WHERE id = %s
            """, (record_id,))
            
            current_record = cursor.fetchone()
            if not current_record:
                raise ValueError(f"Record {record_id} not found")
            
            old_hash = current_record['record_hash']
            old_data = current_record['original_data']
            
            # Update record
            cursor.execute("""
                UPDATE data_records 
                SET original_data = %s, record_hash = %s, updated_by = %s
                WHERE id = %s
            """, (json.dumps(new_data), new_hash, updated_by, record_id))
            
            # Log the change
            cursor.execute("""
                INSERT INTO data_record_changes (
                    record_id, change_type, changed_fields, change_reason,
                    change_source, old_hash, new_hash, created_by
                )
                VALUES (%s, 'UPDATE', %s, %s, 'user', %s, %s, %s)
                RETURNING id
            """, (record_id, json.dumps(changed_fields), change_reason,
                 old_hash, new_hash, updated_by))
            
            change_id = cursor.fetchone()['id']
            self._connection.commit()
            
            return change_id
    
    def get_records_by_file(self, file_id: str, limit: int = 100) -> List[Dict]:
        """Get data records for a file"""
        query = """
            SELECT * FROM data_records 
            WHERE file_id = %s 
            ORDER BY row_number 
            LIMIT %s
        """
        return self.execute_query(query, (file_id, limit))
    
    def get_record_changes(self, record_id: str) -> List[Dict]:
        """Get change history for a record"""
        query = """
            SELECT rc.*, u.username as changed_by_username
            FROM data_record_changes rc
            LEFT JOIN data_users u ON rc.created_by = u.id
            WHERE rc.record_id = %s
            ORDER BY rc.created_at DESC
        """
        return self.execute_query(query, (record_id,))
    
    # ============================================================================
    # INTEGRITY MONITORING OPERATIONS
    # ============================================================================
    
    def create_integrity_baseline(self, file_id: str, baseline_name: str,
                                 baseline_type: str, content_hash: str,
                                 record_hashes: Dict, schema_hash: str = None,
                                 total_records: int = None,
                                 column_definitions: Dict = None,
                                 created_by: str = None) -> str:
        """Create integrity baseline"""
        query = """
            INSERT INTO data_integrity_baselines (
                file_id, baseline_name, baseline_type, content_hash,
                record_hashes, schema_hash, total_records, 
                column_definitions, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (file_id, baseline_name, baseline_type, content_hash,
                 json.dumps(record_hashes), schema_hash, total_records,
                 json.dumps(column_definitions) if column_definitions else None,
                 created_by)
        return self.execute_insert(query, params)
    
    def create_integrity_event(self, event_type: str, severity: str,
                              file_id: str = None, record_id: str = None,
                              baseline_id: str = None, expected_hash: str = None,
                              actual_hash: str = None, affected_fields: Dict = None,
                              change_description: str = None, created_by: str = None) -> str:
        """Create integrity monitoring event"""
        query = """
            INSERT INTO data_integrity_events (
                event_type, severity, file_id, record_id, baseline_id,
                expected_hash, actual_hash, affected_fields, 
                change_description, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (event_type, severity, file_id, record_id, baseline_id,
                 expected_hash, actual_hash,
                 json.dumps(affected_fields) if affected_fields else None,
                 change_description, created_by)
        return self.execute_insert(query, params)
    
    def get_integrity_events(self, severity: str = None, status: str = None,
                           limit: int = 100) -> List[Dict]:
        """Get integrity monitoring events"""
        query = """
            SELECT ie.*, f.filename, u.username as created_by_username
            FROM data_integrity_events ie
            LEFT JOIN data_files f ON ie.file_id = f.id
            LEFT JOIN data_users u ON ie.created_by = u.id
            WHERE (%s IS NULL OR ie.severity = %s)
            AND (%s IS NULL OR ie.status = %s)
            ORDER BY ie.created_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (severity, severity, status, status, limit))
    
    def get_integrity_statistics(self) -> Dict:
        """Get integrity monitoring statistics"""
        query = """
            SELECT 
                COUNT(*) as total_events,
                COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_events,
                COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_events,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open_events,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as recent_events_24h
            FROM data_integrity_events
        """
        results = self.execute_query(query)
        return results[0] if results else {}
    
    # ============================================================================
    # COMPLIANCE OPERATIONS
    # ============================================================================
    
    def create_compliance_violation(self, file_id: str, violation_type: str,
                                   violation_category: str, severity: str,
                                   description: str, affected_columns: List[str] = None,
                                   affected_records_count: int = None,
                                   data_classification: str = None,
                                   record_id: str = None, created_by: str = None) -> str:
        """Create compliance violation"""
        query = """
            INSERT INTO data_compliance_violations (
                file_id, record_id, violation_type, violation_category,
                severity, description, affected_columns, affected_records_count,
                data_classification, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (file_id, record_id, violation_type, violation_category,
                 severity, description, affected_columns, affected_records_count,
                 data_classification, created_by)
        return self.execute_insert(query, params)
    
    def get_compliance_violations(self, file_id: str = None, 
                                 severity: str = None, 
                                 status: str = None) -> List[Dict]:
        """Get compliance violations"""
        query = """
            SELECT cv.*, f.filename, u.username as created_by_username
            FROM data_compliance_violations cv
            LEFT JOIN data_files f ON cv.file_id = f.id
            LEFT JOIN data_users u ON cv.created_by = u.id
            WHERE (%s IS NULL OR cv.file_id = %s)
            AND (%s IS NULL OR cv.severity = %s)
            AND (%s IS NULL OR cv.status = %s)
            ORDER BY cv.created_at DESC
        """
        return self.execute_query(query, (file_id, file_id, severity, severity, status, status))
    
    # ============================================================================
    # AUDIT OPERATIONS
    # ============================================================================
    
    def log_audit_event(self, action_type: str, resource_type: str = None,
                       resource_id: str = None, user_id: str = None,
                       ip_address: str = None, user_agent: str = None,
                       details: Dict = None) -> str:
        """Log system audit event"""
        query = """
            INSERT INTO system_audit_log (
                action_type, resource_type, resource_id, user_id,
                ip_address, user_agent, details
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (action_type, resource_type, resource_id, user_id,
                 ip_address, user_agent, json.dumps(details) if details else None)
        return self.execute_insert(query, params)
    
    def get_audit_log(self, user_id: str = None, action_type: str = None,
                     hours_back: int = 24, limit: int = 100) -> List[Dict]:
        """Get audit log entries"""
        query = """
            SELECT sal.*, u.username
            FROM system_audit_log sal
            LEFT JOIN data_users u ON sal.user_id = u.id
            WHERE (%s IS NULL OR sal.user_id = %s)
            AND (%s IS NULL OR sal.action_type = %s)
            AND sal.created_at >= NOW() - INTERVAL '%s hours'
            ORDER BY sal.created_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (user_id, user_id, action_type, action_type, hours_back, limit))
    
    # ============================================================================
    # UTILITY OPERATIONS
    # ============================================================================
    
    def get_system_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        queries = {
            'total_users': "SELECT COUNT(*) as count FROM data_users WHERE is_active = TRUE",
            'total_files': "SELECT COUNT(*) as count FROM data_files",
            'total_records': "SELECT COUNT(*) as count FROM data_records",
            'active_jobs': "SELECT COUNT(*) as count FROM data_processing_jobs WHERE status IN ('pending', 'running')",
            'open_violations': "SELECT COUNT(*) as count FROM data_compliance_violations WHERE status = 'open'",
            'recent_logins': "SELECT COUNT(*) as count FROM data_users WHERE last_login >= NOW() - INTERVAL '24 hours'"
        }
        
        stats = {}
        for key, query in queries.items():
            result = self.execute_query(query)
            stats[key] = result[0]['count'] if result else 0
        
        return stats
    
    def check_user_permission(self, user_id: str, resource_type: str, action: str) -> bool:
        """Check if user has specific permission"""
        query = """
            SELECT COUNT(*) as count
            FROM user_permissions
            WHERE user_id = %s 
            AND resource_type = %s 
            AND action IN (%s, 'admin')
        """
        result = self.execute_query(query, (user_id, resource_type, action))
        return result[0]['count'] > 0 if result else False
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("PostgreSQL connection closed")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_database_if_not_exists(host: str, port: int, database: str, 
                                 username: str, password: str):
    """Create database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(
            host=host, port=port, user=username, password=password,
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("""
            SELECT 1 FROM pg_database WHERE datname = %s
        """, (database,))
        
        if not cursor.fetchone():
            # Create database
            cursor.execute(f'CREATE DATABASE "{database}"')
            logger.info(f"Created database: {database}")
        else:
            logger.info(f"Database {database} already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

def run_schema_migration(connector: PostgreSQLConnector, schema_file: str):
    """Run schema migration from SQL file"""
    try:
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        with connector.get_cursor() as cursor:
            cursor.execute(schema_sql)
        
        logger.info(f"Schema migration completed successfully")
        
    except Exception as e:
        logger.error(f"Schema migration failed: {e}")
        raise 