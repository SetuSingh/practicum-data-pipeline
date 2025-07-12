import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Reports } from '@/pages/Reports'
import { JobDetails } from '@/pages/JobDetails'
import { Monitoring } from '@/pages/Monitoring'
import { Settings } from '@/pages/Settings'

function App() {
  try {
    return (
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/reports/:jobId" element={<JobDetails />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    )
  } catch (error) {
    console.error('App Error:', error)
    return (
      <div className="p-8 bg-red-100">
        <h1>Error Loading App</h1>
        <pre>{error?.toString()}</pre>
      </div>
    )
  }
}

export default App 