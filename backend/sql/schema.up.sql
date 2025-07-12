-- ============================================================================
-- Data Integrity Monitoring System - PostgreSQL Schema
-- ============================================================================
-- This schema implements:
-- 1. Role-based access control (RBAC)
-- 2. Data file and processing tracking
-- 3. Data integrity monitoring with audit trails
-- 4. Comprehensive audit columns for compliance
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. USER ROLES AND PERMISSIONS SYSTEM
-- ============================================================================

-- Core user roles table
CREATE TABLE core_user_roles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID
);

-- Permissions table
CREATE TABLE data_permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) NOT NULL, -- 'file', 'record', 'system', etc.
    action VARCHAR(50) NOT NULL, -- 'read', 'write', 'delete', 'admin'
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID
);

-- Role permissions mapping
CREATE TABLE data_role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES core_user_roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES data_permissions(id) ON DELETE CASCADE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    
    UNIQUE(role_id, permission_id)
);

-- Users table
CREATE TABLE data_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    password_hash VARCHAR(255), -- For authentication
    role_id INTEGER NOT NULL REFERENCES core_user_roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID
);

-- ============================================================================
-- 2. DATA FILE TRACKING SYSTEM
-- ============================================================================

-- Data file types
CREATE TABLE data_file_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    description TEXT,
    schema_definition JSONB, -- Store expected schema
    compliance_rules JSONB, -- Store compliance requirements
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID
);

-- Original data files
CREATE TABLE data_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64) NOT NULL, -- SHA256 hash of entire file
    mime_type VARCHAR(100),
    file_type_id INTEGER REFERENCES data_file_types(id),
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'uploaded', -- 'uploaded', 'processing', 'processed', 'failed'
    total_records INTEGER,
    valid_records INTEGER,
    invalid_records INTEGER,
    
    -- Compliance tracking
    compliance_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'compliant', 'violations'
    compliance_report JSONB,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES data_users(id)
);

-- Data processing jobs
CREATE TABLE data_processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255) NOT NULL,
    file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    pipeline_type VARCHAR(50) NOT NULL, -- 'batch', 'stream', 'hybrid'
    processor_config JSONB,
    
    -- Job status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Performance metrics
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    processing_time_seconds INTEGER,
    records_processed INTEGER,
    throughput_per_second DECIMAL(10,2),
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES data_users(id)
);

-- ============================================================================
-- 3. DATA RECORDS AND INTEGRITY MONITORING
-- ============================================================================

-- Individual data records (for integrity monitoring)
CREATE TABLE data_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    job_id UUID REFERENCES data_processing_jobs(id),
    
    -- Record identification
    record_id VARCHAR(255) NOT NULL, -- Business key from the data
    record_hash VARCHAR(64) NOT NULL, -- SHA256 hash of record content
    row_number INTEGER,
    
    -- Record content
    original_data JSONB NOT NULL, -- Original record data
    processed_data JSONB, -- Processed/transformed data
    
    -- Compliance tracking
    has_pii BOOLEAN DEFAULT FALSE,
    has_violations BOOLEAN DEFAULT FALSE,
    violation_types TEXT[],
    compliance_score DECIMAL(5,2),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'archived', 'deleted'
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES data_users(id),
    
    UNIQUE(file_id, record_id)
);

-- Data record changes audit trail
CREATE TABLE data_record_changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    record_id UUID NOT NULL REFERENCES data_records(id) ON DELETE CASCADE,
    
    -- Change details
    change_type VARCHAR(50) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE', 'RESTORE'
    changed_fields JSONB NOT NULL, -- {"field": {"old": "value1", "new": "value2"}}
    
    -- Change metadata
    change_reason VARCHAR(255),
    change_source VARCHAR(100) NOT NULL, -- 'user', 'system', 'api', 'batch_job'
    old_hash VARCHAR(64),
    new_hash VARCHAR(64),
    
    -- Impact assessment
    compliance_impact VARCHAR(50), -- 'none', 'low', 'medium', 'high', 'critical'
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES data_users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    
    -- Prevent duplicate change records
    UNIQUE(record_id, created_at, change_type)
);

-- ============================================================================
-- 4. DATA INTEGRITY MONITORING SYSTEM
-- ============================================================================

-- Integrity baselines (for each file/dataset)
CREATE TABLE data_integrity_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    
    -- Baseline metadata
    baseline_name VARCHAR(255) NOT NULL,
    baseline_type VARCHAR(50) NOT NULL, -- 'file', 'schema', 'records'
    
    -- Hash storage
    content_hash VARCHAR(64) NOT NULL, -- Overall hash
    record_hashes JSONB, -- {"record_id": "hash", ...}
    schema_hash VARCHAR(64), -- Hash of schema structure
    
    -- Baseline stats
    total_records INTEGER,
    record_count_hash VARCHAR(64),
    column_definitions JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES data_users(id)
);

