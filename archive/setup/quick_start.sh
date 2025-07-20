#!/bin/bash

# Quick Start Script for Secure Data Pipeline Research
# Sets up everything for 2-3 day implementation

echo "🚀 Quick Start - Secure Data Pipeline Research"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

print_status "Docker is running"

# Setup Python environment
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
fi

print_info "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt
print_status "Dependencies installed"

# Create necessary directories
mkdir -p data configs/prometheus

# Create Prometheus config
cat > configs/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

print_status "Prometheus config created"

# Start Docker services
print_info "Starting Docker services..."
docker-compose up -d

print_status "Docker services started"

# Wait for services to be ready
print_info "Waiting for services to start (30 seconds)..."
sleep 30

# Generate test data
print_info "Generating test data..."
python src/common/data_generator.py
print_status "Test data generated"

# Create Kafka topics
print_info "Creating Kafka topics..."
docker exec practicum-kafka kafka-topics --create --topic healthcare-stream --bootstrap-server localhost:9093 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic may already exist"
docker exec practicum-kafka kafka-topics --create --topic financial-stream --bootstrap-server localhost:9093 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic may already exist"
docker exec practicum-kafka kafka-topics --create --topic hybrid-input --bootstrap-server localhost:9093 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic may already exist"
docker exec practicum-kafka kafka-topics --create --topic processed-stream --bootstrap-server localhost:9093 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic may already exist"
docker exec practicum-kafka kafka-topics --create --topic compliance-violations --bootstrap-server localhost:9093 --partitions 3 --replication-factor 1 2>/dev/null || echo "Topic may already exist"

print_status "Kafka topics created"

echo ""
print_status "🎉 Setup Complete!"
echo ""
echo "==============================================="
echo "📊 Available Services:"
echo "  • Spark Master UI:    http://localhost:8080"
echo "  • Storm UI:           http://localhost:8084"
echo "  • Flink Dashboard:    http://localhost:8082"
echo "  • Grafana:            http://localhost:3000 (admin/admin)"
echo "  • Prometheus:         http://localhost:9090"
echo ""
echo "🔧 Updated for M3 Pro compatibility:"
echo "  • Kafka (Practicum):  localhost:9093"
echo "  • PostgreSQL:         localhost:5433"
echo "  • Zookeeper:          localhost:2182"
echo ""
echo "🔬 Testing the Pipelines:"
echo ""
echo "1. Test Batch Processing (Spark):"
echo "   python src/batch/spark_processor.py"
echo ""
echo "2. Test Stream Processing (Storm simulation):"
echo "   # Terminal 1 - Start consumer"
echo "   python src/stream/storm_processor.py --mode consumer"
echo "   # Terminal 2 - Generate stream data"
echo "   python src/stream/storm_processor.py --mode producer --rate 50"
echo ""
echo "3. Test Hybrid Processing (Flink):"
echo "   # Terminal 1 - Start hybrid processor"
echo "   python src/hybrid/flink_processor.py"
echo "   # Terminal 2 - Send test data"
echo "   python test_hybrid.py"
echo ""
echo "📈 Research Questions Testing:"
echo "  RQ1: Compare batch vs stream by running both and measuring:"
echo "       - Processing latency"
echo "       - Violation detection rate"
echo "       - Resource usage"
echo ""
echo "  RQ2: Test anonymization techniques by modifying methods in:"
echo "       - src/batch/spark_processor.py (anonymize_data method)"
echo "       - src/stream/storm_processor.py (anonymize_realtime method)"
echo ""
echo "  RQ3: Test hybrid routing by monitoring Flink decisions:"
echo "       - Stream vs batch routing ratios"
echo "       - Processing efficiency"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
echo "📝 Check data/ directory for generated datasets and results" 