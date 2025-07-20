# Setup and Installation Scripts

This directory contains all setup, installation, and initialization scripts for the Data Integrity Monitoring System.

## Files

### `setup_database.py`

- **Purpose**: Complete PostgreSQL database initialization
- **What it does**:
  - Creates the `compliance_db` database
  - Runs schema migration from `sql/schema.up.sql`
  - Creates default user roles and permissions
  - Sets up test users for each role
  - Creates sample data for testing
  - Validates all database operations
- **Usage**: `python setup/setup_database.py`

### `quick_start.sh`

- **Purpose**: Quick system setup and dependency installation
- **What it does**:
  - Sets up Python virtual environment
  - Installs Python dependencies
  - Starts Docker services (Kafka, PostgreSQL, etc.)
  - Resolves common setup issues
- **Usage**: `chmod +x setup/quick_start.sh && ./setup/quick_start.sh`

### `start_implementation.sh`

- **Purpose**: Alternative startup script for development
- **What it does**:
  - Starts core services
  - Initializes development environment
  - Provides development-specific configurations
- **Usage**: `chmod +x setup/start_implementation.sh && ./setup/start_implementation.sh`

## Setup Process

### First-Time Setup

1. **Run quick start** (handles most dependencies):

   ```bash
   chmod +x setup/quick_start.sh
   ./setup/quick_start.sh
   ```

2. **Initialize database** (PostgreSQL setup):

   ```bash
   python setup/setup_database.py
   ```

3. **Start the system**:
   ```bash
   ./start_dashboard.sh
   ```

### Manual Setup (if needed)

1. **Create virtual environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Docker services**:

   ```bash
   docker-compose up -d
   ```

4. **Initialize database**:

   ```bash
   python setup/setup_database.py
   ```

5. **Start Flask application**:
   ```bash
   python app.py
   ```

## What Gets Set Up

### Database Structure

- 10+ PostgreSQL tables with proper relationships
- Role-based access control system
- Data integrity monitoring infrastructure
- Compliance tracking system
- Comprehensive audit logging

### Default Users

- **admin** / admin@example.com (System Administrator)
- **analyst** / analyst@example.com (Data Analyst)
- **compliance** / compliance@example.com (Compliance Officer)
- **security** / security@example.com (Security Manager)

### Default Permissions

- File operations (read, write, delete, admin)
- Record operations (read, write, delete, admin)
- System operations (read, write, admin)
- Compliance operations (read, write, admin)
- Audit operations (read, admin)

### Sample Data

- Healthcare data samples (HIPAA compliance)
- Financial data samples (GDPR compliance)
- E-commerce data samples (PCI-DSS compliance)
- IoT sensor data samples

## Troubleshooting

### Common Issues

1. **PostgreSQL connection failed**:

   ```bash
   # Check if PostgreSQL is running
   docker-compose ps
   # Restart PostgreSQL
   docker-compose restart practicum-postgres
   ```

2. **Port conflicts**:

   - PostgreSQL: 5433 (avoid conflicts with system PostgreSQL)
   - Kafka: 9093 (avoid conflicts with default Kafka)
   - Flask: 5001 (avoid conflicts with other services)

3. **Permission denied on scripts**:

   ```bash
   chmod +x setup/*.sh
   ```

4. **Python dependencies failed**:
   ```bash
   # On macOS, install PostgreSQL development libraries
   brew install postgresql
   # Then retry pip install
   pip install -r requirements.txt
   ```

### Reset Everything

If you need to completely reset the system:

```bash
# Stop all services
docker-compose down -v

# Remove virtual environment
rm -rf venv

# Run fresh setup
./setup/quick_start.sh
python setup/setup_database.py
```

## Verification

After setup, verify everything works:

1. **Test database connection**:

   ```bash
   python tests/test_postgres_integration.py
   ```

2. **Test web interface**:

   - Open http://localhost:5001
   - Try uploading a file
   - Check dashboard functionality

3. **Test data integrity**:
   ```bash
   python demos/demo_data_integrity.py
   ```

## Production Deployment

For production deployment:

1. **Configure environment variables**:

   ```bash
   export DB_HOST=your-postgres-host
   export DB_PASSWORD=secure-password
   export SECRET_KEY=your-secret-key
   ```

2. **Use production-grade database**:

   - AWS RDS PostgreSQL
   - Google Cloud SQL
   - Azure Database for PostgreSQL

3. **Set up monitoring**:

   - Prometheus metrics collection
   - Grafana dashboards
   - Alert manager configuration

4. **Configure SSL/TLS**:
   - Database connections
   - Web application HTTPS
   - API endpoint security