-- Integrity monitoring events
CREATE TABLE data_integrity_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES data_files(id),
    record_id UUID REFERENCES data_records(id),
    baseline_id UUID REFERENCES data_integrity_baselines(id),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL, -- 'hash_mismatch', 'schema_change', 'record_count_change', 'unauthorized_access'
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    
    -- Detection details
    expected_hash VARCHAR(64),
    actual_hash VARCHAR(64),
    affected_fields JSONB,
    change_description TEXT,
    
    -- Response tracking
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'investigating', 'resolved', 'false_positive'
    resolution_notes TEXT,
    resolved_by UUID REFERENCES data_users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id)
);

-- ============================================================================
-- 5. COMPLIANCE AND AUDIT TABLES
-- ============================================================================

-- Compliance violations
CREATE TABLE data_compliance_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES data_files(id),
    record_id UUID REFERENCES data_records(id),
    
    -- Violation details
    violation_type VARCHAR(100) NOT NULL, -- 'gdpr', 'hipaa', 'pci_dss', 'sox'
    violation_category VARCHAR(100) NOT NULL, -- 'data_exposure', 'consent_missing', 'retention_exceeded'
    severity VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    
    -- Affected data
    affected_columns TEXT[],
    affected_records_count INTEGER,
    data_classification VARCHAR(50), -- 'public', 'internal', 'confidential', 'restricted'
    
    -- Resolution tracking
    status VARCHAR(50) DEFAULT 'open',
    remediation_plan TEXT,
    resolved_by UUID REFERENCES data_users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit columns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES data_users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES data_users(id)
);

-- System audit log
CREATE TABLE system_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Action details
    action_type VARCHAR(100) NOT NULL, -- 'login', 'logout', 'file_upload', 'data_access', 'config_change'
    resource_type VARCHAR(50), -- 'file', 'record', 'user', 'system'
    resource_id UUID,
    
    -- User context
    user_id UUID REFERENCES data_users(id),
    user_role VARCHAR(50),
    session_id VARCHAR(100),
    
    -- Technical details
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_url TEXT,
    response_status INTEGER,
    
    -- Additional metadata
    details JSONB,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 6. INDEXES FOR PERFORMANCE
-- ============================================================================

-- User and role indexes
CREATE INDEX idx_data_users_role_id ON data_users(role_id);
CREATE INDEX idx_data_users_username ON data_users(username);
CREATE INDEX idx_data_users_email ON data_users(email);

-- File and processing indexes
CREATE INDEX idx_data_files_created_by ON data_files(created_by);
CREATE INDEX idx_data_files_status ON data_files(status);
CREATE INDEX idx_data_files_file_type_id ON data_files(file_type_id);
CREATE INDEX idx_data_processing_jobs_file_id ON data_processing_jobs(file_id);
CREATE INDEX idx_data_processing_jobs_status ON data_processing_jobs(status);

-- Records and changes indexes
CREATE INDEX idx_data_records_file_id ON data_records(file_id);
CREATE INDEX idx_data_records_record_id ON data_records(record_id);
CREATE INDEX idx_data_records_created_by ON data_records(created_by);
CREATE INDEX idx_data_record_changes_record_id ON data_record_changes(record_id);
CREATE INDEX idx_data_record_changes_created_at ON data_record_changes(created_at);
CREATE INDEX idx_data_record_changes_change_type ON data_record_changes(change_type);

-- Integrity monitoring indexes
CREATE INDEX idx_data_integrity_baselines_file_id ON data_integrity_baselines(file_id);
CREATE INDEX idx_data_integrity_events_file_id ON data_integrity_events(file_id);
CREATE INDEX idx_data_integrity_events_severity ON data_integrity_events(severity);
CREATE INDEX idx_data_integrity_events_status ON data_integrity_events(status);

-- Compliance indexes
CREATE INDEX idx_compliance_violations_file_id ON data_compliance_violations(file_id);
CREATE INDEX idx_compliance_violations_severity ON data_compliance_violations(severity);
CREATE INDEX idx_compliance_violations_status ON data_compliance_violations(status);

-- Audit log indexes
CREATE INDEX idx_audit_log_user_id ON system_audit_log(user_id);
CREATE INDEX idx_audit_log_action_type ON system_audit_log(action_type);
CREATE INDEX idx_audit_log_created_at ON system_audit_log(created_at);

