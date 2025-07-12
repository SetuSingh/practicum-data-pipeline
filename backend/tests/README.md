# Test Scripts

This directory contains comprehensive test scripts for validating the Data Integrity Monitoring System functionality.

## Files

### `test_custom_data.py`

- **Purpose**: Tests custom data type support and extensibility
- **What it tests**:
  - Multiple data formats (healthcare, financial, e-commerce, IoT)
  - Custom schema detection
  - Compliance rule application
  - Data type flexibility
- **Usage**: `python tests/test_custom_data.py`

### `test_hybrid.py`

- **Purpose**: Tests hybrid processing pipeline functionality
- **What it tests**:
  - Stream and batch processing integration
  - Flink hybrid processor
  - Real-time data handling
  - Performance metrics
- **Usage**: `python tests/test_hybrid.py`

### `test_modular_components.py`

- **Purpose**: Tests individual system components in isolation
- **What it tests**:
  - Data generators
  - Schema registry
  - Compliance engines
  - Component integration
- **Usage**: `python tests/test_modular_components.py`

### `test_postgres_integration.py`

- **Purpose**: Comprehensive PostgreSQL database integration testing
- **What it tests**:
  - Database operations
  - User management and permissions
  - Data integrity monitoring
  - Compliance violation tracking
  - Audit logging
  - Role-based access control
- **Usage**: `python tests/test_postgres_integration.py`

## Prerequisites

Before running tests:

1. **Set up the database**:

   ```bash
   python setup/setup_database.py
   ```

2. **Start required services**:

   ```bash
   docker-compose up -d
   ```

3. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

## Running Tests

### Individual Tests

```bash
# Test custom data types
python tests/test_custom_data.py

# Test hybrid processing
python tests/test_hybrid.py

# Test modular components
python tests/test_modular_components.py

# Test PostgreSQL integration
python tests/test_postgres_integration.py
```

### All Tests

```bash
# Run all tests in sequence
for test in tests/test_*.py; do
    echo "Running $test..."
    python "$test"
    echo "---"
done
```

## Test Coverage

The test suite covers:

- ✅ Data processing pipelines (batch, stream, hybrid)
- ✅ Multiple data formats and schemas
- ✅ Database operations and transactions
- ✅ User authentication and authorization
- ✅ Data integrity monitoring
- ✅ Compliance violation detection
- ✅ Audit logging and tracking
- ✅ Role-based access control
- ✅ Real-time monitoring and alerting
- ✅ Performance metrics and statistics

## Test Results

Each test provides:

- Detailed step-by-step execution logs
- Pass/fail status for each component
- Performance metrics
- Error handling validation
- System statistics

Perfect for:

- Continuous integration testing
- System validation
- Regression testing
- Performance benchmarking
