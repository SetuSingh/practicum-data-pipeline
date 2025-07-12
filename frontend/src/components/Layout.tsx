import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  FileText, 
  Shield, 
  Settings, 
  Menu,
  X
} from 'lucide-react'
import type { NavItem } from '@/types'

const navigation: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', href: '/', icon: BarChart3 },
  { id: 'reports', label: 'Reports', href: '/reports', icon: FileText },
  { id: 'monitoring', label: 'Monitoring', href: '/monitoring', icon: Shield },
  { id: 'settings', label: 'Settings', href: '/settings', icon: Settings },
]

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="min-h-screen gradient-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="glass-card rounded-2xl p-6 mb-8 mt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <Shield className="w-8 h-8 text-primary-500" />
                <div>
                  <h1 className="text-2xl font-semibold text-gray-900">
                    Secure Data Pipeline
                  </h1>
                  <p className="text-sm text-gray-600">
                    Data Processing & Compliance Dashboard
                  </p>
                </div>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon
                const isActive = item.href === '/' 
                  ? location.pathname === '/' 
                  : location.pathname.startsWith(item.href)
                return (
                  <Link
                    key={item.id}
                    to={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-500 text-white'
                        : 'text-gray-600 hover:text-primary-500 hover:bg-primary-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </nav>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-lg text-gray-600 hover:text-primary-500 hover:bg-primary-50"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>

          {/* Mobile Navigation */}
          {isMobileMenuOpen && (
            <nav className="md:hidden mt-4 pt-4 border-t border-gray-200">
              <div className="space-y-2">
                {navigation.map((item) => {
                  const Icon = item.icon
                  const isActive = item.href === '/' 
                    ? location.pathname === '/' 
                    : location.pathname.startsWith(item.href)
                  return (
                    <Link
                      key={item.id}
                      to={item.href}
                      className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-primary-500 text-white'
                          : 'text-gray-600 hover:text-primary-500 hover:bg-primary-50'
                      }`}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </Link>
                  )
                })}
              </div>
            </nav>
          )}
        </header>

        {/* Main Content */}
        <main className="pb-8">
          {children}
        </main>
      </div>
    </div>
  )
} 