-- ============================================================================
-- 7. TRIGGERS FOR AUDIT COLUMNS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_core_user_roles_updated_at BEFORE UPDATE ON core_user_roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_permissions_updated_at BEFORE UPDATE ON data_permissions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_users_updated_at BEFORE UPDATE ON data_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_file_types_updated_at BEFORE UPDATE ON data_file_types FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_files_updated_at BEFORE UPDATE ON data_files FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_processing_jobs_updated_at BEFORE UPDATE ON data_processing_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_records_updated_at BEFORE UPDATE ON data_records FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_integrity_baselines_updated_at BEFORE UPDATE ON data_integrity_baselines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_compliance_violations_updated_at BEFORE UPDATE ON data_compliance_violations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 8. VIEWS FOR COMMON QUERIES
-- ============================================================================

-- User permissions view
CREATE VIEW user_permissions AS
SELECT 
    u.id as user_id,
    u.username,
    u.full_name,
    r.code as role_code,
    r.label as role_label,
    p.code as permission_code,
    p.label as permission_label,
    p.resource_type,
    p.action
FROM data_users u
JOIN core_user_roles r ON u.role_id = r.id
JOIN data_role_permissions rp ON r.id = rp.role_id
JOIN data_permissions p ON rp.permission_id = p.id
WHERE u.is_active = TRUE AND r.is_active = TRUE;

-- File integrity status view
CREATE VIEW file_integrity_status AS
SELECT 
    f.id as file_id,
    f.filename,
    f.status as file_status,
    f.total_records,
    COUNT(DISTINCT ie.id) as integrity_events_count,
    COUNT(DISTINCT CASE WHEN ie.severity = 'critical' THEN ie.id END) as critical_events,
    COUNT(DISTINCT CASE WHEN ie.severity = 'high' THEN ie.id END) as high_events,
    COUNT(DISTINCT CASE WHEN ie.status = 'open' THEN ie.id END) as open_events,
    MAX(ie.created_at) as last_integrity_event
FROM data_files f
LEFT JOIN data_integrity_events ie ON f.id = ie.file_id
GROUP BY f.id, f.filename, f.status, f.total_records;

-- Data processing summary view
CREATE VIEW data_processing_summary AS
SELECT 
    f.id as file_id,
    f.filename,
    f.created_at as uploaded_at,
    u.username as uploaded_by,
    j.pipeline_type,
    j.status as processing_status,
    j.progress,
    j.processing_time_seconds,
    j.throughput_per_second,
    COUNT(DISTINCT cv.id) as compliance_violations
FROM data_files f
JOIN data_users u ON f.created_by = u.id
LEFT JOIN data_processing_jobs j ON f.id = j.file_id
LEFT JOIN data_compliance_violations cv ON f.id = cv.file_id
GROUP BY f.id, f.filename, f.created_at, u.username, j.pipeline_type, j.status, j.progress, j.processing_time_seconds, j.throughput_per_second;

-- ============================================================================
-- 9. INITIAL DATA SETUP
-- ============================================================================

-- Insert default user roles
INSERT INTO core_user_roles (code, label, description) VALUES
('admin', 'System Administrator', 'Full system access and configuration'),
('data_analyst', 'Data Analyst', 'View and analyze data, limited modification'),
('compliance_officer', 'Compliance Officer', 'Monitor compliance and audit trails'),
('security_manager', 'Security Manager', 'Security oversight and incident response'),
('viewer', 'Viewer', 'Read-only access to data and reports'),
('data_engineer', 'Data Engineer', 'Manage data pipelines and processing');

-- Insert default permissions
INSERT INTO data_permissions (code, label, description, resource_type, action) VALUES
-- File permissions
('file_read', 'Read Files', 'View file contents and metadata', 'file', 'read'),
('file_write', 'Write Files', 'Upload and modify files', 'file', 'write'),
('file_delete', 'Delete Files', 'Remove files from system', 'file', 'delete'),
('file_admin', 'Administer Files', 'Full file management', 'file', 'admin'),

-- Record permissions
('record_read', 'Read Records', 'View individual records', 'record', 'read'),
('record_write', 'Write Records', 'Modify record data', 'record', 'write'),
('record_delete', 'Delete Records', 'Remove records', 'record', 'delete'),
('record_admin', 'Administer Records', 'Full record management', 'record', 'admin'),

-- System permissions
('system_read', 'Read System', 'View system status and metrics', 'system', 'read'),
('system_write', 'Write System', 'Modify system configuration', 'system', 'write'),
('system_admin', 'Administer System', 'Full system administration', 'system', 'admin'),

