import { useQuery } from '@tanstack/react-query'
import { Shield, AlertTriangle, Activity, Database, Lock, Eye } from 'lucide-react'

// API functions for monitoring
const getHealthCheck = async () => {
  const response = await fetch('http://localhost:5001/api/health')
  if (!response.ok) throw new Error('Failed to fetch health data')
  return response.json()
}

const getAlerts = async () => {
  const response = await fetch('http://localhost:5001/api/alerts')
  if (!response.ok) throw new Error('Failed to fetch alerts')
  return response.json()
}

const getMetricsSummary = async () => {
  const response = await fetch('http://localhost:5001/api/metrics/summary')
  if (!response.ok) throw new Error('Failed to fetch metrics summary')
  return response.json()
}

const getEncryptionStatus = async () => {
  const response = await fetch('http://localhost:5001/api/encryption/status')
  if (!response.ok) throw new Error('Failed to fetch encryption status')
  return response.json()
}

export function Monitoring() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: getHealthCheck,
    refetchInterval: 5000,
  })

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: getAlerts,
    refetchInterval: 3000,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics-summary'],
    queryFn: getMetricsSummary,
    refetchInterval: 5000,
  })

  const { data: encryption, isLoading: encryptionLoading } = useQuery({
    queryKey: ['encryption-status'],
    queryFn: getEncryptionStatus,
    refetchInterval: 30000,
  })

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500 bg-red-50 text-red-800'
      case 'high':
        return 'border-orange-500 bg-orange-50 text-orange-800'
      case 'medium':
        return 'border-yellow-500 bg-yellow-50 text-yellow-800'
      default:
        return 'border-blue-500 bg-blue-50 text-blue-800'
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">System Monitoring</h1>
            <p className="text-gray-600 mt-1">
              Real-time security, compliance, and performance monitoring
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              health?.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              <Activity className="w-4 h-4 mr-2" />
              {healthLoading ? 'Checking...' : health?.status || 'Unknown'}
            </div>
            <button
              onClick={() => window.open('http://localhost:3000', '_blank')}
              className="inline-flex items-center px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              <Eye className="w-4 h-4 mr-2" />
              Open Grafana
            </button>
          </div>
        </div>
      </div>

      {/* Alerts Section */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <AlertTriangle className="w-5 h-5 mr-2 text-orange-500" />
          Active Alerts
        </h3>
        {alertsLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
            <p className="text-gray-500 mt-2">Loading alerts...</p>
          </div>
        ) : alerts?.alerts?.length > 0 ? (
          <div className="space-y-3">
            {alerts.alerts.map((alert: any, index: number) => (
              <div
                key={index}
                className={`p-4 rounded-lg border-l-4 ${getSeverityColor(alert.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{alert.type.replace(/_/g, ' ').toUpperCase()}</p>
                    <p className="text-sm mt-1">{alert.message}</p>
                    <p className="text-xs mt-2 opacity-75">
                      {new Date(alert.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>
                    {alert.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-green-600">
            <Shield className="w-12 h-12 mx-auto mb-4" />
            <p className="font-medium">All systems operating normally</p>
            <p className="text-sm text-gray-500 mt-1">No active alerts detected</p>
          </div>
        )}
      </div>

      {/* System Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Database Status */}
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Database className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-600">Database</p>
              <p className="text-lg font-semibold text-gray-900">
                {healthLoading ? 'Checking...' : health?.components?.database?.status || 'Unknown'}
              </p>
            </div>
          </div>
          {health?.components?.database && (
            <div className="mt-4 text-sm text-gray-600">
              <p>{health.components.database.details}</p>
            </div>
          )}
        </div>

        {/* API Server Status */}
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Activity className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-gray-600">API Server</p>
              <p className="text-lg font-semibold text-gray-900">
                {healthLoading ? 'Checking...' : health?.components?.api_server?.status || 'Unknown'}
              </p>
            </div>
          </div>
          {health?.components?.api_server && (
            <div className="mt-4 text-sm text-gray-600">
              <p>Memory: {health.components.api_server.memory_usage_mb}MB</p>
              <p>CPU: {health.components.api_server.cpu_usage_percent}%</p>
            </div>
          )}
        </div>

        {/* Encryption Status */}
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center space-x-3">
            <Lock className="w-8 h-8 text-purple-500" />
            <div>
              <p className="text-sm text-gray-600">Encryption</p>
              <p className="text-lg font-semibold text-gray-900">
                {encryptionLoading ? 'Checking...' : encryption?.data?.status || 'Unknown'}
              </p>
            </div>
          </div>
          {encryption?.data && (
            <div className="mt-4 text-sm text-gray-600">
              <p>Algorithm: {encryption.data.algorithm}</p>
              <p>Operations: {encryption.data.encryption_operations}</p>
            </div>
          )}
        </div>
      </div>

      {/* Metrics Summary */}
      {metrics?.data && (
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Security Metrics Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{metrics.data.data_access_operations || 0}</p>
              <p className="text-sm text-gray-600">Data Access Operations</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{metrics.data.integrity_violations || 0}</p>
              <p className="text-sm text-gray-600">Integrity Violations</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">{metrics.data.unauthorized_attempts || 0}</p>
              <p className="text-sm text-gray-600">Unauthorized Attempts</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-yellow-600">{metrics.data.compliance_violations || 0}</p>
              <p className="text-sm text-gray-600">Compliance Violations</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">{metrics.data.encryption_operations || 0}</p>
              <p className="text-sm text-gray-600">Encryption Operations</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{metrics.data.api_requests || 0}</p>
              <p className="text-sm text-gray-600">API Requests</p>
            </div>
          </div>
        </div>
      )}

      {/* Grafana Integration */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Advanced Monitoring</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Prometheus Metrics</h4>
            <p className="text-sm text-gray-600 mb-4">
              Access raw metrics and custom queries via Prometheus interface
            </p>
            <button
              onClick={() => window.open('http://localhost:9090', '_blank')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Open Prometheus
            </button>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Grafana Dashboards</h4>
            <p className="text-sm text-gray-600 mb-4">
              Comprehensive dashboards for security, compliance, and performance monitoring
            </p>
            <button
              onClick={() => window.open('http://localhost:3000', '_blank')}
              className="inline-flex items-center px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Open Grafana
            </button>
          </div>
        </div>
      </div>
    </div>
  )
} 