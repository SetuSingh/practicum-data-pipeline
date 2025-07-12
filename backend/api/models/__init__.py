#!/usr/bin/env python3
"""
API Models Package
Contains shared data models and classes
"""

import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

def clean_data_for_json_serialization(data):
    """
    Clean data dictionary for JSON serialization, handling all problematic types
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Convert keys to strings (required for JSON)
            str_key = str(key)
            cleaned[str_key] = clean_data_for_json_serialization(value)
        return cleaned
    elif isinstance(data, list):
        return [clean_data_for_json_serialization(item) for item in data]
    elif isinstance(data, tuple):
        return [clean_data_for_json_serialization(item) for item in data]
    elif isinstance(data, set):
        return [clean_data_for_json_serialization(item) for item in data]
    elif data is None:
        return None
    elif isinstance(data, bool):
        return data
    elif isinstance(data, (int, float)):
        # Handle NaN and infinity values
        if hasattr(pd, 'isna') and pd.isna(data):
            return None
        try:
            if np.isnan(data) or np.isinf(data):
                return None
        except (TypeError, ValueError):
            pass
        return data
    elif isinstance(data, str):
        return data
    elif isinstance(data, (np.integer, np.floating)):
        # Convert numpy types to Python types
        try:
            value = data.item()
            if np.isnan(value) or np.isinf(value):
                return None
            return value
        except (TypeError, ValueError):
            return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    elif hasattr(data, '__dict__'):
        # Handle custom objects by converting to dict
        try:
            return clean_data_for_json_serialization(data.__dict__)
        except Exception:
            return str(data)
    else:
        # For any other type, try to convert to string
        try:
            # Test if it's JSON serializable
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)

class ProcessingJob:
    """Data class for tracking file processing jobs"""
    
    def __init__(self, job_id: str, filename: str, pipeline_type: str, 
                 user_id: Optional[str] = None, file_id: Optional[str] = None):
        self.job_id = job_id
        self.filename = filename
        self.pipeline_type = pipeline_type
        self.status = 'pending'
        self.progress = 0
        self.start_time = datetime.now()
        self.end_time = None
        self.results = {}
        self.error = None
        self.user_id = user_id or 'system'
        self.file_id = file_id
        self.records_processed = 0
        self.compliance_violations = []
        # Add database job ID for tracking
        self.db_job_id = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization"""
        # Clean results data to ensure JSON serializability
        cleaned_results = clean_data_for_json_serialization(self.results)
        
        return {
            'job_id': self.job_id,
            'filename': self.filename,
            'pipeline_type': self.pipeline_type,
            'status': self.status,
            'progress': self.progress,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'results': cleaned_results,
            'error': self.error,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'records_processed': self.records_processed,
            'db_job_id': self.db_job_id
        } 