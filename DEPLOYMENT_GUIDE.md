# 🚀 Deployment Guide - Cross-Platform Setup

## 📋 **SYSTEM REQUIREMENTS**

### **Minimum Requirements:**

- **OS**: macOS 10.15+, Windows 10+, Ubuntu 18.04+
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: 4 cores minimum, 8 cores recommended
- **Storage**: 10GB free space
- **Docker**: Docker Desktop 4.0+ with Docker Compose
- **Python**: Python 3.9+ (3.11+ recommended)
- **Java**: Java 11+ (Java 17+ recommended for best Spark compatibility)

---

## 🔧 **ONE-COMMAND SETUP**

### **Quick Start (Recommended)**

```bash
# Clone and setup everything automatically
git clone <repository-url>
cd practicum
chmod +x start-setup.sh
./start-setup.sh
```

This script handles:

- ✅ Docker service startup
- ✅ Python environment creation
- ✅ Dependency installation
- ✅ Database schema setup
- ✅ Kafka topic creation
- ✅ Test data generation

---

## 📦 **MANUAL SETUP (If Automated Setup Fails)**

### **Step 1: Prerequisites**

```bash
# Verify Docker is running
docker --version && docker-compose --version

# Verify Python version
python3 --version  # Should be 3.9+

# Verify Java (for Spark)
java -version  # Should be Java 11+
```

### **Step 2: Infrastructure**

```bash
# Start all services in Docker
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
docker-compose ps  # All services should show "Up"
```

### **Step 3: Python Environment**

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### **Step 4: Database Setup**

```bash
# Setup PostgreSQL database and schema
python setup/setup_database.py

# Verify database connection
python -c "
from src.database.postgres_connector import PostgreSQLConnector
db = PostgreSQLConnector('localhost', 5433, 'compliance_db', 'admin', 'password')
print('✅ Database connected successfully')
"
```

### **Step 5: Kafka Setup**

```bash
# Create Kafka topics
docker exec practicum-kafka kafka-topics \
  --create --topic healthcare-stream \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 1

# Verify Kafka connectivity
python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['localhost:9093'])
producer.close()
print('✅ Kafka connected successfully')
"
```

### **Step 6: Test System**

```bash
# Run comprehensive system test
python test_real_vs_simulated_fixed.py

# Should show all ✅ REAL processing modes working
```

---

## 🌍 **CROSS-PLATFORM COMPATIBILITY**

### **macOS (Intel & Apple Silicon)**

```bash
# For Apple Silicon Macs, ensure Docker uses correct architecture
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# Run setup
./start-setup.sh
```

### **Windows**

```powershell
# Use PowerShell or Git Bash
# Ensure Docker Desktop is running with WSL2 backend

# Clone repository
git clone <repository-url>
cd practicum

# Run setup (use Git Bash)
bash start-setup.sh
```

### **Linux (Ubuntu/Debian)**

```bash
# Install Docker if not present
sudo apt update
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Run setup
./start-setup.sh
```

---

## 🔧 **CONFIGURATION FILES**

### **Docker Services (`docker-compose.yml`)**

- ✅ **Kafka**: Port 9093 (external)
- ✅ **PostgreSQL**: Port 5433 (external)
- ✅ **Spark Master**: Port 8080 (UI)
- ✅ **Flink Dashboard**: Port 8082 (UI)
- ✅ **Storm UI**: Port 8084 (UI)
- ✅ **Grafana**: Port 3000 (admin/admin)

### **Python Dependencies (`backend/requirements.txt`)**

- ✅ **Core**: pandas, numpy, pyspark
- ✅ **Messaging**: kafka-python
- ✅ **Database**: psycopg2-binary
- ✅ **Web**: Flask, Flask-CORS
- ✅ **Utilities**: requests, setuptools

### **Frontend (`frontend/package.json`)**

- ✅ **Framework**: React 18 with TypeScript
- ✅ **Build**: Vite with hot reload
- ✅ **UI**: Tailwind CSS, Lucide icons
- ✅ **Charts**: Recharts for visualization

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues & Solutions**

#### **1. Spark Java Compatibility Error**

```
Error: "getSubject is supported only if a security manager is allowed"
```

**Solution**: Java security flags are already configured in `SparkBatchProcessor`:

```python
.config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow")
.config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow")
```

#### **2. Kafka Connection Refused**

```
Error: "[Errno 61] Connection refused"
```

**Solutions**:

