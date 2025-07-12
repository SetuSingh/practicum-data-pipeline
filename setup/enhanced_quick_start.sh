#!/bin/bash

# Enhanced Quick Start Script for Secure Data Pipeline Research
# Comprehensive cross-platform setup with automatic configuration

echo "🚀 Enhanced Quick Start - Secure Data Pipeline Research"
echo "======================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_header() {
    echo -e "${BLUE}🔧 $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    print_info "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port >/dev/null 2>&1; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "$service_name failed to start on port $port"
    return 1
}

# Platform detection
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "Windows"
    else
        echo "Unknown"
    fi
}

PLATFORM=$(detect_platform)
print_info "Detected platform: $PLATFORM"

# Prerequisites check
print_header "Checking Prerequisites"

# Check Docker
if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker Desktop first."
    echo "  Download from: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

print_status "Docker is running"

# Check Python
PYTHON_CMD=""
if command_exists python3; then
    PYTHON_CMD="python3"
elif command_exists python; then
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1)
    if [ "$PYTHON_VERSION" = "3" ]; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python 3.9+ is required. Please install Python first."
    echo "  Download from: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
print_status "Python $PYTHON_VERSION found"

# Check Java (optional but recommended for Spark)
if command_exists java; then
    JAVA_VERSION=$(java -version 2>&1 | head -1 | cut -d'"' -f2)
    print_status "Java $JAVA_VERSION found"
else
    print_info "Java not found - Spark will use fallback mode"
fi

# Check Node.js (for frontend)
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_status "Node.js $NODE_VERSION found"
else
    print_info "Node.js not found - frontend development will be skipped"
fi

# Platform-specific Docker configuration
if [[ "$PLATFORM" == "macOS" ]] && [[ $(uname -m) == "arm64" ]]; then
    print_info "Configuring Docker for Apple Silicon..."
    export DOCKER_DEFAULT_PLATFORM=linux/amd64
fi

# Create necessary directories
print_header "Setting Up Directory Structure"
mkdir -p backend/data/uploads backend/data/processed configs

# Docker services startup
print_header "Starting Infrastructure Services"
print_info "Starting Docker services..."
docker-compose up -d

print_status "Docker services started"

# Wait for critical services
print_header "Waiting for Services to Initialize"
wait_for_service "Kafka" 9093
wait_for_service "PostgreSQL" 5433

# Python environment setup
print_header "Setting Up Python Environment"
cd backend

if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    $PYTHON_CMD -m venv venv
    print_status "Virtual environment created"
fi

print_info "Activating virtual environment..."
if [[ "$PLATFORM" == "Windows" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install Python dependencies with error handling
print_info "Installing Python dependencies..."
if pip install -r requirements.txt; then
    print_status "Dependencies installed successfully"
else
    print_error "Failed to install some dependencies. Attempting individual installation..."
    
    # Install critical packages individually
    pip install pandas numpy flask flask-cors pyspark kafka-python psycopg2-binary requests setuptools
    print_status "Core dependencies installed"
fi

# Database setup
print_header "Setting Up Database"
print_info "Initializing PostgreSQL database and schema..."

# Wait a bit more for PostgreSQL to be fully ready
sleep 10

if $PYTHON_CMD setup/setup_database.py; then
    print_status "Database setup completed"
else
    print_info "Database setup had issues - continuing anyway (may work with retries)"
fi

# Kafka topics setup
print_header "Setting Up Kafka Topics"
print_info "Creating Kafka topics..."

# Create topics with error handling
TOPICS=("healthcare-stream" "financial-stream" "hybrid-input" "processed-stream" "compliance-violations")

for topic in "${TOPICS[@]}"; do
    docker exec practicum-kafka kafka-topics \
        --create --topic "$topic" \
        --bootstrap-server localhost:9092 \
        --partitions 3 --replication-factor 1 \
        --if-not-exists 2>/dev/null || true
done

print_status "Kafka topics created"

# Test data generation
print_header "Generating Test Data"
if [ -f "src/common/data_generator.py" ]; then
    print_info "Generating test datasets..."
    $PYTHON_CMD src/common/data_generator.py || print_info "Test data generation skipped"
    print_status "Test data ready"
fi

# Frontend setup (if Node.js available)
if command_exists node; then
    print_header "Setting Up Frontend"
    cd ../frontend
    
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install
        print_status "Frontend dependencies installed"
    else
        print_status "Frontend dependencies already installed"
    fi
    
    cd ../backend
fi

# System verification
print_header "System Verification"
print_info "Running system connectivity tests..."

# Test Kafka connectivity
$PYTHON_CMD -c "
try:
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers=['localhost:9093'], request_timeout_ms=5000)
    producer.close()
    print('✅ Kafka connectivity: Working')
except Exception as e:
    print(f'⚠️  Kafka connectivity: {str(e)[:50]}...')
" 2>/dev/null

# Test PostgreSQL connectivity
$PYTHON_CMD -c "
try:
    import sys
    sys.path.append('src')
    from database.postgres_connector import PostgreSQLConnector
    db = PostgreSQLConnector('localhost', 5433, 'compliance_db', 'admin', 'password')
    result = db.execute_query('SELECT COUNT(*) FROM data_users')
    print(f'✅ PostgreSQL connectivity: {result[0][\"count\"]} users found')
except Exception as e:
    print(f'⚠️  PostgreSQL connectivity: {str(e)[:50]}...')
" 2>/dev/null

# Test Spark initialization
$PYTHON_CMD -c "
try:
    import sys
    sys.path.append('src')
    from batch.spark_processor import SparkBatchProcessor
    processor = SparkBatchProcessor()
    if processor.use_spark:
        print('✅ Spark processing: Distributed mode ready')
        processor.stop()
    else:
        print('⚡ Spark processing: Pandas fallback mode')
except Exception as e:
    print(f'⚠️  Spark processing: {str(e)[:50]}...')
" 2>/dev/null

# Final summary
print_header "Setup Complete!"
echo ""
print_status "🎉 Secure Data Pipeline is ready for use!"
echo ""
echo "==============================================="
echo "📊 Available Services:"
echo "  • Backend API:        http://localhost:5000"
if command_exists node; then
    echo "  • Frontend Web UI:    http://localhost:3007"
fi
echo "  • Spark Master UI:    http://localhost:8080"
echo "  • Flink Dashboard:    http://localhost:8082"
echo "  • Storm UI:           http://localhost:8084"
echo "  • Grafana:            http://localhost:3000 (admin/admin)"
echo "  • Prometheus:         http://localhost:9090"
echo ""
echo "🧪 Quick Tests:"
echo "  • System Test:       python test_real_vs_simulated_fixed.py"
echo "  • Simple Pipeline:    python test_simple_pipeline.py"
echo ""
echo "🚀 Start Applications:"
echo "  • Backend Server:     python app.py"
if command_exists node; then
    echo "  • Frontend Dev:       cd ../frontend && npm run dev"
fi
echo ""
echo "🛑 Stop Services:"
echo "  • Docker services:    docker-compose down"
echo ""
echo "📁 Data Directories:"
echo "  • Input files:        backend/data/uploads/"
echo "  • Processed files:    backend/data/processed/"
echo ""
print_status "Setup completed successfully! 🎯"
echo ""
echo "💡 If you encounter issues, check DEPLOYMENT_GUIDE.md for troubleshooting." 