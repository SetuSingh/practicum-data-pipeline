import axios from 'axios'
import type { SystemStatus, ProcessingJob, DataFile, DatabaseRecord, AuditLogEntry, AnonymizationParameters } from '@/types'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: 'http://localhost:5001/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// System Status
export const getSystemStatus = async (): Promise<SystemStatus> => {
  const response = await api.get('/status')
  return response.data
}

// Jobs
export const getJobs = async (): Promise<ProcessingJob[]> => {
  const response = await api.get('/jobs')
  return response.data
}

export const getJobStatus = async (jobId: string): Promise<ProcessingJob> => {
  const response = await api.get(`/jobs/${jobId}`)
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

// Database Operations
export const getDatabaseFiles = async (): Promise<DataFile[]> => {
  const response = await api.get('/database/files')
  return response.data
}

export const getDatabaseRecords = async (fileId: string): Promise<DatabaseRecord[]> => {
  const response = await api.get(`/database/records/${fileId}`)
  // Handle both array and object with records property
  if (Array.isArray(response.data)) {
    return response.data
  } else if (response.data && response.data.records) {
    return response.data.records
  }
  return []
}

export const getDatabaseStatistics = async () => {
  const response = await api.get('/database/statistics')
  return response.data
}

// Audit Operations
export const getAuditLog = async (): Promise<AuditLogEntry[]> => {
  const response = await api.get('/database/audit')
  return response.data
}

// User Management
export interface UserRole {
  id: number
  code: string
  label: string
  description?: string
  permissions?: UserPermission[]
}

export interface UserPermission {
  permission_code: string
  permission_label: string
  resource_type: string
  action: string
}

export interface User {
  id: string
  username: string
  full_name?: string
  email?: string
  role_code: string
  role_label: string
}

// Get available user roles with permissions
export const getUserRoles = async (): Promise<UserRole[]> => {
  const response = await api.get('/roles')
  return response.data.roles
}

// Get available users
export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('/users')
  return response.data.users
}

// Get user permissions
export const getUserPermissions = async (userId: string): Promise<UserPermission[]> => {
  const response = await api.get(`/user-permissions/${userId}`)
  return response.data.permissions
}

export default api 