-- Compliance permissions
('compliance_read', 'Read Compliance', 'View compliance reports', 'compliance', 'read'),
('compliance_write', 'Write Compliance', 'Manage compliance settings', 'compliance', 'write'),
('compliance_admin', 'Administer Compliance', 'Full compliance management', 'compliance', 'admin'),

-- Audit permissions
('audit_read', 'Read Audit', 'View audit logs', 'audit', 'read'),
('audit_admin', 'Administer Audit', 'Manage audit configuration', 'audit', 'admin');

-- Insert default file types
INSERT INTO data_file_types (code, label, description, schema_definition, compliance_rules) VALUES
('healthcare', 'Healthcare Data', 'Medical records and health information', 
 '{"required_columns": ["patient_id", "diagnosis"], "pii_columns": ["patient_name", "ssn", "dob"]}',
 '{"regulations": ["HIPAA"], "encryption_required": true, "retention_years": 7}'),
 
('financial', 'Financial Data', 'Financial transactions and account information',
 '{"required_columns": ["account_number", "transaction_amount"], "pii_columns": ["customer_name", "ssn"]}',
 '{"regulations": ["GDPR", "SOX"], "encryption_required": true, "retention_years": 7}'),
 
('ecommerce', 'E-commerce Data', 'Online shopping and customer data',
 '{"required_columns": ["customer_id", "order_id"], "pii_columns": ["customer_name", "email", "address"]}',
 '{"regulations": ["GDPR", "PCI_DSS"], "encryption_required": true, "retention_years": 3}'),
 
('iot', 'IoT Sensor Data', 'Internet of Things device data',
 '{"required_columns": ["device_id", "timestamp", "sensor_value"], "pii_columns": ["location", "user_id"]}',
 '{"regulations": ["GDPR"], "encryption_required": false, "retention_years": 2}');

-- Set up default role permissions (Admin gets everything)
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'admin';

-- Data Analyst permissions
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'data_analyst' 
AND p.code IN ('file_read', 'file_write', 'record_read', 'record_write', 'system_read', 'compliance_read');

-- Compliance Officer permissions
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'compliance_officer' 
AND p.code IN ('file_read', 'record_read', 'system_read', 'compliance_read', 'compliance_write', 'audit_read');

-- Security Manager permissions
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'security_manager' 
AND p.code IN ('file_read', 'record_read', 'system_read', 'system_write', 'compliance_read', 'audit_read', 'audit_admin');

-- Viewer permissions
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'viewer' 
AND p.code IN ('file_read', 'record_read', 'system_read', 'compliance_read');

-- Data Engineer permissions
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r 
CROSS JOIN data_permissions p 
WHERE r.code = 'data_engineer' 
AND p.code IN ('file_read', 'file_write', 'record_read', 'record_write', 'system_read', 'system_write');

-- ============================================================================
-- 10. COMMENTS AND DOCUMENTATION
-- ============================================================================

-- Add table comments
COMMENT ON TABLE core_user_roles IS 'System user roles for role-based access control';
COMMENT ON TABLE data_permissions IS 'System permissions that can be assigned to roles';
COMMENT ON TABLE data_role_permissions IS 'Mapping between roles and permissions';
COMMENT ON TABLE data_users IS 'System users with role assignments';
COMMENT ON TABLE data_file_types IS 'Supported data file types with schemas and compliance rules';
COMMENT ON TABLE data_files IS 'Uploaded data files with processing status and metadata';
COMMENT ON TABLE data_processing_jobs IS 'Data processing jobs with performance metrics';
COMMENT ON TABLE data_records IS 'Individual data records with integrity hashes';
COMMENT ON TABLE data_record_changes IS 'Audit trail for all data record changes';
COMMENT ON TABLE data_integrity_baselines IS 'Baseline hashes for integrity monitoring';
COMMENT ON TABLE data_integrity_events IS 'Detected integrity violations and security events';
COMMENT ON TABLE data_compliance_violations IS 'Compliance violations and remediation tracking';
COMMENT ON TABLE system_audit_log IS 'Comprehensive system audit log';

-- Add column comments for important fields
COMMENT ON COLUMN data_records.record_hash IS 'SHA256 hash of record content for integrity monitoring';
COMMENT ON COLUMN data_record_changes.changed_fields IS 'JSONB storing old and new values for changed fields';
COMMENT ON COLUMN data_integrity_events.severity IS 'Severity level: low, medium, high, critical';
COMMENT ON COLUMN data_files.file_hash IS 'SHA256 hash of entire file for integrity verification';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================ 