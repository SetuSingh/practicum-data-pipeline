"""
Simple Mock Data Generator for Pipeline Testing
Generates small datasets with compliance violations for quick testing

This module creates synthetic healthcare and financial data with intentional
GDPR/HIPAA compliance violations for testing our data processing pipelines.
"""
import pandas as pd
import numpy as np
from faker import Faker  # Library for generating fake but realistic data
import uuid
from datetime import datetime, timedelta
import json

class SimpleDataGenerator:
    def __init__(self):
        """Initialize the data generator with Faker instance for realistic data"""
        self.fake = Faker()  # Faker generates realistic fake data (names, addresses, etc.)
        
    def generate_healthcare_data(self, size=1000):
        """
        Generate simple healthcare data with some HIPAA violations
        
        Args:
            size (int): Number of patient records to generate
            
        Returns:
            pandas.DataFrame: Healthcare data with intentional violations
        """
        data = []
        
        # Generate each patient record
        for i in range(size):
            # Randomly decide if this record should have a compliance violation
            # 20% chance of violation for testing purposes
            has_violation = np.random.random() < 0.2
            
            # Create patient record with either real PHI (violation) or masked PHI (compliant)
            record = {
                'id': str(uuid.uuid4()),  # Unique identifier for each patient
                'patient_name': self.fake.name(),  # Generate realistic patient name
                
                # PHI fields: expose real data for violations, mask for compliance
                'ssn': self.fake.ssn() if has_violation else f"***-**-{str(i).zfill(4)}",
                'phone': self.fake.phone_number() if has_violation else "***-***-****",
                'email': self.fake.email() if has_violation else "***@***.com",
                
                # Medical information
                'diagnosis': np.random.choice(['diabetes', 'hypertension', 'asthma', 'flu']),
                'treatment_date': self.fake.date_time_between(start_date='-1y', end_date='now'),
                
                # Compliance tracking fields
                'has_violation': has_violation,  # Flag for testing compliance detection
                'violation_type': 'phi_exposure' if has_violation else None,  # Type of HIPAA violation
                'timestamp': datetime.now()  # When this record was generated
            }
            data.append(record)
            
        return pd.DataFrame(data)
    
    def generate_financial_data(self, size=1000):
        """
        Generate simple financial data with some GDPR violations
        
        Args:
            size (int): Number of transaction records to generate
            
        Returns:
            pandas.DataFrame: Financial data with intentional GDPR violations
        """
        data = []
        
        # Generate each transaction record
        for i in range(size):
            # Randomly decide if this record should have a GDPR violation
            # 15% chance of violation (lower than healthcare for realistic distribution)
            has_violation = np.random.random() < 0.15
            
            # Create financial transaction record
            record = {
                'id': str(uuid.uuid4()),  # Unique transaction identifier
                'customer_name': self.fake.name(),  # Customer name
                'account_number': f"ACC{i:06d}",  # Sequential account numbers
                
                # Transaction details
                'transaction_amount': round(np.random.uniform(10, 5000), 2),  # Random amount
                'transaction_date': self.fake.date_time_between(start_date='-6m', end_date='now'),
                'location': self.fake.city(),  # Transaction location
                
                # GDPR compliance fields
                'consent_given': not has_violation,  # Violation = no consent given
                'has_violation': has_violation,  # Flag for testing compliance detection
                'violation_type': 'missing_consent' if has_violation else None,  # GDPR violation type
                'timestamp': datetime.now()  # When this record was generated
            }
            data.append(record)
            
        return pd.DataFrame(data)
    
    def generate_ecommerce_data(self, size=1000):
        """
        Generate e-commerce order data with PCI-DSS violations
        
        Args:
            size (int): Number of order records to generate
            
        Returns:
            pandas.DataFrame: E-commerce data with intentional violations
        """
        data = []
        
        for i in range(size):
            # 10% chance of PCI-DSS violation (exposed credit card)
            has_violation = np.random.random() < 0.1
            
            record = {
                'order_id': f"ORD{i:06d}",
                'customer_email': self.fake.email(),
                'customer_name': self.fake.name(),
                'credit_card': self.fake.credit_card_number() if has_violation else "****-****-****-1234",
                'billing_address': self.fake.address(),
                'product_name': np.random.choice(['Laptop', 'Phone', 'Tablet', 'Headphones']),
                'order_amount': round(np.random.uniform(50, 2000), 2),
                'order_date': self.fake.date_time_between(start_date='-3m', end_date='now'),
                'shipping_address': self.fake.address(),
                'consent_marketing': np.random.choice([True, False]),
                'has_violation': has_violation,
                'violation_type': 'pci_dss_exposure' if has_violation else None,
                'timestamp': datetime.now()
            }
            data.append(record)
            
        return pd.DataFrame(data)
    
    def generate_iot_data(self, size=1000):
        """
        Generate IoT sensor data with location privacy violations
        
        Args:
            size (int): Number of sensor readings to generate
            
        Returns:
            pandas.DataFrame: IoT data with intentional violations
        """
        data = []
        
        for i in range(size):
            # 15% chance of location privacy violation (too precise coordinates)
            has_violation = np.random.random() < 0.15
            
            # Generate coordinates with varying precision
            if has_violation:
                # High precision coordinates (violation)
                lat = round(np.random.uniform(40.0, 41.0), 6)  # 6 decimal places
                lng = round(np.random.uniform(-74.0, -73.0), 6)
            else:
                # Low precision coordinates (compliant)
                lat = round(np.random.uniform(40.0, 41.0), 2)  # 2 decimal places
                lng = round(np.random.uniform(-74.0, -73.0), 2)
            
            record = {
                'device_id': f"DEV{i:04d}",
                'sensor_type': np.random.choice(['temperature', 'humidity', 'air_quality']),
                'location_lat': lat,
                'location_lng': lng,
                'temperature': round(np.random.uniform(15, 35), 1),
                'humidity': round(np.random.uniform(30, 80), 1),
                'user_id': f"USER{np.random.randint(1, 100):03d}",
                'reading_timestamp': self.fake.date_time_between(start_date='-1d', end_date='now'),
                'data_retention_days': np.random.choice([30, 90, 365, 1095]),  # Some may exceed limits
                'has_violation': has_violation,
                'violation_type': 'location_privacy' if has_violation else None,
                'timestamp': datetime.now()
            }
            data.append(record)
            
        return pd.DataFrame(data)
    
    def save_to_csv(self, df, filename):
        """
        Save dataframe to CSV file in the data directory
        
        Args:
            df (pandas.DataFrame): Data to save
            filename (str): Name of the CSV file
            
        Returns:
            str: Full filepath where data was saved
        """
        filepath = f"data/{filename}"
        df.to_csv(filepath, index=False)  # Save without row indices
        print(f"Saved {len(df)} records to {filepath}")
        return filepath
    
    def generate_stream_record(self, data_type='healthcare'):
        """
        Generate a single record for streaming/real-time processing
        
        Args:
            data_type (str): Type of data ('healthcare' or 'financial')
            
        Returns:
            dict: Single record as dictionary for JSON serialization
        """
        if data_type == 'healthcare':
            # Generate single healthcare record and convert to dictionary
            return self.generate_healthcare_data(1).iloc[0].to_dict()
        else:
            # Generate single financial record and convert to dictionary
            return self.generate_financial_data(1).iloc[0].to_dict()

def main():
    """
    Main function to generate test datasets for batch processing
    Creates both healthcare and financial datasets with compliance violations
    """
    generator = SimpleDataGenerator()
    
    # Generate healthcare dataset (5000 records for testing)
    print("Generating healthcare data...")
    healthcare_df = generator.generate_healthcare_data(5000)
    generator.save_to_csv(healthcare_df, "healthcare_batch.csv")
    
    # Generate financial dataset (5000 records for testing)
    print("Generating financial data...")
    financial_df = generator.generate_financial_data(5000)
    generator.save_to_csv(financial_df, "financial_batch.csv")
    
    # Print summary statistics
    print("Data generation complete!")
    print(f"Healthcare violations: {healthcare_df['has_violation'].sum()}")
    print(f"Financial violations: {financial_df['has_violation'].sum()}")

if __name__ == "__main__":
    main() 