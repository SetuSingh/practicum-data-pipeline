#!/bin/bash

# Dashboard Startup Script
# Launches the Flask backend with full dashboard functionality

echo "🚀 Starting Secure Data Pipeline Dashboard with Backend"
echo "========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    print_info "Installing Flask dependencies..."
    pip install Flask==2.3.3 Werkzeug==2.3.7
fi

# Create data directories
mkdir -p data/uploads data/processed

print_status "Environment ready"

# Check if port 5001 is available
if lsof -i :5001 > /dev/null 2>&1; then
    print_warning "Port 5001 is already in use. Stopping existing process..."
    pkill -f "python app.py" || true
    sleep 2
fi

print_info "Starting Flask backend on http://localhost:5001"
print_info "Loading dashboard with full functionality..."

echo ""
echo "🌐 Dashboard Features:"
echo "  • Live file upload and processing"
echo "  • Real-time job status tracking"
echo "  • Auto-refreshing system metrics"
echo "  • Sample data generation"
echo "  • Multi-pipeline support (Batch/Stream/Hybrid)"
echo "  • Role-based access simulation"
echo ""

print_status "Starting server..."

# Start the Flask application
python app.py 