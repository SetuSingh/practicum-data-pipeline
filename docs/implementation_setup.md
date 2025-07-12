# Implementation Setup Guide

## Quick Start Infrastructure Setup

### Prerequisites

```bash
# Required tools
- Docker Desktop
- Minikube
- kubectl
- Helm 3.x
- Python 3.9+
- Java 11+
```

### Step 1: Environment Setup (Day 1)

#### 1.1 Minikube Cluster Setup

```bash
# Start Minikube with sufficient resources
minikube start --memory=8192 --cpus=4 --disk-size=50g

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server

# Verify cluster
kubectl cluster-info
```

#### 1.2 Namespace Setup

```bash
# Create dedicated namespaces
kubectl create namespace data-pipeline
kubectl create namespace monitoring
kubectl create namespace security

# Set default namespace
kubectl config set-context --current --namespace=data-pipeline
```

### Step 2: Core Infrastructure Deployment (Day 2)

#### 2.1 Kafka Deployment

```bash
# Add Strimzi Helm repository
helm repo add strimzi https://strimzi.io/charts/
helm repo update

# Install Kafka operator
helm install kafka-operator strimzi/strimzi-kafka-operator \
  --namespace data-pipeline \
  --version 0.38.0

# Deploy Kafka cluster (create kafka-cluster.yaml)
kubectl apply -f kafka-cluster.yaml
```

#### 2.2 Spark Deployment

```bash
# Add Spark Helm repository
helm repo add spark https://googlecloudplatform.github.io/spark-on-k8s-operator
helm repo update

# Install Spark operator
helm install spark-operator spark/spark-operator \
  --namespace data-pipeline \
  --set webhook.enable=true
```

#### 2.3 Monitoring Stack

```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus + Grafana
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Step 3: Security Components (Day 3)

#### 3.1 HashiCorp Vault

```bash
# Add Vault Helm repository
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Install Vault
helm install vault hashicorp/vault \
  --namespace security \
  --set server.dev.enabled=true
```

#### 3.2 RBAC Configuration

```yaml
# rbac-config.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: data-pipeline-operator
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

## Mock Dataset Specifications

### Dataset 1: Healthcare Data (HIPAA Compliance Testing)

#### Schema Design

```python
healthcare_schema = {
    "patient_id": "uuid",
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "date",
    "ssn": "string",
    "phone": "string",
    "email": "string",
    "address": "string",
    "city": "string",
    "state": "string",
    "zip_code": "string",
    "medical_record_number": "string",
    "diagnosis_code": "string",
    "treatment_date": "timestamp",
    "provider_name": "string",
    "insurance_id": "string",
    "billing_amount": "decimal",
    "lab_results": "string",
    "prescription_data": "string",
    "emergency_contact": "string",
    "consent_status": "boolean",
    "data_retention_period": "integer"
}
```

#### Volume Specifications

- **Small**: 10,000 patients (1GB)
- **Medium**: 100,000 patients (10GB)
- **Large**: 1,000,000 patients (50GB+)

#### Compliance Violations to Include

```python
violation_scenarios = [
    "expired_consent",           # GDPR Article 7
    "retention_period_exceeded", # GDPR Article 5(1)(e)
    "unauthorized_cross_border", # GDPR Article 44
    "missing_legal_basis",       # GDPR Article 6
    "excessive_data_collection", # Data minimization violation
    "phi_exposure",             # HIPAA violation
    "missing_consent_withdrawal" # Right to be forgotten
]
```

### Dataset 2: Financial Data (GDPR Compliance Testing)

#### Schema Design

```python
financial_schema = {
    "customer_id": "uuid",
    "account_number": "string",
    "full_name": "string",
    "date_of_birth": "date",
    "national_id": "string",
    "phone_number": "string",
    "email_address": "string",
    "home_address": "string",
    "employment_status": "string",
    "annual_income": "decimal",
    "transaction_id": "uuid",
    "transaction_amount": "decimal",
    "transaction_date": "timestamp",
    "merchant_category": "string",
    "payment_method": "string",
    "device_id": "string",
    "ip_address": "string",
    "geolocation": "string",
    "risk_score": "float",
    "consent_timestamp": "timestamp",
    "data_subject_rights": "json"
}
```

### Dataset 3: IoT Sensor Data (Real-time Processing)

#### Schema Design

```python
iot_schema = {
    "device_id": "string",
    "user_id": "uuid",
    "timestamp": "timestamp",
    "sensor_type": "string",
    "location_lat": "float",
    "location_lng": "float",
    "temperature": "float",
    "humidity": "float",
    "motion_detected": "boolean",
    "audio_level": "float",
    "image_hash": "string",
    "device_metadata": "json",
    "privacy_level": "integer",
    "consent_scope": "string",
    "retention_policy": "string"
}
```

#### Streaming Characteristics

- **Rate**: 1000-10000 records/second
- **Burst Testing**: 50000 records/second
- **Duration**: Continuous 24/7 simulation

## Mock Data Generation Scripts

### Healthcare Data Generator

