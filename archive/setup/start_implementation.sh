#!/bin/bash

# Secure Data Pipeline Implementation Setup Script
# Research Practicum - Masters in Computing

echo "🚀 Starting Secure Data Pipeline Implementation Setup..."
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
}

print_info() {
    echo "ℹ️  $1"
}

# Check prerequisites
echo "📋 Checking Prerequisites..."

if command_exists docker; then
    print_status "Docker found"
else
    print_error "Docker not found. Please install Docker Desktop"
    exit 1
fi

if command_exists minikube; then
    print_status "Minikube found"
else
    print_error "Minikube not found. Please install minikube"
    echo "   Run: brew install minikube"
    exit 1
fi

if command_exists kubectl; then
    print_status "kubectl found"
else
    print_error "kubectl not found. Please install kubectl"
    echo "   Run: brew install kubectl"
    exit 1
fi

if command_exists helm; then
    print_status "Helm found"
else
    print_error "Helm not found. Please install Helm"
    echo "   Run: brew install helm"
    exit 1
fi

if command_exists python3; then
    print_status "Python3 found"
else
    print_error "Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Create project directory structure
echo ""
echo "📁 Creating Project Structure..."

# Main directories
mkdir -p {infrastructure,src,data,configs,notebooks,tests,docs,results}

# Infrastructure subdirectories
mkdir -p infrastructure/{kafka,spark,flink,monitoring,security}

# Source code subdirectories  
mkdir -p src/{batch_processing,stream_processing,hybrid_processing,anonymization,compliance,monitoring,data_generation}

# Data subdirectories
mkdir -p data/{raw,processed,anonymized,synthetic,compliance_violations}

# Config subdirectories
mkdir -p configs/{kafka,spark,flink,grafana,prometheus}

# Test subdirectories
mkdir -p tests/{unit,integration,performance,compliance}

print_status "Project structure created"

# Create Python virtual environment
echo ""
echo "🐍 Setting up Python Environment..."

python3 -m venv venv
source venv/bin/activate

print_status "Python virtual environment created"

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Data Processing
pandas==2.1.0
numpy==1.24.3
pyspark==3.4.1

# Streaming
kafka-python==2.0.2
confluent-kafka==2.2.0

# Data Generation
faker==19.3.0
mimesis==11.1.0

# Anonymization
diffprivlib==0.6.0
opendp==0.7.0

# Monitoring
prometheus-client==0.17.1
grafana-api==1.0.3

# Kubernetes
kubernetes==27.2.0

# Security
cryptography==41.0.3
hvac==1.1.1

# Data Quality
great-expectations==0.17.12

# Analysis and Visualization
scipy==1.11.2
statsmodels==0.14.0
matplotlib==3.7.2
seaborn==0.12.2
plotly==5.15.0

# Testing
pytest==7.4.0
pytest-cov==4.1.0

# Utilities
click==8.1.7
pyyaml==6.0.1
python-dotenv==1.0.0
tqdm==4.66.1
EOF

pip install -r requirements.txt

print_status "Python dependencies installed"

# Create basic configuration files
echo ""
echo "⚙️  Creating Configuration Files..."

# Docker Compose for local development
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    hostname: zookeeper
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    hostname: kafka
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "9997:9997"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_JMX_PORT: 9997
      KAFKA_JMX_HOSTNAME: localhost

  postgresql:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: compliance_db
      POSTGRES_USER: compliance_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
EOF

print_status "Docker Compose configuration created"

# Create Minikube startup script
cat > infrastructure/start_minikube.sh << 'EOF'
#!/bin/bash

echo "Starting Minikube cluster..."

# Start Minikube with sufficient resources
minikube start --memory=8192 --cpus=4 --disk-size=50g --driver=docker

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard

# Create namespaces
kubectl create namespace data-pipeline --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace security --dry-run=client -o yaml | kubectl apply -f -

# Set default namespace
kubectl config set-context --current --namespace=data-pipeline

echo "Minikube setup complete!"
echo "Dashboard URL: $(minikube dashboard --url)"
EOF

chmod +x infrastructure/start_minikube.sh

print_status "Minikube startup script created"

# Create basic Kafka configuration
cat > configs/kafka/topics.yaml << 'EOF'
topics:
  - name: healthcare-data
    partitions: 3
    replication-factor: 1
  - name: financial-data
    partitions: 3
    replication-factor: 1
  - name: iot-sensor-data
    partitions: 6
    replication-factor: 1
  - name: compliance-violations
    partitions: 3
    replication-factor: 1
  - name: anonymized-data
    partitions: 3
    replication-factor: 1
EOF

print_status "Kafka topic configuration created"

