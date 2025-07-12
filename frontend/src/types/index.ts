// API Response Types
export interface SystemStatus {
  status: string
  files: {
    uploaded: number
    processed: number
  }
  jobs: {
    total: number
    active: number
    completed: number
  }
  system: {
    uptime: string
    response_time: string
  }
}

export interface ProcessingJob {
  job_id: string
  filename: string
  pipeline_type: 'batch' | 'stream' | 'hybrid'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  start_time: string
  end_time?: string
  results: Record<string, any>
  error?: string
  user_id: string
  file_id?: string
  records_processed: number
  compliance_violations: ComplianceViolation[]
}

export interface ComplianceViolation {
  id: string
  file_id: string
  field_name: string
  violation_type: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  detected_at: string
}

export interface DataFile {
  id: string
  filename: string
  original_filename: string
  file_path: string
  file_size: number
  file_hash: string
  mime_type: string
  file_type_code: string
  created_at: string
  created_by: string
  is_processed: boolean
}

export interface User {
  id: string
  username: string
  email: string
  role: string
  created_at: string
}

export interface AuditLogEntry {
  id: string
  action_type: string
  resource_type: string
  resource_id: string
  user_id: string
  timestamp: string
  ip_address: string
  user_agent: string
  details: Record<string, any>
}

export interface IntegrityStatus {
  overall_status: 'healthy' | 'warning' | 'critical'
  last_check: string
  files_checked: number
  issues_found: number
  baseline_exists: boolean
}

export interface DatabaseStatistics {
  total_files: number
  total_records: number
  total_violations: number
  active_users: number
  storage_used: string
}

// UI Types
export interface NavItem {
  id: string
  label: string
  href: string
  icon: any
}

export interface StatCardProps {
  title: string
  value: string | number
  icon: any
  trend?: {
    value: number
    isPositive: boolean
  }
}

export interface ChartDataPoint {
  name: string
  value: number
  date?: string
} 