```bash
# Check Docker services
docker-compose ps

# Restart Kafka
docker-compose restart kafka

# Wait 30 seconds and test
python -c "from kafka import KafkaProducer; KafkaProducer(bootstrap_servers=['localhost:9093'])"
```

#### **3. PostgreSQL Connection Failed**

```
Error: "could not connect to server"
```

**Solutions**:

```bash
# Check PostgreSQL container
docker logs practicum-postgres

# Restart PostgreSQL
docker-compose restart postgres

# Verify port is available
netstat -an | grep 5433
```

#### **4. Docker Platform Issues (Apple Silicon)**

```
Error: Platform compatibility warnings
```

**Solution**:

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker-compose up -d
```

#### **5. Python Package Conflicts**

```
Error: Version conflicts or import errors
```

**Solution**:

```bash
# Fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 **VERIFICATION COMMANDS**

### **Infrastructure Check**

```bash
# Docker services status
docker-compose ps

# Should show all services as "Up":
# - practicum-kafka
# - practicum-postgres
# - practicum-zookeeper
# - practicum-spark-master
# - practicum-flink-jobmanager
```

### **Application Check**

```bash
# Backend test
cd backend
python test_real_vs_simulated_fixed.py

# Expected output:
# ✅ Kafka: Available
# ✅ Spark Batch Engine: Distributed processing ready
# ✅ Storm Stream Engine: Kafka integration ready
# ✅ Flink Hybrid Engine: Intelligent routing ready
```

### **Frontend Check**

```bash
# Frontend development server
cd frontend
npm install
npm run dev

# Should open http://localhost:3007
```

---

## 🌐 **NETWORK PORTS**

| Service         | Internal Port | External Port | Purpose               |
| --------------- | ------------- | ------------- | --------------------- |
| Kafka           | 29092         | 9093          | Message streaming     |
| PostgreSQL      | 5432          | 5433          | Compliance database   |
| Zookeeper       | 2181          | 2182          | Kafka coordination    |
| Spark Master    | 8080          | 8080          | Spark cluster UI      |
| Flink Dashboard | 8081          | 8082          | Flink job monitoring  |
| Storm UI        | 8080          | 8084          | Storm topology UI     |
| Grafana         | 3000          | 3000          | Monitoring dashboards |
| Flask Backend   | 5000          | 5000          | API server            |
| React Frontend  | 3007          | 3007          | Web interface         |

---

## 📂 **PROJECT STRUCTURE**

```
practicum/
├── 🐳 docker-compose.yml      # All infrastructure services
├── 🚀 start-setup.sh          # One-command setup script
├── backend/
│   ├── 📦 requirements.txt    # Python dependencies
│   ├── 🌐 app.py              # Flask application
│   ├── 🔧 src/               # Processing engines
│   ├── 📊 data/              # Input/output data
│   └── 🧪 tests/             # Test suites
├── frontend/
│   ├── 📦 package.json       # Node.js dependencies
│   ├── ⚛️ src/               # React components
│   └── 🎨 public/            # Static assets
└── setup/
    ├── 🗄️ setup_database.py   # Database initialization
    └── ⚡ quick_start.sh      # Alternative setup script
```

---

## ✅ **SUCCESS INDICATORS**

### **System Ready When You See:**

```bash
✅ Docker services: All containers running
✅ Kafka: 10+ topics available
✅ PostgreSQL: 6+ users in compliance database
✅ Spark: Distributed processing engine ready
✅ Frontend: Development server on http://localhost:3007
✅ Backend: API server on http://localhost:5000
```

### **Test Processing:**

```bash
# Upload a CSV file through the web interface
# OR use direct API:
curl -X POST http://localhost:5000/api/upload \
  -F "file=@your_data.csv" \
  -F "pipeline=batch"

# Should return job_id and start processing immediately
```

---

## 🎯 **DEPLOYMENT SUMMARY**

Your data processing pipeline is designed for **maximum portability**:

- ✅ **Docker Containerization**: All infrastructure services
- ✅ **Python Virtual Environment**: Isolated dependencies
- ✅ **Cross-platform Support**: macOS, Windows, Linux
- ✅ **Automated Setup**: One-command deployment
- ✅ **Zero Configuration**: Works out of the box
- ✅ **Real Infrastructure**: No simulations or mocks

**Expected Setup Time**: 5-10 minutes for full deployment

🚀 **Your system is enterprise-ready and fully portable!**
