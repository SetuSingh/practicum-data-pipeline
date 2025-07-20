-- Add System Roles and Permissions for Monitoring Tools
-- This script adds roles and permissions for Prometheus and Grafana to access metrics

-- Insert system roles for monitoring
INSERT INTO core_user_roles (code, label, description, is_system_role) VALUES
('prometheus', 'Prometheus Monitor', 'System role for Prometheus metrics collection', TRUE),
('grafana', 'Grafana Dashboard', 'System role for Grafana dashboard access', TRUE),
('monitoring_admin', 'Monitoring Administrator', 'Full access to monitoring and metrics', FALSE)
ON CONFLICT (code) DO NOTHING;

-- Create system users for monitoring tools
INSERT INTO data_users (username, email, full_name, role_id, is_system_user, created_by) 
SELECT 
    'prometheus_system', 
    'prometheus@system.local', 
    'Prometheus System User',
    r.id,
    TRUE,
    (SELECT id FROM data_users WHERE username = 'admin' LIMIT 1)
FROM core_user_roles r WHERE r.code = 'prometheus'
ON CONFLICT (username) DO NOTHING;

INSERT INTO data_users (username, email, full_name, role_id, is_system_user, created_by)
SELECT 
    'grafana_system', 
    'grafana@system.local', 
    'Grafana System User',
    r.id,
    TRUE,
    (SELECT id FROM data_users WHERE username = 'admin' LIMIT 1)
FROM core_user_roles r WHERE r.code = 'grafana'
ON CONFLICT (username) DO NOTHING;

-- Add metrics permissions
INSERT INTO data_permissions (code, label, description, resource_type, action) VALUES
('metrics_read', 'Read Metrics', 'Permission to read system metrics', 'metrics', 'read'),
('metrics_admin', 'Metrics Administration', 'Full access to metrics system', 'metrics', 'admin'),
('health_read', 'Read Health Status', 'Permission to read system health', 'health', 'read'),
('monitoring_read', 'Read Monitoring Data', 'Permission to read monitoring data', 'monitoring', 'read')
ON CONFLICT (code) DO NOTHING;

-- Assign permissions to system roles
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'prometheus' AND p.code IN ('metrics_read', 'health_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'grafana' AND p.code IN ('metrics_read', 'health_read', 'monitoring_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'monitoring_admin' AND p.code IN ('metrics_admin', 'health_read', 'monitoring_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Grant file upload permissions to admin and data_analyst roles
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code IN ('admin', 'data_analyst') AND p.code IN ('file_write', 'file_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Create file permissions if they don't exist
INSERT INTO data_permissions (code, label, description, resource_type, action) VALUES
('file_read', 'Read Files', 'Permission to read files', 'file', 'read'),
('file_write', 'Write Files', 'Permission to upload and modify files', 'file', 'write'),
('file_admin', 'File Administration', 'Full access to file management', 'file', 'admin')
ON CONFLICT (code) DO NOTHING;

-- Grant file permissions to existing roles
INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'admin' AND p.code IN ('file_admin', 'metrics_admin')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'data_analyst' AND p.code IN ('file_write', 'file_read', 'metrics_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO data_role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM core_user_roles r, data_permissions p
WHERE r.code = 'viewer' AND p.code IN ('file_read', 'metrics_read', 'health_read')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Add system columns to tables if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'core_user_roles' AND column_name = 'is_system_role') THEN
        ALTER TABLE core_user_roles ADD COLUMN is_system_role BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'data_users' AND column_name = 'is_system_user') THEN
        ALTER TABLE data_users ADD COLUMN is_system_user BOOLEAN DEFAULT FALSE;
    END IF;
END $$; 