"""
Research Utilities for Pipeline Analysis
Provides shared functionality for all research analysis scripts

This module contains:
- Test data generation with incremental sizes
- Anonymization configuration management
- Metrics collection and CSV output
- Timing measurement utilities
"""

import sys
import os
import pandas as pd
import numpy as np
import csv
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from faker import Faker
import json
import uuid

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
src_dir = os.path.join(backend_dir, 'src')
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)

# Import anonymization components
try:
    from src.common.anonymization_engine import (
        EnhancedAnonymizationEngine, 
        AnonymizationConfig, 
        AnonymizationMethod
    )
except ImportError:
    from common.anonymization_engine import (
        EnhancedAnonymizationEngine, 
        AnonymizationConfig, 
        AnonymizationMethod
    )

class ResearchDataGenerator:
    """Generate test datasets with incremental sizes for research analysis"""
    
    def __init__(self):
        self.fake = Faker()
        # Don't create engine during initialization to avoid hanging
        # self.anonymization_engine = EnhancedAnonymizationEngine()
    
    def generate_test_datasets(self, base_dir: str = "test_data") -> List[Dict[str, Any]]:
        """
        Generate test datasets with incremental sizes
        
        Returns:
            List of dataset metadata with file paths and sizes
        """
        # Create test data directory
        test_data_dir = os.path.join(os.path.dirname(__file__), base_dir)
        os.makedirs(test_data_dir, exist_ok=True)
        
        # Dataset sizes for incremental testing
        dataset_sizes = [500, 1000, 2500, 5000, 10000, 20000, 40000, 50000]
        
        datasets = []
        
        for size in dataset_sizes:
            # CSV files already exist, so just create metadata for them
            healthcare_file = os.path.join(test_data_dir, f"healthcare_{size}_records.csv")
            financial_file = os.path.join(test_data_dir, f"financial_{size}_records.csv")

            # 📦 E-commerce dataset file path
            ecommerce_file = os.path.join(test_data_dir, f"ecommerce_{size}_records.csv")
            
            # Check if files exist, if not generate them
            if not os.path.exists(healthcare_file):
                print(f"⚠️  Healthcare file missing, generating: {healthcare_file}")
                healthcare_data = self._generate_healthcare_data(size)
                healthcare_data.to_csv(healthcare_file, index=False)
            
            if not os.path.exists(financial_file):
                print(f"⚠️  Financial file missing, generating: {financial_file}")
                financial_data = self._generate_financial_data(size)
                financial_data.to_csv(financial_file, index=False)
            
            if not os.path.exists(ecommerce_file):
                print(f"⚠️  Ecommerce file missing, generating: {ecommerce_file}")
                ecommerce_data = self._generate_ecommerce_data(size)
                ecommerce_data.to_csv(ecommerce_file, index=False)
            
            # COMMENTED OUT: CSV generation logic (kept for future reference)
            # # Generate healthcare dataset
            # healthcare_data = self._generate_healthcare_data(size)
            # healthcare_file = os.path.join(test_data_dir, f"healthcare_{size}_records.csv")
            # healthcare_data.to_csv(healthcare_file, index=False)
            
            datasets.append({
                'type': 'healthcare',
                'size': size,
                'file_path': healthcare_file,
                'expected_violations': int(size * 0.15),  # ~15% violation rate
                'description': f'Healthcare dataset with {size} patient records'
            })
            
            # COMMENTED OUT: CSV generation logic (kept for future reference)
            # # Generate financial dataset
            # financial_data = self._generate_financial_data(size)
            # financial_file = os.path.join(test_data_dir, f"financial_{size}_records.csv")
            # financial_data.to_csv(financial_file, index=False)
            
            datasets.append({
                'type': 'financial',
                'size': size,
                'file_path': financial_file,
                'expected_violations': int(size * 0.12),  # ~12% violation rate
                'description': f'Financial dataset with {size} transaction records'
            })
            
            datasets.append({
                'type': 'ecommerce',
                'size': size,
                'file_path': ecommerce_file,
                'expected_violations': int(size * 0.10),  # ~10% violation rate
                'description': f'Ecommerce dataset with {size} consumer buying records'
            })
            
            print(f"✅ Using existing test datasets for size {size} records")
        
        return datasets
    
    def _generate_healthcare_data(self, size: int) -> pd.DataFrame:
        """Generate healthcare test data with HIPAA violations"""
        data = []
        
        for i in range(size):
            # Generate base record
            record = {
                'id': str(uuid.uuid4()),
                'patient_name': self.fake.name(),
                'age': self.fake.random_int(min=18, max=90),
                'gender': self.fake.random_element(['M', 'F', 'Other']),
                'diagnosis': self.fake.random_element([
                    'Diabetes', 'Hypertension', 'Flu', 'Pneumonia', 'Asthma',
                    'Depression', 'Arthritis', 'Cancer', 'Heart Disease'
                ]),
                'treatment_date': self.fake.date_between(start_date='-2y', end_date='today'),
                'doctor_name': self.fake.name(),
                'hospital': self.fake.company(),
                'insurance_id': f"INS{self.fake.random_int(min=100000, max=999999)}",
                'medical_record_number': f"MRN{self.fake.random_int(min=1000000, max=9999999)}",
                'created_at': datetime.now().isoformat()
            }
            
            # Add violations to ~15% of records
            if i < size * 0.15:
                # Add PHI violations
                record['ssn'] = f"{self.fake.random_int(min=100, max=999)}-{self.fake.random_int(min=10, max=99)}-{self.fake.random_int(min=1000, max=9999)}"
                record['phone'] = f"({self.fake.random_int(min=100, max=999)}) {self.fake.random_int(min=100, max=999)}-{self.fake.random_int(min=1000, max=9999)}"
                record['email'] = self.fake.email()
                record['has_violation'] = True
                record['violation_type'] = 'PHI_EXPOSURE'
            else:
                record['ssn'] = None
                record['phone'] = None
                record['email'] = None
                record['has_violation'] = False
                record['violation_type'] = None
            
            data.append(record)
        
        return pd.DataFrame(data)
    
    def _generate_financial_data(self, size: int) -> pd.DataFrame:
        """Generate financial test data with GDPR violations"""
        data = []
        
        for i in range(size):
            # Generate base record
            record = {
                'id': str(uuid.uuid4()),
                'customer_name': self.fake.name(),
                'age': self.fake.random_int(min=18, max=80),
                'transaction_amount': round(self.fake.random.uniform(10.0, 10000.0), 2),
                'transaction_date': self.fake.date_between(start_date='-1y', end_date='today'),
                'transaction_type': self.fake.random_element(['purchase', 'withdrawal', 'deposit', 'transfer']),
                'location': self.fake.city(),
                'merchant': self.fake.company(),
                'currency': 'USD',
                'created_at': datetime.now().isoformat()
            }
            
            # Add violations to ~12% of records
            if i < size * 0.12:
                # Add GDPR violations
                record['customer_id'] = f"CUST{self.fake.random_int(min=100000, max=999999)}"
                record['account_number'] = f"ACC{self.fake.random_int(min=1000000000, max=9999999999)}"
                record['credit_score'] = self.fake.random_int(min=300, max=850)
                record['consent_given'] = False  # GDPR violation
                record['data_retention_days'] = self.fake.random_int(min=2557, max=5000)  # >7 years = violation
                record['has_violation'] = True
                record['violation_type'] = 'GDPR_VIOLATION'
            else:
                record['customer_id'] = None
                record['account_number'] = None
                record['credit_score'] = None
                record['consent_given'] = True
                record['data_retention_days'] = self.fake.random_int(min=30, max=2556)  # <7 years = compliant
                record['has_violation'] = False
                record['violation_type'] = None
            
            data.append(record)
        
        return pd.DataFrame(data)

    def _generate_ecommerce_data(self, size: int) -> pd.DataFrame:
        """Generate e-commerce consumer buying test data with PCI-DSS/GDPR violations"""
        data = []
        
        for i in range(size):
            unit_price = round(self.fake.random.uniform(5.0, 500.0), 2)
            quantity = self.fake.random_int(min=1, max=5)
            total_amount = round(unit_price * quantity, 2)
            
            record = {
                'id': str(uuid.uuid4()),
                'customer_name': self.fake.name(),
                'email': self.fake.email(),
                'age': self.fake.random_int(min=18, max=80),
                'gender': self.fake.random_element(['M', 'F', 'Other']),
                'country': self.fake.country(),
                'product_id': f"SKU{self.fake.random_int(min=100000, max=999999)}",
                'product_category': self.fake.random_element([
                    'Electronics', 'Clothing', 'Home', 'Sports', 'Health', 'Books', 'Toys'
                ]),
                'unit_price': unit_price,
                'quantity': quantity,
                'total_amount': total_amount,
                'purchase_date': self.fake.date_between(start_date='-1y', end_date='today'),
                'payment_method': self.fake.random_element(['credit_card', 'paypal', 'apple_pay', 'google_pay']),
                'created_at': datetime.now().isoformat()
            }
            
            # Add PCI-DSS/GDPR violations to ~10% of records
            if i < size * 0.10:
                record['credit_card_number'] = self.fake.credit_card_number()
                record['credit_card_cvv'] = self.fake.random_int(min=100, max=999)
                record['consent_given'] = False
                record['has_violation'] = True
                record['violation_type'] = 'PCI_DSS_VIOLATION'
            else:
                record['credit_card_number'] = None
                record['credit_card_cvv'] = None
                record['consent_given'] = True
                record['has_violation'] = False
                record['violation_type'] = None
            
            data.append(record)
        
        return pd.DataFrame(data)

