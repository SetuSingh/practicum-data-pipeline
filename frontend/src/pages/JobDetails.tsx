import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  FileText, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Database,
  Shield,
  TrendingUp,
  Download
} from 'lucide-react'
import { getJobStatus, getDatabaseRecords } from '@/services/api'

export function JobDetails() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
  })

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ['records', job?.file_id],
    queryFn: () => getDatabaseRecords(job!.file_id!),
    enabled: !!job?.file_id,
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'processing':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (jobLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        <p className="text-gray-500 ml-3">Loading job details...</p>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Job not found</p>
        <button 
          onClick={() => navigate('/reports')}
          className="mt-4 text-primary-500 hover:text-primary-700"
        >
          Back to Reports
        </button>
      </div>
    )
  }

  // Use results from job.results if available, otherwise calculate from timestamps
  const processingTime = job.results?.processing_time ? 
    parseFloat(job.results.processing_time) :
    job.end_time ? 
      Math.round((new Date(job.end_time).getTime() - new Date(job.start_time).getTime()) / 1000) : 
      null

  const throughput = job.results?.throughput ? 
    parseFloat(job.results.throughput) :
    processingTime && job.records_processed ? 
      Math.round(job.records_processed / processingTime) : 
      null

  const violationsCount = job.results?.violations_found ? 
    parseInt(job.results.violations_found) :
    job.compliance_violations?.length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/reports')}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Reports</span>
            </button>
            <div className="h-6 border-l border-gray-300"></div>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 flex items-center space-x-3">
                <FileText className="w-6 h-6" />
                <span>{job.filename}</span>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(job.status)}
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(job.status)}`}>
                    {job.status}
                  </span>
                </div>
              </h1>
              <p className="text-gray-600 mt-1">
                {job.pipeline_type} processing • Started {new Date(job.start_time).toLocaleString()}
              </p>
            </div>
          </div>
          <button className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors">
            <Download className="w-4 h-4" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Database className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-600">Records Processed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {job.records_processed.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Clock className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-gray-600">Processing Time</p>
              <p className="text-2xl font-semibold text-gray-900">
                {processingTime ? `${processingTime.toFixed(3)}s` : '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <TrendingUp className="w-8 h-8 text-purple-500" />
            <div>
              <p className="text-sm text-gray-600">Throughput</p>
              <p className="text-2xl font-semibold text-gray-900">
                {throughput ? `${Math.round(throughput)}/s` : '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Shield className="w-8 h-8 text-orange-500" />
            <div>
              <p className="text-sm text-gray-600">Violations</p>
              <p className="text-2xl font-semibold text-gray-900">
                {violationsCount.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Job Results */}
      {job.results && Object.keys(job.results).length > 0 && (
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Results</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(job.results).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 capitalize">
                  {key.replace(/_/g, ' ')}
                </p>
                {key === 'compliance_details' && Array.isArray(value) ? (
                  <div className="text-sm text-gray-900">
                    {value.slice(0, 3).map((detail, idx) => (
                      <div key={idx} className="mb-1">
                        <span className="font-medium">{detail.type}:</span> {detail.field} 
                        <span className="text-gray-600"> ({detail.severity})</span>
                      </div>
                    ))}
                    {value.length > 3 && (
                      <p className="text-gray-500 text-xs mt-2">
                        +{value.length - 3} more violations
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-lg font-medium text-gray-900">
                    {typeof value === 'number' ? value.toLocaleString() : 
                     typeof value === 'object' && value !== null ? 
                       Array.isArray(value) ? 
                         `${value.length} items` : 
                         Object.keys(value).length > 0 ? 
                           `${Object.keys(value).length} entries` : 
                           'No data' :
                       String(value)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compliance Violations */}
      {job.compliance_violations && job.compliance_violations.length > 0 && (
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Compliance Violations</h3>
          <div className="space-y-3">
            {job.compliance_violations.map((violation, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border-l-4 ${
                  violation.severity === 'critical' ? 'border-red-500 bg-red-50' :
                  violation.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                  violation.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                  'border-blue-500 bg-blue-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {violation.violation_type}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {violation.description}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      Field: {violation.field_name}
                    </p>
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    violation.severity === 'critical' ? 'bg-red-200 text-red-800' :
                    violation.severity === 'high' ? 'bg-orange-200 text-orange-800' :
                    violation.severity === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                    'bg-blue-200 text-blue-800'
                  }`}>
                    {violation.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Records */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Records</h3>
        <div className="overflow-x-auto">
          {recordsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading records...</p>
            </div>
          ) : records?.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No records found</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Record ID</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Row Number</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Has PII</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Violations</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Compliance Score</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-700">Created</th>
                </tr>
              </thead>
              <tbody>
                {records?.slice(0, 100).map((record) => (
                  <tr key={record.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <span className="text-sm font-mono text-gray-600">
                        {record.record_id?.substring(0, 8)}...
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">{record.row_number}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        record.has_pii ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {record.has_pii ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        record.has_violations ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {record.has_violations ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">
                        {record.compliance_score ? (record.compliance_score * 100).toFixed(1) + '%' : '-'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">
                        {new Date(record.created_at).toLocaleString()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {records && records.length > 100 && (
            <div className="text-center py-4 text-sm text-gray-500">
              Showing first 100 of {records.length.toLocaleString()} records
            </div>
          )}
        </div>
      </div>

      {/* Error Details */}
      {job.error && (
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Error Details</h3>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-mono text-sm">{job.error}</p>
          </div>
        </div>
      )}
    </div>
  )
} 