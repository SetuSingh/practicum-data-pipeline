import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { uploadFile, getUserRoles } from '@/services/api'
import type { AnonymizationTechnique, AnonymizationParameters } from '@/types'

interface FileUploaderProps {
  onUploadSuccess?: (jobId: string) => void
}

export function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [pipelineType, setPipelineType] = useState('batch')
  const [userRole, setUserRole] = useState('admin')
  
  // Anonymization parameters state
  const [anonymizationTechnique, setAnonymizationTechnique] = useState<AnonymizationTechnique>('k_anonymity')
  const [kValue, setKValue] = useState(5)
  const [epsilon, setEpsilon] = useState(1.0)
  const [keySize, setKeySize] = useState(256)
  
  const queryClient = useQueryClient()

  // Fetch user roles from database
  const { data: roles, isLoading: rolesLoading } = useQuery({
    queryKey: ['user-roles'],
    queryFn: getUserRoles,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const uploadMutation = useMutation({
    mutationFn: ({ 
      file, 
      pipeline, 
      role, 
      anonymizationParams 
    }: { 
      file: File; 
      pipeline: string; 
      role: string; 
      anonymizationParams: AnonymizationParameters 
    }) =>
      uploadFile(file, pipeline, role, anonymizationParams),
    onSuccess: (data) => {
      toast.success(`File uploaded successfully! Job ID: ${data.job_id}`)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
      onUploadSuccess?.(data.job_id)
    },
    onError: (error: any) => {
      console.log('Upload error:', error)
      
      // Handle 403 Forbidden specifically
      if (error.response?.status === 403) {
        const errorData = error.response.data
        toast.error(
          `🚫 Access Denied: ${errorData.message || 'Insufficient permissions'}`,
          {
            duration: 6000,
            style: {
              background: '#FEE2E2',
              color: '#DC2626',
              border: '1px solid #FCA5A5'
            }
          }
        )
      } else {
        // Handle other errors
        toast.error(error.response?.data?.error || 'Upload failed')
      }
    },
  })

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
    },
    maxSize: 16 * 1024 * 1024, // 16MB
    multiple: false,
    onDrop: (files) => {
      if (files.length > 0) {
        const file = files[0]
        const anonymizationParams: AnonymizationParameters = {
          anonymization_technique: anonymizationTechnique,
          k_value: anonymizationTechnique === 'k_anonymity' ? kValue : undefined,
          epsilon: anonymizationTechnique === 'differential_privacy' ? epsilon : undefined,
          key_size: anonymizationTechnique === 'tokenization' ? keySize : undefined,
        }
        uploadMutation.mutate({ file, pipeline: pipelineType, role: userRole, anonymizationParams })
      }
    },
  })

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Upload Data File
        </h3>
        <div className="text-xs text-gray-500">
          Testing RBAC: Try uploading with different roles
        </div>
      </div>

      {/* Pipeline and Role Selection */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Pipeline Type
          </label>
          <select
            value={pipelineType}
            onChange={(e) => setPipelineType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={uploadMutation.isPending}
          >
            <option value="batch">Batch Processing</option>
            <option value="stream">Stream Processing</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            User Role
          </label>
          <select
            value={userRole}
            onChange={(e) => setUserRole(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={uploadMutation.isPending || rolesLoading}
          >
            {rolesLoading ? (
              <option value="">Loading roles...</option>
            ) : roles && roles.length > 0 ? (
              roles.map((role) => (
                <option key={role.code} value={role.code}>
                  {role.label}
                </option>
              ))
            ) : (
              <>
                <option value="admin">Admin</option>
                <option value="data_analyst">Data Analyst</option>
                <option value="viewer">Regular User</option>
              </>
            )}
          </select>
        </div>
      </div>

      {/* Role Permission Info */}
      {roles && (
        <div className="mb-6 p-3 bg-gray-50 rounded-lg border">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium text-gray-700">Selected Role: </span>
              <span className={`text-sm px-2 py-1 rounded-md ${
                userRole === 'admin' ? 'bg-green-100 text-green-800' :
                userRole === 'viewer' ? 'bg-red-100 text-red-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {roles.find(r => r.code === userRole)?.label || userRole}
              </span>
            </div>
            {userRole === 'viewer' && (
              <div className="flex items-center text-sm text-red-600">
                <span className="mr-1">⚠️</span>
                <span>Read-only access</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Anonymization Configuration */}
      <div className="border-t border-gray-200 pt-6 mb-6">
        <h4 className="text-md font-medium text-gray-900 mb-4">
          Anonymization Configuration
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Anonymization Technique
            </label>
            <select
              value={anonymizationTechnique}
              onChange={(e) => setAnonymizationTechnique(e.target.value as AnonymizationTechnique)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={uploadMutation.isPending}
            >
              <option value="k_anonymity">K-Anonymity</option>
              <option value="differential_privacy">Differential Privacy</option>
              <option value="tokenization">Tokenization</option>
            </select>
          </div>

          {/* K-Anonymity Parameters */}
          {anonymizationTechnique === 'k_anonymity' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                K Value
              </label>
              <select
                value={kValue}
                onChange={(e) => setKValue(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={uploadMutation.isPending}
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Minimum group size for anonymization
              </p>
            </div>
          )}

          {/* Differential Privacy Parameters */}
          {anonymizationTechnique === 'differential_privacy' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Epsilon (ε)
              </label>
              <select
                value={epsilon}
                onChange={(e) => setEpsilon(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={uploadMutation.isPending}
              >
                <option value={0.1}>0.1</option>
                <option value={0.5}>0.5</option>
                <option value={1.0}>1.0</option>
                <option value={2.0}>2.0</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Privacy budget (lower = more private)
              </p>
            </div>
          )}

          {/* Tokenization Parameters */}
          {anonymizationTechnique === 'tokenization' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Key Size (bits)
              </label>
              <select
                value={keySize}
                onChange={(e) => setKeySize(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={uploadMutation.isPending}
              >
                <option value={128}>128</option>
                <option value={256}>256</option>
                <option value={512}>512</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Token encryption key length
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        } ${uploadMutation.isPending ? 'pointer-events-none opacity-50' : ''}`}
      >
        <input {...getInputProps()} />
        
        {uploadMutation.isPending ? (
          <div className="flex flex-col items-center space-y-3">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin" />
            <p className="text-gray-600 font-medium">Uploading...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-3">
            <Upload className="w-12 h-12 text-gray-400" />
            <div>
              <p className="text-gray-600 font-medium">
                {isDragActive
                  ? 'Drop the CSV file here'
                  : 'Drop a CSV file here, or click to select'}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Maximum file size: 16MB
              </p>
              {userRole === 'viewer' && (
                <p className="text-xs text-amber-600 mt-2 font-medium">
                  ⚠️ Note: Viewer role may have limited upload permissions
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Selected File Display */}
      {acceptedFiles.length > 0 && !uploadMutation.isPending && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-green-600" />
            <span className="text-sm text-green-800 font-medium">
              {acceptedFiles[0].name}
            </span>
            <span className="text-xs text-green-600">
              ({(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </div>
        </div>
      )}
    </div>
  )
} 