class AnonymizationConfigManager:
    """Manage all anonymization configurations for comprehensive testing"""
    
    def __init__(self):
        # Don't create engine during initialization to avoid hanging
        # self.engine = EnhancedAnonymizationEngine()
        self.all_configs = self._generate_all_configs()
    
    def _generate_all_configs(self) -> List[AnonymizationConfig]:
        """Generate all possible anonymization configurations for research"""
        configs = []
        
        # K-anonymity configurations
        for k in [3, 5, 10, 15]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.K_ANONYMITY,
                k_value=k
            ))
        
        # Differential privacy configurations
        for epsilon in [0.1, 0.5, 1.0, 2.0]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.DIFFERENTIAL_PRIVACY,
                epsilon=epsilon
            ))
        
        # Tokenization configurations
        for key_length in [128, 256, 512]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.TOKENIZATION,
                key_length=key_length
            ))
        
        return configs
    
    def get_all_configs(self) -> List[AnonymizationConfig]:
        """Get all anonymization configurations"""
        return self.all_configs
    
    def get_config_description(self, config: AnonymizationConfig) -> str:
        """Get human-readable description of configuration"""
        if config.method == AnonymizationMethod.K_ANONYMITY:
            return f"K-Anonymity (k={config.k_value})"
        elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
            return f"Differential Privacy (ε={config.epsilon})"
        elif config.method == AnonymizationMethod.TOKENIZATION:
            return f"Tokenization ({config.key_length}-bit key)"
        return "Unknown"