# Create basic data generator
cat > src/data_generation/mock_data_generator.py << 'EOF'
"""
Mock Data Generator for Secure Data Pipeline Research
Generates healthcare, financial, and IoT data with compliance violations
"""

import pandas as pd
import numpy as np
from faker import Faker
import uuid
from datetime import datetime, timedelta
import json
import argparse

class MockDataGenerator:
    def __init__(self, locale='en_US'):
        self.fake = Faker(locale)
        
    def generate_healthcare_data(self, size=10000, violation_rate=0.1):
        """Generate healthcare data with HIPAA compliance violations"""
        data = []
        
        for i in range(size):
            # Randomly inject violations
            has_violation = np.random.random() < violation_rate
            violation_type = None
            
            if has_violation:
                violation_type = np.random.choice([
                    'expired_consent', 'retention_exceeded', 
                    'phi_exposure', 'unauthorized_access'
                ])
            
            record = {
                'patient_id': str(uuid.uuid4()),
                'first_name': self.fake.first_name(),
                'last_name': self.fake.last_name(),
                'date_of_birth': self.fake.date_of_birth(minimum_age=18, maximum_age=90),
                'ssn': self.fake.ssn(),
                'phone': self.fake.phone_number(),
                'email': self.fake.email(),
                'address': self.fake.street_address(),
                'city': self.fake.city(),
                'state': self.fake.state_abbr(),
                'zip_code': self.fake.zipcode(),
                'medical_record_number': f'MRN{i:08d}',
                'diagnosis_code': np.random.choice(['J44.0', 'E11.9', 'I25.9', 'M79.3']),
                'treatment_date': self.fake.date_time_between(start_date='-2y', end_date='now'),
                'provider_name': self.fake.name(),
                'insurance_id': f'INS{i:08d}',
                'billing_amount': round(np.random.uniform(100, 5000), 2),
                'consent_status': not (violation_type == 'expired_consent'),
                'consent_date': self.fake.date_time_between(start_date='-3y', end_date='-1y'),
                'data_retention_days': np.random.choice([365, 1095, 2555]),  # 1, 3, 7 years
                'violation_type': violation_type,
                'created_timestamp': datetime.now()
            }
            data.append(record)
            
        return pd.DataFrame(data)
    
    def generate_financial_data(self, size=50000, violation_rate=0.08):
        """Generate financial data with GDPR compliance violations"""
        data = []
        
        for i in range(size):
            has_violation = np.random.random() < violation_rate
            violation_type = None
            
            if has_violation:
                violation_type = np.random.choice([
                    'cross_border_violation', 'excessive_collection',
                    'missing_consent', 'data_minimization_violation'
                ])
            
            record = {
                'customer_id': str(uuid.uuid4()),
                'account_number': f'ACC{i:010d}',
                'full_name': self.fake.name(),
                'date_of_birth': self.fake.date_of_birth(minimum_age=18, maximum_age=80),
                'national_id': self.fake.ssn(),
                'phone_number': self.fake.phone_number(),
                'email_address': self.fake.email(),
                'home_address': self.fake.address(),
                'transaction_id': str(uuid.uuid4()),
                'transaction_amount': round(np.random.uniform(10, 10000), 2),
                'transaction_date': self.fake.date_time_between(start_date='-1y', end_date='now'),
                'merchant_category': np.random.choice(['grocery', 'gas', 'restaurant', 'retail', 'healthcare']),
                'payment_method': np.random.choice(['credit_card', 'debit_card', 'bank_transfer', 'digital_wallet']),
                'ip_address': self.fake.ipv4(),
                'device_id': str(uuid.uuid4()),
                'geolocation': f'{self.fake.latitude()},{self.fake.longitude()}',
                'risk_score': np.random.uniform(0, 1),
                'consent_timestamp': self.fake.date_time_between(start_date='-2y', end_date='now'),
                'processing_purpose': np.random.choice(['payment_processing', 'fraud_detection', 'marketing', 'analytics']),
                'violation_type': violation_type,
                'created_timestamp': datetime.now()
            }
            data.append(record)
            
        return pd.DataFrame(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate mock data for compliance testing')
    parser.add_argument('--type', choices=['healthcare', 'financial', 'both'], default='both')
    parser.add_argument('--size', type=int, default=10000)
    parser.add_argument('--violation-rate', type=float, default=0.1)
    parser.add_argument('--output-dir', default='data/raw')
    
    args = parser.parse_args()
    
    generator = MockDataGenerator()
    
    if args.type in ['healthcare', 'both']:
        print(f"Generating {args.size} healthcare records...")
        healthcare_df = generator.generate_healthcare_data(args.size, args.violation_rate)
        healthcare_df.to_csv(f'{args.output_dir}/healthcare_data_{args.size}.csv', index=False)
        healthcare_df.to_parquet(f'{args.output_dir}/healthcare_data_{args.size}.parquet')
        print(f"Healthcare data saved to {args.output_dir}/")
        
    if args.type in ['financial', 'both']:
        print(f"Generating {args.size} financial records...")
        financial_df = generator.generate_financial_data(args.size, args.violation_rate)
        financial_df.to_csv(f'{args.output_dir}/financial_data_{args.size}.csv', index=False)
        financial_df.to_parquet(f'{args.output_dir}/financial_data_{args.size}.parquet')
        print(f"Financial data saved to {args.output_dir}/")
        
    print("Mock data generation complete!")
EOF

print_status "Mock data generator created"

# Create basic compliance rule engine
cat > src/compliance/rule_engine.py << 'EOF'
"""
Compliance Rule Engine for GDPR and HIPAA violations
"""

from datetime import datetime, timedelta
import re
from typing import Dict, List, Any

class ComplianceRuleEngine:
    def __init__(self):
        self.gdpr_rules = self._load_gdpr_rules()
        self.hipaa_rules = self._load_hipaa_rules()
        
    def _load_gdpr_rules(self):
        return {
            'consent_validity': {
                'description': 'Check if consent is valid and not expired',
                'function': self._check_consent_validity
            },
            'data_retention': {
                'description': 'Check if data retention period is exceeded',
                'function': self._check_data_retention
            },
            'data_minimization': {
                'description': 'Check if excessive data is collected',
                'function': self._check_data_minimization
            },
            'cross_border_transfer': {
                'description': 'Check unauthorized cross-border data transfers',
                'function': self._check_cross_border_transfer
            }
        }
    
    def _load_hipaa_rules(self):
        return {
            'phi_exposure': {
                'description': 'Check for exposed PHI identifiers',
                'function': self._check_phi_exposure
            },
            'minimum_necessary': {
                'description': 'Check minimum necessary rule compliance',
                'function': self._check_minimum_necessary
            },
            'access_controls': {
                'description': 'Check proper access controls',
                'function': self._check_access_controls
            }
        }
    
    def evaluate_record(self, record: Dict[str, Any], regulation: str = 'both') -> Dict[str, Any]:
        """Evaluate a single record against compliance rules"""
        violations = []
        
        if regulation in ['gdpr', 'both']:
            for rule_name, rule_config in self.gdpr_rules.items():
                violation = rule_config['function'](record)
                if violation:
                    violations.append({
                        'rule': rule_name,
                        'regulation': 'GDPR',
                        'description': rule_config['description'],
                        'violation_details': violation
                    })
        
        if regulation in ['hipaa', 'both']:
            for rule_name, rule_config in self.hipaa_rules.items():
                violation = rule_config['function'](record)
                if violation:
                    violations.append({
                        'rule': rule_name,
                        'regulation': 'HIPAA',
                        'description': rule_config['description'],
                        'violation_details': violation
                    })
        
        return {
            'record_id': record.get('patient_id') or record.get('customer_id'),
            'violations': violations,
            'compliant': len(violations) == 0,
            'evaluation_timestamp': datetime.now()
        }
    
    def _check_consent_validity(self, record):
        """Check if consent is valid and not expired"""
        consent_status = record.get('consent_status', False)
        consent_date = record.get('consent_date')
        
        if not consent_status:
            return 'Consent not provided or withdrawn'
        
        if consent_date and isinstance(consent_date, datetime):
            # Consent expires after 2 years
            if datetime.now() - consent_date > timedelta(days=730):
                return 'Consent expired (>2 years old)'
        
        return None
    
    def _check_data_retention(self, record):
        """Check if data retention period is exceeded"""
        created_timestamp = record.get('created_timestamp') or record.get('treatment_date')
        retention_days = record.get('data_retention_days', 1095)  # Default 3 years
        
        if created_timestamp and isinstance(created_timestamp, datetime):
            if datetime.now() - created_timestamp > timedelta(days=retention_days):
                return f'Data retention period exceeded ({retention_days} days)'
        
        return None
    
    def _check_phi_exposure(self, record):
        """Check for exposed PHI identifiers"""
        phi_fields = ['ssn', 'phone', 'email', 'medical_record_number']
        exposed_fields = []
        
        for field in phi_fields:
            if field in record and record[field]:
                # Check if field is properly masked/encrypted
                value = str(record[field])
                if not self._is_properly_anonymized(value):
                    exposed_fields.append(field)
        
        if exposed_fields:
            return f'Exposed PHI fields: {", ".join(exposed_fields)}'
        
        return None
    
    def _is_properly_anonymized(self, value):
        """Check if a value is properly anonymized"""
        # Simple check - look for patterns that suggest non-anonymized data
        patterns = [
            r'\d{3}-\d{2}-\d{4}',  # SSN pattern
            r'\(\d{3}\)\s?\d{3}-\d{4}',  # Phone pattern
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'  # Email pattern
        ]
        
        for pattern in patterns:
            if re.search(pattern, value):
                return False
        
        return True
    
    # Additional rule implementations...
    def _check_data_minimization(self, record):
        return None  # Placeholder
    
    def _check_cross_border_transfer(self, record):
        return None  # Placeholder
        
    def _check_minimum_necessary(self, record):
        return None  # Placeholder
        
    def _check_access_controls(self, record):
        return None  # Placeholder

if __name__ == '__main__':
    # Test the rule engine
    engine = ComplianceRuleEngine()
    
    test_record = {
        'patient_id': '12345',
        'ssn': '123-45-6789',
        'consent_status': False,
        'consent_date': datetime.now() - timedelta(days=800),
        'created_timestamp': datetime.now() - timedelta(days=1200),
        'data_retention_days': 1095
    }
    
    result = engine.evaluate_record(test_record, 'both')
    print(f"Compliance evaluation result: {result}")
EOF

print_status "Compliance rule engine created"

# Create a simple README
cat > README.md << 'EOF'
# Secure Data Pipeline Research Implementation

## Research Questions

1. **Batch vs Real-time Verification**: How do batch verification and real-time automated verification compare in ensuring compliance and detecting violations in data pipelines?

2. **Anonymization Technique Comparison**: How do k-anonymity, differential privacy, and tokenization techniques perform under varying data volumes and real-time processing constraints?

3. **Hybrid Architecture Evaluation**: How does a hybrid batch-stream processing architecture with adaptive privacy budget allocation compare to single-mode processing?

## Quick Start

1. **Start local infrastructure**:
   ```bash
   # Start Docker services
   docker-compose up -d
   
   # Start Minikube (in a new terminal)
   ./infrastructure/start_minikube.sh
   ```

2. **Generate mock data**:
   ```bash
   python src/data_generation/mock_data_generator.py --type both --size 10000
   ```

3. **Test compliance engine**:
   ```bash
   python src/compliance/rule_engine.py
   ```

## Project Structure

```
├── infrastructure/     # Kubernetes manifests, Helm charts
├── src/               # Source code
│   ├── batch_processing/
│   ├── stream_processing/
│   ├── hybrid_processing/
│   ├── anonymization/
│   ├── compliance/
│   └── monitoring/
├── data/              # Generated datasets
├── configs/           # Configuration files
├── tests/             # Test suites
└── results/           # Experimental results
```

## Next Steps

1. Set up monitoring stack (Prometheus + Grafana)
2. Implement batch processing pipeline with Spark
3. Implement stream processing pipeline with Flink
4. Develop anonymization modules
5. Create hybrid architecture
6. Run experiments and collect data

## Development

Activate virtual environment:
```bash
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```
EOF

print_status "README.md created"

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.env
.venv/

# Data files
data/raw/*.csv
data/raw/*.parquet
data/processed/*.csv
data/processed/*.parquet
*.db
*.sqlite

# Jupyter Notebooks
.ipynb_checkpoints/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp

# Results and outputs
results/*.png
results/*.pdf
results/*.html

# Secrets and configs
.env
secrets.yaml
*.key
*.pem
EOF

print_status ".gitignore created"

# Final setup
echo ""
echo "🎯 Final Setup Steps..."

# Make scripts executable
chmod +x src/data_generation/mock_data_generator.py
chmod +x src/compliance/rule_engine.py

print_status "Made scripts executable"

echo ""
echo "🎉 Setup Complete!"
echo "=================================================="
echo ""
echo "📋 Next Steps:"
echo "1. Activate Python environment: source venv/bin/activate"
echo "2. Start Docker services: docker-compose up -d"
echo "3. Start Minikube: ./infrastructure/start_minikube.sh"
echo "4. Generate test data: python src/data_generation/mock_data_generator.py"
echo "5. Test compliance engine: python src/compliance/rule_engine.py"
echo ""
echo "📖 Documentation:"
echo "- Architecture: ./architecture_diagrams.md"
echo "- Implementation Guide: ./implementation_setup.md"
echo "- Evaluation Framework: ./research_evaluation_framework.md"
echo ""
echo "🔬 Research Focus:"
echo "- RQ1: Batch vs Stream processing comparison"
echo "- RQ2: Anonymization technique evaluation"
echo "- RQ3: Hybrid architecture performance"
echo ""
echo "Happy researching! 🚀"

print_status "Setup complete! Check README.md for next steps."
echo ""
echo "🎯 Immediate Next Steps:"
echo "1. source venv/bin/activate"
echo "2. pip install -r requirements.txt"
echo "3. docker-compose up -d"
echo "4. ./infrastructure/start_minikube.sh" 