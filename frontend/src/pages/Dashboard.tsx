import { useQuery } from '@tanstack/react-query'
import { FileText, Database, Shield } from 'lucide-react'
import { StatCard } from '@/components/StatCard'
import { FileUploader } from '@/components/FileUploader'
import { getSystemStatus, getJobs } from '@/services/api'

export function Dashboard() {
  const { data: systemStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    refetchInterval: 3000, // Refresh every 3 seconds
  })

  const recentJobs = Array.isArray(jobs) ? jobs.slice(0, 5) : []

  return (
    <div className="space-y-8">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Files Uploaded"
          value={statusLoading ? '...' : systemStatus?.files.uploaded || 0}
          icon={FileText}
          trend={{ value: 12, isPositive: true }}
        />
        <StatCard
          title="Files Processed"
          value={statusLoading ? '...' : systemStatus?.files.processed || 0}
          icon={Database}
          trend={{ value: 8, isPositive: true }}
        />
        <StatCard
          title="Active Jobs"
          value={statusLoading ? '...' : systemStatus?.jobs.active || 0}
          icon={Database}
          trend={{ value: 3, isPositive: false }}
        />
        <StatCard
          title="System Status"
          value={statusLoading ? '...' : systemStatus?.status === 'healthy' ? 'Healthy' : 'Warning'}
          icon={Shield}
          trend={{ value: 99, isPositive: true }}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* File Upload Section */}
        <div>
          <FileUploader onUploadSuccess={(jobId) => console.log('Uploaded:', jobId)} />
        </div>

        {/* Recent Jobs */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Processing Jobs
          </h3>
          <div className="space-y-3">
            {jobsLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
                <p className="text-gray-500 mt-2">Loading jobs...</p>
              </div>
            ) : recentJobs.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No processing jobs yet</p>
                <p className="text-sm text-gray-400 mt-1">Upload a file to get started</p>
              </div>
            ) : (
              recentJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      job.status === 'completed' ? 'bg-green-500' :
                      job.status === 'processing' ? 'bg-yellow-500' :
                      job.status === 'failed' ? 'bg-red-500' :
                      'bg-gray-400'
                    }`} />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {job.filename}
                      </p>
                      <p className="text-xs text-gray-500">
                        {job.pipeline_type} • {new Date(job.start_time).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 capitalize">
                      {job.status}
                    </p>
                    <p className="text-xs text-gray-500">
                      {job.records_processed} records
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

    </div>
  )
} 