import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { uploadFile } from '@/services/api'

interface FileUploaderProps {
  onUploadSuccess?: (jobId: string) => void
}

export function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [pipelineType, setPipelineType] = useState('batch')
  const [userRole, setUserRole] = useState('admin')
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: ({ file, pipeline, role }: { file: File; pipeline: string; role: string }) =>
      uploadFile(file, pipeline, role),
    onSuccess: (data) => {
      toast.success(`File uploaded successfully! Job ID: ${data.job_id}`)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
      onUploadSuccess?.(data.job_id)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Upload failed')
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
        uploadMutation.mutate({ file, pipeline: pipelineType, role: userRole })
      }
    },
  })

  return (
    <div className="glass-card rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Upload Data File
      </h3>

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
            <option value="hybrid">Hybrid Processing</option>
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
            disabled={uploadMutation.isPending}
          >
            <option value="admin">Admin</option>
            <option value="analyst">Data Analyst</option>
            <option value="user">Regular User</option>
          </select>
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