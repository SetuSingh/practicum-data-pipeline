import { useQuery } from '@tanstack/react-query'
import { FileText, Download, Filter, Eye, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getJobs } from '@/services/api'

export function Reports() {
  const navigate = useNavigate()
  
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    refetchInterval: 5000, // Refresh every 5 seconds
  })



  const handleViewJobDetails = (jobId: string) => {
    navigate(`/reports/${jobId}`)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      case 'processing':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
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

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Processing Reports</h1>
            <p className="text-gray-600 mt-1">
              View all processing jobs and their detailed reports
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors">
              <Download className="w-4 h-4" />
              <span>Export All</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
              <Filter className="w-4 h-4" />
              <span>Filter</span>
            </button>
          </div>
        </div>
      </div>

      {/* Processing Jobs Table */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          All Processing Jobs
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-700">File Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Pipeline</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Records</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Start Time</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Duration</th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobsLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
                    <p className="text-gray-500 mt-2">Loading jobs...</p>
                  </td>
                </tr>
              ) : jobs?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8">
                    <p className="text-gray-500">No processing jobs found</p>
                    <p className="text-sm text-gray-400 mt-1">Upload a file to create your first job</p>
                  </td>
                </tr>
              ) : (
                jobs?.map((job) => (
                  <tr key={job.job_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium">{job.filename}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600 capitalize">{job.pipeline_type}</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(job.status)}
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(job.status)}`}>
                          {job.status}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">
                        {job.records_processed.toLocaleString()}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">
                        {new Date(job.start_time).toLocaleString()}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">
                        {job.end_time ? 
                          `${Math.round((new Date(job.end_time).getTime() - new Date(job.start_time).getTime()) / 1000)}s` : 
                          '-'
                        }
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <button 
                        onClick={() => handleViewJobDetails(job.job_id)}
                        className="flex items-center space-x-1 text-primary-500 hover:text-primary-700 text-sm font-medium"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
} 