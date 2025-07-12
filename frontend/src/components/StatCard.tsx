import { TrendingUp, TrendingDown } from 'lucide-react'
import type { StatCardProps } from '@/types'

export function StatCard({ title, value, icon: Icon, trend }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-4">
        <Icon className="w-8 h-8" />
        {trend && (
          <div className={`flex items-center space-x-1 ${
            trend.isPositive ? 'text-green-100' : 'text-red-100'
          }`}>
            {trend.isPositive ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span className="text-sm font-medium">
              {Math.abs(trend.value)}%
            </span>
          </div>
        )}
      </div>
      <div className="space-y-1">
        <p className="text-3xl font-bold">{value}</p>
        <p className="text-sm opacity-90">{title}</p>
      </div>
    </div>
  )
} 