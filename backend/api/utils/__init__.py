#!/usr/bin/env python3
"""
API Utilities Package
Contains shared utility functions for the API
"""

import hashlib
import json
import threading
import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from werkzeug.utils import secure_filename

def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename with timestamp"""
    filename = secure_filename(original_filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{filename}"

def detect_data_type(df: pd.DataFrame) -> str:
    """Auto-detect data type based on column names"""
    if 'patient_name' in df.columns:
        return 'healthcare'
    elif 'account_number' in df.columns:
        return 'financial'
    elif 'credit_card' in df.columns:
        return 'ecommerce'
    elif 'sensor_type' in df.columns:
        return 'iot'
    else:
        return 'healthcare'  # Default to healthcare for database compatibility

def detect_data_type_from_file(filepath: str) -> str:
    """Auto-detect data type by reading file and analyzing columns"""
    try:
        # Read just the first few rows to detect columns
        df = pd.read_csv(filepath, nrows=5)
        return detect_data_type(df)
    except Exception as e:
        print(f"Warning: Could not detect data type from file {filepath}: {e}")
        return 'healthcare'  # Default fallback

def run_async_task(target_function, *args, **kwargs):
    """Run a function asynchronously in a background thread"""
    thread = threading.Thread(target=target_function, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread 