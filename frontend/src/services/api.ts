import axios from 'axios'
import type { 
  SystemStatus, 
  ProcessingJob, 
  DataFile, 
  User, 
  AuditLogEntry, 
  IntegrityStatus, 
  DatabaseStatistics,
  ComplianceViolation,
  AnonymizationParameters
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// System Status
export const getSystemStatus = async (): Promise<SystemStatus> => {
  const response = await api.get('/status')
  return response.data
}

// File Upload
export const uploadFile = async (
  file: File, 
  pipelineType: string = 'batch', 
  userRole: string = 'admin',
  anonymizationParams?: AnonymizationParameters
): Promise<{ job_id: string; message: string }> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('pipeline', pipelineType)
  formData.append('user_role', userRole)
  
  // Add anonymization parameters if provided
  if (anonymizationParams) {
    formData.append('anonymization_technique', anonymizationParams.anonymization_technique)
    if (anonymizationParams.k_value !== undefined) {
      formData.append('k_value', anonymizationParams.k_value.toString())
    }
    if (anonymizationParams.epsilon !== undefined) {
      formData.append('epsilon', anonymizationParams.epsilon.toString())
    }
    if (anonymizationParams.key_size !== undefined) {
      formData.append('key_size', anonymizationParams.key_size.toString())
    }
  }
  
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

// Processing Jobs
export const getJobs = async (): Promise<ProcessingJob[]> => {
  const response = await api.get('/jobs')
  return response.data.jobs
}

export const getJobStatus = async (jobId: string): Promise<ProcessingJob> => {
  const response = await api.get(`/jobs/${jobId}`)
  return response.data
}

// Sample Data Generation
export const generateSampleData = async (dataType: string): Promise<{ filename: string; message: string }> => {
  const response = await api.post('/generate-sample', { data_type: dataType })
  return response.data
}

// Schemas
export const getSchemas = async (): Promise<Record<string, any>> => {
  const response = await api.get('/schemas')
  return response.data.schemas
}

// Data Integrity
export const getIntegrityStatus = async (): Promise<IntegrityStatus> => {
  const response = await api.get('/integrity/status')
  return response.data.data
}

export const getChangeHistory = async (): Promise<any[]> => {
  const response = await api.get('/integrity/changes')
  return response.data.data
}

export const createBaseline = async (): Promise<{ message: string }> => {
  const response = await api.post('/integrity/baseline')
  return response.data
}

export const checkIntegrity = async (): Promise<{ message: string; results: any }> => {
  const response = await api.post('/integrity/check')
  return response.data
}

// Database Operations
export const getDatabaseFiles = async (): Promise<DataFile[]> => {
  const response = await api.get('/database/files')
  return response.data.files
}

export const getDatabaseRecords = async (fileId: string): Promise<any[]> => {
  const response = await api.get(`/database/records/${fileId}`)
  return response.data.records
}

export const getComplianceViolations = async (): Promise<ComplianceViolation[]> => {
  const response = await api.get('/database/violations')
  return response.data.violations
}

export const getAuditLog = async (): Promise<AuditLogEntry[]> => {
  const response = await api.get('/database/audit-log')
  return response.data.audit_log
}

export const getDatabaseStatistics = async (): Promise<DatabaseStatistics> => {
  const response = await api.get('/database/statistics')
  return response.data
}

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('/users')
  return response.data.users
}

export default api 