#!/bin/bash

echo "Starting Secure Data Pipeline..."
echo "==================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Set Python command
PYTHON_CMD="python3"
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✅ Dependencies check passed"
echo ""

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi

echo ""
echo "🎯 Choose how to start:"
echo ""
echo "1. Frontend only:  cd frontend && npm install && npm run dev"
echo "2. Backend only:   cd backend && source venv/bin/activate && pip install -r requirements.txt && python app.py"
echo "3. Both manually:  Run commands above in separate terminals"
echo ""
echo "Frontend: http://localhost:3007"
echo "Backend:  http://localhost:5001"
echo ""
echo "This script completed setup. Choose your preferred startup method above." 