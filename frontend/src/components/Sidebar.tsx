import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Inbox, Send, GitBranch, Mail, Repeat, BarChart3, Settings as SettingsIcon } from 'lucide-react'
import { api } from '../api'

const nav: Array<{
  to: string
  icon: typeof LayoutDashboard
  label: string
  badge?: 'queued' | 'approved' | 'followups_due'
}> = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/queue', icon: Inbox, label: 'Queue', badge: 'queued' },
  { to: '/send', icon: Send, label: 'Send', badge: 'approved' },
  { to: '/followups', icon: Repeat, label: 'Follow-ups', badge: 'followups_due' },
  { to: '/outreach', icon: Mail, label: 'Outreach' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
  { to: '/settings', icon: SettingsIcon, label: 'Settings' },
]

export default function Sidebar() {
  const [counts, setCounts] = useState<Record<string, number>>({})

  useEffect(() => {
    const fetchCounts = () =>
      api.stats()
        .then((s) => setCounts({
          queued: s.queued,
          approved: s.approved,
          followups_due: s.followups_due ?? 0,
        }))
        .catch(() => {})
    fetchCounts()
    const iv = setInterval(fetchCounts, 8000)
    return () => clearInterval(iv)
  }, [])

  return (
    <aside className="w-[200px] min-w-[200px] h-screen border-r border-border flex flex-col bg-surface">
      <div className="px-4 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-accent flex items-center justify-center">
            <span className="text-white font-mono font-bold" style={{ fontSize: 9 }}>OA</span>
          </div>
          <span className="text-primary font-medium text-md tracking-tight">Opportunity</span>
        </div>
      </div>

      <nav className="flex-1 p-2 flex flex-col gap-0.5">
        {nav.map(({ to, icon: Icon, label, badge }) => {
          const count = badge ? counts[badge] : undefined
          return (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-1.5 rounded text-sm transition-colors ${
                  isActive ? 'bg-s3 text-primary' : 'text-muted hover:text-primary hover:bg-s2'
                }`
              }
            >
              <Icon size={14} strokeWidth={1.5} />
              <span className="flex-1">{label}</span>
              {count != null && count > 0 && (
                <span className={`text-2xs font-mono px-1.5 rounded ${
                  badge === 'followups_due' ? 'bg-blue/20 text-blue' : 'bg-s3 text-muted'
                }`}>
                  {count}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-3 border-t border-border">
        <div className="text-2xs text-dim font-mono">v0.1.0 · local</div>
      </div>
    </aside>
  )
}
