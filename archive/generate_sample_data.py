#!/usr/bin/env python3
"""
Sample Data Generator
Creates realistic sample data for testing data processing pipelines

Usage:
    python generate_sample_data.py --type healthcare --rows 1000 --output data/my_healthcare_data.csv
    python generate_sample_data.py --type financial --rows 500 --violations 0.3
    
Or use as a module:
    from generate_sample_data import DataGenerator
    generator = DataGenerator()
    df = generator.generate_healthcare_data(1000, violation_rate=0.2)
"""

import pandas as pd
import numpy as np
import random
import uuid
from datetime import datetime, timedelta
import argparse
import os
from typing import Dict, List, Optional
from faker import Faker

# Initialize Faker for realistic fake data
fake = Faker()

class DataGenerator:
    """Generates realistic sample data for different domains"""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)
        
        # Common violation patterns
        self.violation_patterns = {
            'phi_exposure': ['ssn', 'phone', 'email'],
            'missing_consent': ['consent_given'],
            'data_breach': ['unauthorized_access'],
            'retention_violation': ['data_retention_exceeded']
        }
    
    def generate_healthcare_data(self, num_rows: int, violation_rate: float = 0.2) -> pd.DataFrame:
        """
        Generate healthcare data with HIPAA compliance considerations
        
        Args:
            num_rows: Number of records to generate
            violation_rate: Percentage of records with violations (0.0 to 1.0)
            
        Returns:
            DataFrame with healthcare data
        """
        print(f"🏥 Generating {num_rows} healthcare records with {violation_rate*100}% violations...")
        
        data = []
        violation_count = int(num_rows * violation_rate)
        
        # Medical conditions and their frequencies
        diagnoses = ['diabetes', 'hypertension', 'asthma', 'flu', 'covid-19', 'heart_disease', 'cancer', 'arthritis']
        treatments = ['medication', 'surgery', 'therapy', 'monitoring', 'consultation']
        
        for i in range(num_rows):
            # Determine if this record should have violations
            has_violation = i < violation_count
            
            # Generate base record in the exact order expected by healthcare_v1 schema:
            # ['id', 'patient_name', 'ssn', 'phone', 'email', 'diagnosis', 'treatment_date', 
            #  'has_violation', 'violation_type', 'timestamp', 'medical_record_number', 'doctor_name', 'insurance_id']
            
            record = {
                'id': str(uuid.uuid4()),
                'patient_name': fake.name(),
                # ssn, phone, email will be set below based on violation status
                'diagnosis': np.random.choice(diagnoses),
                'treatment_date': fake.date_between(start_date='-2y', end_date='today'),
                # has_violation, violation_type will be set below
                'timestamp': datetime.now() - timedelta(days=random.randint(0, 365)),
                'medical_record_number': f"MRN{fake.random_number(digits=8)}",
                'doctor_name': f"Dr. {fake.name()}",
                'insurance_id': f"INS{fake.random_number(digits=10)}"
            }
            
            # Add sensitive fields with or without violations
            if has_violation:
                # PHI exposure violations - real data instead of masked
                record.update({
                    'ssn': fake.ssn(),
                    'phone': fake.phone_number(),
                    'email': fake.email(),
                    'has_violation': True,
                    'violation_type': 'phi_exposure'
                })
            else:
                # Compliant - masked sensitive data
                record.update({
                    'ssn': f"***-**-{str(random.randint(1000, 9999))}",
                    'phone': "***-***-****",
                    'email': "***@***.com",
                    'has_violation': False,
                    'violation_type': ""
                })
            
            data.append(record)
        
        # Create DataFrame with exact column order expected by schema
        column_order = [
            'id', 'patient_name', 'ssn', 'phone', 'email', 'diagnosis', 'treatment_date',
            'has_violation', 'violation_type', 'timestamp', 'medical_record_number', 'doctor_name', 'insurance_id'
        ]
        
        df = pd.DataFrame(data)[column_order]  # Reorder columns to match schema
        print(f"✅ Generated {len(df)} healthcare records ({violation_count} with violations)")
        return df
    
    def generate_financial_data(self, num_rows: int, violation_rate: float = 0.15) -> pd.DataFrame:
        """
        Generate financial data with GDPR compliance considerations
        
        Args:
            num_rows: Number of records to generate
            violation_rate: Percentage of records with violations
            
        Returns:
            DataFrame with financial data
        """
        print(f"💰 Generating {num_rows} financial records with {violation_rate*100}% violations...")
        
        data = []
        violation_count = int(num_rows * violation_rate)
        
        transaction_types = ['deposit', 'withdrawal', 'transfer', 'payment', 'investment']
        account_types = ['checking', 'savings', 'credit', 'investment', 'loan']
        
        for i in range(num_rows):
            has_violation = i < violation_count
            
            record = {
                'id': str(uuid.uuid4()),
                'customer_name': fake.name(),
                'account_number': f"ACC{fake.random_number(digits=10)}",
                'account_type': np.random.choice(account_types),
                'transaction_id': f"TXN{fake.random_number(digits=12)}",
                'transaction_type': np.random.choice(transaction_types),
                'transaction_amount': round(random.uniform(10.0, 50000.0), 2),
                'transaction_date': fake.date_between(start_date='-1y', end_date='today'),
                'merchant': fake.company(),
                'credit_score': random.randint(300, 850),
                'timestamp': datetime.now() - timedelta(days=random.randint(0, 365))
            }
            
            # Handle consent and sensitive data
            if has_violation:
                # Missing consent or exposed PII
                violation_types = ['missing_consent', 'pii_exposure', 'unauthorized_processing']
                violation_type = np.random.choice(violation_types)
                
                record.update({
                    'consent_given': False if violation_type == 'missing_consent' else True,
                    'phone': fake.phone_number(),  # Exposed
                    'email': fake.email(),  # Exposed
                    'has_violation': True,
                    'violation_type': violation_type
                })
            else:
                record.update({
                    'consent_given': True,
                    'phone': "***-***-****",  # Masked
                    'email': "***@***.com",   # Masked
                    'has_violation': False,
                    'violation_type': ""
                })
            
            data.append(record)
        
        df = pd.DataFrame(data)
        print(f"✅ Generated {len(df)} financial records ({violation_count} with violations)")
        return df
    
    def generate_ecommerce_data(self, num_rows: int, violation_rate: float = 0.1) -> pd.DataFrame:
        """Generate e-commerce data with privacy considerations"""
        print(f"🛒 Generating {num_rows} e-commerce records with {violation_rate*100}% violations...")
        
        data = []
        violation_count = int(num_rows * violation_rate)
        
        categories = ['electronics', 'clothing', 'books', 'home', 'sports', 'beauty']
        payment_methods = ['credit_card', 'debit_card', 'paypal', 'apple_pay', 'bank_transfer']
        
        for i in range(num_rows):
            has_violation = i < violation_count
            
            record = {
                'id': str(uuid.uuid4()),
                'customer_name': fake.name(),
                'order_id': f"ORD{fake.random_number(digits=8)}",
                'product_name': fake.catch_phrase(),
                'category': np.random.choice(categories),
                'price': round(random.uniform(5.0, 1000.0), 2),
                'quantity': random.randint(1, 5),
                'payment_method': np.random.choice(payment_methods),
                'order_date': fake.date_between(start_date='-6m', end_date='today'),
                'shipping_address': fake.address(),
                'timestamp': datetime.now() - timedelta(days=random.randint(0, 180))
            }
            
            if has_violation:
                # Credit card exposure or missing privacy consent
                record.update({
                    'credit_card': fake.credit_card_number(),  # Should be masked
                    'phone': fake.phone_number(),
                    'email': fake.email(),
                    'privacy_consent': False,
                    'has_violation': True,
                    'violation_type': 'payment_data_exposure'
                })
            else:
                record.update({
                    'credit_card': f"****-****-****-{fake.random_number(digits=4)}",
                    'phone': "***-***-****",
                    'email': "***@***.com",
                    'privacy_consent': True,
                    'has_violation': False,
                    'violation_type': ""
                })
            
            data.append(record)
        
        df = pd.DataFrame(data)
        print(f"✅ Generated {len(df)} e-commerce records ({violation_count} with violations)")
        return df
    
    def generate_iot_data(self, num_rows: int, violation_rate: float = 0.05) -> pd.DataFrame:
        """Generate IoT sensor data with privacy considerations"""
        print(f"📡 Generating {num_rows} IoT records with {violation_rate*100}% violations...")
        
        data = []
        violation_count = int(num_rows * violation_rate)
        
        sensor_types = ['temperature', 'humidity', 'motion', 'light', 'sound', 'air_quality']
        device_types = ['smart_home', 'wearable', 'industrial', 'automotive', 'medical']
        
        for i in range(num_rows):
            has_violation = i < violation_count
            
            record = {
                'id': str(uuid.uuid4()),
                'device_id': f"DEV{fake.random_number(digits=8)}",
                'sensor_type': np.random.choice(sensor_types),
                'device_type': np.random.choice(device_types),
                'reading_value': round(random.uniform(0.0, 100.0), 3),
                'unit': 'celsius' if record.get('sensor_type') == 'temperature' else 'percent',
                'location': fake.city(),
                'reading_time': fake.date_time_between(start_date='-1m', end_date='now'),
                'battery_level': random.randint(1, 100),
                'firmware_version': f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
                'timestamp': datetime.now() - timedelta(hours=random.randint(0, 720))
            }
            
            if has_violation:
                # Location tracking without consent or device identification
                record.update({
                    'gps_coordinates': f"{fake.latitude()}, {fake.longitude()}",
                    'user_id': fake.uuid4(),  # Should be anonymized
                    'consent_for_tracking': False,
                    'has_violation': True,
                    'violation_type': 'location_tracking_without_consent'
                })
            else:
                record.update({
                    'gps_coordinates': "***,***",  # Anonymized
                    'user_id': "anonymous",
                    'consent_for_tracking': True,
                    'has_violation': False,
                    'violation_type': ""
                })
            
            data.append(record)
        
        df = pd.DataFrame(data)
        print(f"✅ Generated {len(df)} IoT records ({violation_count} with violations)")
        return df
    
    def generate_custom_data(self, num_rows: int, schema: Dict, violation_rate: float = 0.1) -> pd.DataFrame:
        """
        Generate custom data based on provided schema
        
        Args:
            num_rows: Number of records to generate
            schema: Dictionary defining field names and types
            violation_rate: Percentage of records with violations
            
        Returns:
            DataFrame with custom data
        """
        print(f"🔧 Generating {num_rows} custom records...")
        # Implementation for custom schemas
        # This would need to be extended based on specific requirements
        pass