```python
# healthcare_data_generator.py
import pandas as pd
import numpy as np
from faker import Faker
import uuid
from datetime import datetime, timedelta

class HealthcareDataGenerator:
    def __init__(self, size=10000):
        self.fake = Faker()
        self.size = size

    def generate_patient_data(self):
        data = []
        for i in range(self.size):
            # Add compliance violations randomly
            violation_type = np.random.choice([
                None, "expired_consent", "retention_exceeded",
                "missing_legal_basis"], p=[0.7, 0.1, 0.1, 0.1])

            patient = {
                "patient_id": str(uuid.uuid4()),
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "date_of_birth": self.fake.date_of_birth(minimum_age=18, maximum_age=90),
                "ssn": self.fake.ssn(),
                "phone": self.fake.phone_number(),
                "email": self.fake.email(),
                "address": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state_abbr(),
                "zip_code": self.fake.zipcode(),
                "medical_record_number": f"MRN{i:08d}",
                "diagnosis_code": np.random.choice(["J44.0", "E11.9", "I25.9", "M79.3"]),
                "treatment_date": self.fake.date_time_between(start_date="-2y", end_date="now"),
                "provider_name": self.fake.name(),
                "insurance_id": f"INS{i:08d}",
                "billing_amount": round(np.random.uniform(100, 5000), 2),
                "consent_status": violation_type != "expired_consent",
                "violation_type": violation_type
            }
            data.append(patient)

        return pd.DataFrame(data)

    def save_datasets(self):
        df = self.generate_patient_data()

        # Save in multiple formats
        df.to_csv(f"healthcare_data_{self.size}.csv", index=False)
        df.to_parquet(f"healthcare_data_{self.size}.parquet")
        df.to_json(f"healthcare_data_{self.size}.json", orient="records")

        print(f"Generated {self.size} healthcare records")
        return df

# Usage
generator = HealthcareDataGenerator(size=50000)
healthcare_df = generator.save_datasets()
```

### Financial Data Generator

```python
# financial_data_generator.py
class FinancialDataGenerator:
    def __init__(self, size=100000):
        self.fake = Faker()
        self.size = size

    def generate_transaction_data(self):
        data = []
        for i in range(self.size):
            # Simulate GDPR violations
            violation_type = np.random.choice([
                None, "cross_border_violation", "excessive_collection",
                "missing_consent"], p=[0.8, 0.07, 0.08, 0.05])

            transaction = {
                "customer_id": str(uuid.uuid4()),
                "account_number": f"ACC{i:010d}",
                "full_name": self.fake.name(),
                "transaction_id": str(uuid.uuid4()),
                "transaction_amount": round(np.random.uniform(10, 10000), 2),
                "transaction_date": self.fake.date_time_between(start_date="-1y", end_date="now"),
                "merchant_category": np.random.choice(["grocery", "gas", "restaurant", "retail", "healthcare"]),
                "ip_address": self.fake.ipv4(),
                "geolocation": f"{self.fake.latitude()},{self.fake.longitude()}",
                "risk_score": np.random.uniform(0, 1),
                "violation_type": violation_type
            }
            data.append(transaction)

        return pd.DataFrame(data)

# Generate datasets of different sizes
sizes = [10000, 50000, 100000, 500000]
for size in sizes:
    generator = FinancialDataGenerator(size=size)
    df = generator.generate_transaction_data()
    df.to_parquet(f"financial_data_{size}.parquet")
```

### IoT Streaming Data Generator

```python
# iot_stream_generator.py
import json
import time
from kafka import KafkaProducer

class IoTStreamGenerator:
    def __init__(self, kafka_bootstrap_servers=['localhost:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.fake = Faker()

    def generate_sensor_record(self):
        return {
            "device_id": f"sensor_{np.random.randint(1, 1000)}",
            "user_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sensor_type": np.random.choice(["temperature", "motion", "audio", "camera"]),
            "location_lat": float(self.fake.latitude()),
            "location_lng": float(self.fake.longitude()),
            "temperature": round(np.random.uniform(15, 35), 2),
            "humidity": round(np.random.uniform(30, 80), 1),
            "motion_detected": np.random.choice([True, False]),
            "audio_level": round(np.random.uniform(30, 90), 1),
            "privacy_level": np.random.randint(1, 5),
            "consent_scope": np.random.choice(["full", "limited", "analytics_only"]),
            "violation_flag": np.random.choice([None, "location_tracking", "audio_recording"], p=[0.9, 0.05, 0.05])
        }

    def start_streaming(self, topic="iot-sensor-data", records_per_second=1000, duration_minutes=60):
        total_records = records_per_second * duration_minutes * 60
        interval = 1.0 / records_per_second

        for i in range(total_records):
            record = self.generate_sensor_record()
            self.producer.send(topic, value=record)

            if i % 1000 == 0:
                print(f"Sent {i} records")

            time.sleep(interval)

        self.producer.flush()
        self.producer.close()

# Start IoT data streaming
iot_generator = IoTStreamGenerator()
# Stream 1000 records/second for 30 minutes
iot_generator.start_streaming(records_per_second=1000, duration_minutes=30)
```

## Development Environment Setup

### Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Requirements.txt

```
pandas==2.1.0
numpy==1.24.3
faker==19.3.0
kafka-python==2.0.2
pyspark==3.4.1
apache-flink==1.17.1
prometheus-client==0.17.1
grafana-api==1.0.3
kubernetes==27.2.0
hvac==1.1.1  # HashiCorp Vault client
cryptography==41.0.3
great-expectations==0.17.12
```

## Next Steps Priority

1. **Week 1**: Set up Minikube cluster and deploy Kafka
2. **Week 2**: Implement batch processing pipeline with Spark
3. **Week 3**: Develop anonymization modules (k-anonymity, DP)
4. **Week 4**: Build real-time stream processing with Flink
5. **Week 5**: Create compliance monitoring and alerting
6. **Week 6**: Implement hybrid processing logic
7. **Week 7-8**: Performance testing and optimization
8. **Week 9-10**: Data collection and paper writing

This setup provides a solid foundation for your research implementation while maintaining focus on the evaluatable research questions.
