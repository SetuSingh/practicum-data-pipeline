#!/usr/bin/env python3
"""
Data Integrity Monitoring System
Implements hashing, change detection, and metadata monitoring for secure data pipeline

This module addresses the requirement:
"Set up hashing (e.g., MD5 or SHA256) to compute and store hashes for each data record.
At each ingestion, compare new hashes to existing ones to detect unauthorized changes."
"""

import hashlib
import json
import pandas as pd
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
from dataclasses import dataclass

@dataclass
class DataChangeEvent:
    """Represents a detected data change"""
    timestamp: str
    change_type: str  # 'record_modified', 'record_added', 'record_deleted', 'schema_changed'
    record_id: str
    old_hash: Optional[str]
    new_hash: Optional[str]
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'

class DataIntegrityMonitor:
    """
    Data Integrity Monitoring System
    
    This class implements the three types of data change monitoring:
    1. Source Data Integrity - detects tampering with source files
    2. Processed Data Integrity - detects unauthorized changes to processed data
    3. Schema/Metadata Changes - detects structural changes
    """
    
    def __init__(self, db_path="data/integrity_monitor.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database to store hashes and metadata"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table to store record hashes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS record_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                row_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(record_id, file_path)
            )
        ''')
        
        # Table to store file metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL,
                columns TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                last_modified TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table to store change events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                change_type TEXT NOT NULL,
                record_id TEXT,
                file_path TEXT NOT NULL,
                old_hash TEXT,
                new_hash TEXT,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def compute_record_hash(self, record: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash for a single data record
        
        This implements the requirement:
        "Set up hashing (e.g., MD5 or SHA256) to compute and store hashes for each data record"
        """
        # Convert record to a consistent string representation
        record_string = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(record_string.encode()).hexdigest()
    
    def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash for entire file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def baseline_file(self, file_path: str, record_id_column: str = 'id'):
        """
        Create baseline hashes for all records in a file
        
        This is the initial step - we compute hashes for all records
        and store them as our "known good" baseline.
        """
        print(f"📊 Creating baseline for {file_path}...")
        
        try:
            # Read the file
            df = pd.read_csv(file_path)
            
            # Store file metadata
            self._store_file_metadata(file_path, df)
            
            # Store individual record hashes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for index, row in df.iterrows():
                record_dict = row.to_dict()
                record_id = str(record_dict.get(record_id_column, f"row_{index}"))
                record_hash = self.compute_record_hash(record_dict)
                
                # Store or update the hash
                cursor.execute('''
                    INSERT OR REPLACE INTO record_hashes 
                    (record_id, file_path, record_hash, row_data)
                    VALUES (?, ?, ?, ?)
                ''', (record_id, file_path, record_hash, json.dumps(record_dict, default=str)))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Baseline created: {len(df)} records hashed")
            return True
            
        except Exception as e:
            print(f"❌ Error creating baseline: {e}")
            return False
    
    def detect_changes(self, file_path: str, record_id_column: str = 'id') -> List[DataChangeEvent]:
        """
        Compare current file against stored hashes to detect changes
        
        This implements:
        "At each ingestion, compare new hashes to existing ones to detect unauthorized changes"
        """
        print(f"🔍 Detecting changes in {file_path}...")
        
        changes = []
        
        try:
            # Read current file
            df = pd.read_csv(file_path)
            
            # Check for schema changes first
            schema_changes = self._detect_schema_changes(file_path, df)
            changes.extend(schema_changes)
            
            # Get stored hashes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT record_id, record_hash, row_data 
                FROM record_hashes 
                WHERE file_path = ?
            ''', (file_path,))
            
            stored_hashes = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            
            # Check each current record
            current_record_ids = set()
            
            for index, row in df.iterrows():
                record_dict = row.to_dict()
                record_id = str(record_dict.get(record_id_column, f"row_{index}"))
                current_hash = self.compute_record_hash(record_dict)
                
                current_record_ids.add(record_id)
                
                if record_id in stored_hashes:
                    stored_hash, stored_data = stored_hashes[record_id]
                    if current_hash != stored_hash:
                        # Record was modified
                        change = DataChangeEvent(
                            timestamp=datetime.now().isoformat(),
                            change_type='record_modified',
                            record_id=record_id,
                            old_hash=stored_hash,
                            new_hash=current_hash,
                            description=f"Record {record_id} was modified",
                            severity='high'
                        )
                        changes.append(change)
                        
                        # Log the change
                        self._log_change_event(change, file_path, {
                            'old_data': stored_data,
                            'new_data': json.dumps(record_dict, default=str)
                        })
                else:
                    # New record added
                    change = DataChangeEvent(
                        timestamp=datetime.now().isoformat(),
                        change_type='record_added',
                        record_id=record_id,
                        old_hash=None,
                        new_hash=current_hash,
                        description=f"New record {record_id} was added",
                        severity='medium'
                    )
                    changes.append(change)
                    self._log_change_event(change, file_path)
            
            # Check for deleted records
            for stored_id in stored_hashes:
                if stored_id not in current_record_ids:
                    change = DataChangeEvent(
                        timestamp=datetime.now().isoformat(),
                        change_type='record_deleted',
                        record_id=stored_id,
                        old_hash=stored_hashes[stored_id][0],
                        new_hash=None,
                        description=f"Record {stored_id} was deleted",
                        severity='critical'
                    )
                    changes.append(change)
                    self._log_change_event(change, file_path)
            
            conn.close()
            
            if changes:
                print(f"⚠️  Found {len(changes)} changes!")
                for change in changes:
                    print(f"   {change.severity.upper()}: {change.description}")
            else:
                print("✅ No unauthorized changes detected")
            
            return changes
            
        except Exception as e:
            print(f"❌ Error detecting changes: {e}")
            return []
    
    def _store_file_metadata(self, file_path: str, df: pd.DataFrame):
        """Store file metadata for schema monitoring"""
        file_hash = self.compute_file_hash(file_path)
        file_stats = os.stat(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_metadata
            (file_path, file_hash, row_count, column_count, columns, file_size, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_path,
            file_hash,
            len(df),
            len(df.columns),
            json.dumps(list(df.columns)),
            file_stats.st_size,
            datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _detect_schema_changes(self, file_path: str, df: pd.DataFrame) -> List[DataChangeEvent]:
        """Detect schema and metadata changes"""
        changes = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT columns, row_count, column_count 
            FROM file_metadata 
            WHERE file_path = ?
        ''', (file_path,))
        
        result = cursor.fetchone()
        if result:
            stored_columns = json.loads(result[0])
            stored_row_count = result[1]
            stored_column_count = result[2]
            
            current_columns = list(df.columns)
            
            # Check column changes
            if current_columns != stored_columns:
                change = DataChangeEvent(
                    timestamp=datetime.now().isoformat(),
                    change_type='schema_changed',
                    record_id='schema',
                    old_hash=None,
                    new_hash=None,
                    description=f"Schema changed: columns went from {stored_columns} to {current_columns}",
                    severity='critical'
                )
                changes.append(change)
                self._log_change_event(change, file_path)
            
            # Check significant row count changes (>10% difference)
            if abs(len(df) - stored_row_count) / stored_row_count > 0.1:
                change = DataChangeEvent(
                    timestamp=datetime.now().isoformat(),
                    change_type='metadata_changed',
                    record_id='row_count',
                    old_hash=None,
                    new_hash=None,
                    description=f"Significant row count change: {stored_row_count} → {len(df)}",
                    severity='high'
                )
                changes.append(change)
                self._log_change_event(change, file_path)
        
        conn.close()
        return changes
    
    def _log_change_event(self, event: DataChangeEvent, file_path: str, details: Dict = None):
        """Log change event to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO change_events
            (timestamp, change_type, record_id, file_path, old_hash, new_hash, description, severity, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp,
            event.change_type,
            event.record_id,
            file_path,
            event.old_hash,
            event.new_hash,
            event.description,
            event.severity,
            json.dumps(details) if details else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_change_history(self, file_path: str = None, limit: int = 100) -> List[Dict]:
        """Get history of all detected changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if file_path:
            cursor.execute('''
                SELECT * FROM change_events 
                WHERE file_path = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (file_path, limit))
        else:
            cursor.execute('''
                SELECT * FROM change_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_integrity_status(self) -> Dict[str, Any]:
        """Get overall integrity monitoring status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count total records monitored
        cursor.execute('SELECT COUNT(*) FROM record_hashes')
        total_records = cursor.fetchone()[0]
        
        # Count total files monitored
        cursor.execute('SELECT COUNT(*) FROM file_metadata')
        total_files = cursor.fetchone()[0]
        
        # Count recent changes (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) FROM change_events 
            WHERE datetime(timestamp) > datetime('now', '-1 day')
        ''')
        recent_changes = cursor.fetchone()[0]
        
        # Count critical changes
        cursor.execute('''
            SELECT COUNT(*) FROM change_events 
            WHERE severity = 'critical'
        ''')
        critical_changes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_records_monitored': total_records,
            'total_files_monitored': total_files,
            'recent_changes_24h': recent_changes,
            'critical_changes_total': critical_changes,
            'monitoring_active': True
        } 