def save_to_csv(df: pd.DataFrame, output_path: str, include_timestamp: bool = True):
    """Save DataFrame to CSV with optional timestamp in filename"""
    
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(output_path)
        output_path = f"{name}_{timestamp}{ext}"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"💾 Saved {len(df)} records to: {output_path}")
    return output_path

def main():
    """Command line interface for the data generator"""
    parser = argparse.ArgumentParser(description="Generate sample data for testing")
    parser.add_argument('--type', '-t', required=True, 
                       choices=['healthcare', 'financial', 'ecommerce', 'iot'],
                       help='Type of data to generate')
    parser.add_argument('--rows', '-r', type=int, required=True,
                       help='Number of rows to generate')
    parser.add_argument('--violations', '-v', type=float, default=0.2,
                       help='Violation rate (0.0 to 1.0, default: 0.2)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file path (default: data/sample_{type}_{timestamp}.csv)')
    parser.add_argument('--seed', '-s', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = DataGenerator(seed=args.seed)
    
    # Generate data based on type
    if args.type == 'healthcare':
        df = generator.generate_healthcare_data(args.rows, args.violations)
    elif args.type == 'financial':
        df = generator.generate_financial_data(args.rows, args.violations)
    elif args.type == 'ecommerce':
        df = generator.generate_ecommerce_data(args.rows, args.violations)
    elif args.type == 'iot':
        df = generator.generate_iot_data(args.rows, args.violations)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = f"data/sample_{args.type}.csv"
    
    # Save to file
    final_path = save_to_csv(df, output_path)
    
    print(f"\n📊 Summary:")
    print(f"   Data Type: {args.type}")
    print(f"   Records: {len(df)}")
    print(f"   Violations: {df['has_violation'].sum() if 'has_violation' in df.columns else 0}")
    print(f"   File: {final_path}")

if __name__ == "__main__":
    main() 