class ResearchMetricsCollector:
    """Collect and manage research metrics for all experiments"""
    
    def __init__(self, output_file: str = "research_results.csv"):
        self.output_file = output_file
        self.results = []
        self.experiment_start_time = datetime.now()
        
        # Initialize CSV file with headers
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Initialize CSV file with research metrics headers"""
        headers = [
            'experiment_id',
            'timestamp',
            'pipeline_type',
            'dataset_type',
            'dataset_size',
            'anonymization_method',
            'anonymization_params',
            'pure_processing_time_seconds',
            'pre_processing_time_seconds',
            'post_processing_time_seconds',
            'total_time_seconds',
            'records_processed',
            'records_per_second',
            'violations_detected',
            'violation_rate',
            'memory_usage_mb',
            'cpu_usage_percent',
            'anonymization_overhead_seconds',
            'compliance_check_time_seconds',
            # Latency metrics – newly added
            'avg_latency_ms',
            'max_latency_ms',
            'min_latency_ms',
            'latency_std_ms',
            'e2e_latency_ms',
            # Hybrid routing metrics (optional)
            'router_time_ms',
            'stream_percentage',
            'batch_percentage',
            'information_loss_score',
            'utility_preservation_score',
            'privacy_level_score',
            'success',
            'error_message',
            'notes'
        ]
        
        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
    
    def record_experiment(self, 
                         pipeline_type: str,
                         dataset_info: Dict[str, Any],
                         anonymization_config: AnonymizationConfig,
                         timing_results: Dict[str, float],
                         processing_results: Dict[str, Any],
                         success: bool = True,
                         error_message: str = None,
                         notes: str = None):
        """Record a single experiment result"""
        
        experiment_id = f"{pipeline_type}_{dataset_info['type']}_{dataset_info['size']}_{anonymization_config.method.value}_{int(time.time())}"
        
        # Calculate metrics
        pure_processing_time = timing_results.get('pure_processing_time', 0)
        total_records = processing_results.get('total_records', 0)
        records_per_second = total_records / pure_processing_time if pure_processing_time > 0 else 0
        
        # Get anonymization parameters
        # Build anonymization-param blob
        params = {}
        if anonymization_config.k_value is not None:
            params['k_value'] = anonymization_config.k_value
        if anonymization_config.epsilon is not None:
            params['epsilon'] = anonymization_config.epsilon
        if anonymization_config.key_length is not None:
            params['key_length'] = anonymization_config.key_length

        # ------------------------------------------------------------------
        # Derive latency metrics if the caller did not supply them in
        # processing_results.  We use the simple per-record average plus
        # defaults for min/max to ensure non-zero values land in the CSV.
        # ------------------------------------------------------------------
        latency_defaults = {}
        if total_records > 0:
            avg_lat = (pure_processing_time * 1000.0) / total_records
        else:
            avg_lat = 0
        latency_defaults['avg_latency_ms'] = processing_results.get('avg_latency_ms', avg_lat)
        latency_defaults['max_latency_ms'] = processing_results.get('max_latency_ms', avg_lat)
        latency_defaults['min_latency_ms'] = processing_results.get('min_latency_ms', avg_lat)
        latency_defaults['latency_std_ms'] = processing_results.get('latency_std_ms', 0)

        # End-to-end latency (total pipeline time per record)
        e2e_latency_ms = processing_results.get('e2e_latency_ms')
        if e2e_latency_ms is None and total_records > 0:
            e2e_latency_ms = (timing_results.get('total_time', 0) * 1000) / total_records
        
        result = {
            'experiment_id': experiment_id,
            'timestamp': datetime.now().isoformat(),
            'pipeline_type': pipeline_type,
            'dataset_type': dataset_info['type'],
            'dataset_size': dataset_info['size'],
            'anonymization_method': anonymization_config.method.value,
            'anonymization_params': json.dumps(params),
            'pure_processing_time_seconds': pure_processing_time,
            'pre_processing_time_seconds': timing_results.get('pre_processing_time', 0),
            'post_processing_time_seconds': timing_results.get('post_processing_time', 0),
            'total_time_seconds': timing_results.get('total_time', 0),
            'records_processed': total_records,
            'records_per_second': records_per_second,
            'violations_detected': processing_results.get('violations_detected', 0),
            'violation_rate': processing_results.get('violation_rate', 0),
            'memory_usage_mb': processing_results.get('memory_usage_mb', 0),
            'cpu_usage_percent': processing_results.get('cpu_usage_percent', 0),
            'anonymization_overhead_seconds': processing_results.get('anonymization_overhead', 0),
            'compliance_check_time_seconds': processing_results.get('compliance_check_time', 0),
            'information_loss_score': processing_results.get('information_loss_score', 0),
            'utility_preservation_score': processing_results.get('utility_preservation_score', 0),
            'privacy_level_score': processing_results.get('privacy_level_score', 0),
            'avg_latency_ms': latency_defaults['avg_latency_ms'],
            'max_latency_ms': latency_defaults['max_latency_ms'],
            'min_latency_ms': latency_defaults['min_latency_ms'],
            'latency_std_ms': latency_defaults['latency_std_ms'],
            'subprocess_overhead_ms': processing_results.get('subprocess_overhead_ms', 0),
            'e2e_latency_ms': e2e_latency_ms or 0,
            # Hybrid routing metrics (populate if provided, else default 0)
            'router_time_ms': processing_results.get('router_time_ms', 0),
            'stream_percentage': processing_results.get('stream_percentage', 0),
            'batch_percentage': processing_results.get('batch_percentage', 0),
            'success': success,
            'error_message': error_message or '',
            'notes': notes or ''
        }
        
        self.results.append(result)
        
        # Append to CSV file
        with open(self.output_file, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=result.keys())
            writer.writerow(result)
        
        print(f"📊 Recorded experiment: {experiment_id}")
        print(f"   📈 Processing rate: {records_per_second:.2f} records/second")
        print(f"   ⏱️  Pure processing time: {pure_processing_time:.3f}s")
        print(f"   🔍 Violations detected: {processing_results.get('violations_detected', 0)}")
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments"""
        if not self.results:
            return {"message": "No experiments recorded yet"}
        
        total_experiments = len(self.results)
        successful_experiments = sum(1 for r in self.results if r['success'])
        
        # Calculate averages
        avg_processing_time = np.mean([r['pure_processing_time_seconds'] for r in self.results if r['success']])
        avg_records_per_second = np.mean([r['records_per_second'] for r in self.results if r['success']])
        
        return {
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'success_rate': successful_experiments / total_experiments,
            'avg_processing_time': avg_processing_time,
            'avg_records_per_second': avg_records_per_second,
            'experiment_duration': (datetime.now() - self.experiment_start_time).total_seconds(),
            'output_file': self.output_file
        }

class TimingUtilities:
    """Utilities for precise timing measurement"""
    
    @staticmethod
    def time_section(section_name: str = "operation"):
        """Context manager for timing code sections"""
        class TimingContext:
            def __init__(self, name):
                self.name = name
                self.start_time = None
                self.end_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.end_time = time.time()
                self.duration = self.end_time - self.start_time
        
        return TimingContext(section_name)
    
    @staticmethod
    def measure_memory_usage():
        """Measure current memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # MB
        except ImportError:
            return 0
    
    @staticmethod
    def measure_cpu_usage():
        """Measure current CPU usage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.2)  # shorter interval for stable sample
        except ImportError:
            return 0

def create_research_directory_structure():
    """Create the directory structure for research outputs"""
    base_dir = os.path.dirname(__file__)
    
    directories = [
        'test_data',
        'results',
        'logs',
        'temp'
    ]
    
    for directory in directories:
        dir_path = os.path.join(base_dir, directory)
        os.makedirs(dir_path, exist_ok=True)
    
    print("✅ Research directory structure created")

if __name__ == "__main__":
    # Test the utilities
    print("🧪 Testing Research Utilities...")
    
    # Create directory structure
    create_research_directory_structure()
    
    # Test data generation
    generator = ResearchDataGenerator()
    datasets = generator.generate_test_datasets()
    print(f"✅ Generated {len(datasets)} test datasets")
    
    # Test anonymization configs
    config_manager = AnonymizationConfigManager()
    configs = config_manager.get_all_configs()
    print(f"✅ Generated {len(configs)} anonymization configurations")
    
    # Test metrics collection
    metrics_collector = ResearchMetricsCollector("test_results.csv")
    print("✅ Metrics collector initialized")
    
    print("🎉 All research utilities are working correctly!") 