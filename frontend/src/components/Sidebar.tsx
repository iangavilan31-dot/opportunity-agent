import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Orbit, Map, LayoutDashboard, Inbox, Send, Repeat, Mail,
  BarChart3, GitBranch, Settings as SettingsIcon,
} from 'lucide-react'
import { api } from '../api'
import { useRealLeads, summarize } from '../lib/leads'

const nav: Array<{
  to: string
  icon: typeof Orbit
  label: string
  badge?: 'queued' | 'approved' | 'followups_due'
}> = [
  { to: '/', icon: Orbit, label: 'Field' },
  { to: '/atlas', icon: Map, label: 'Atlas' },
  { to: '/overview', icon: LayoutDashboard, label: 'Overview' },
  { to: '/queue', icon: Inbox, label: 'Queue', badge: 'queued' },
  { to: '/send', icon: Send, label: 'Send', badge: 'approved' },
  { to: '/followups', icon: Repeat, label: 'Follow up', badge: 'followups_due' },
  { to: '/outreach', icon: Mail, label: 'Outreach' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
]

export default function Sidebar() {
  // badges count the same real businesses every view renders — one truth
  const { leads } = useRealLeads(20000)
  const sum = summarize(leads)
  const [followupsDue, setFollowupsDue] = useState(0)

  useEffect(() => {
    const f = () => api.stats().then((s) => setFollowupsDue(s.followups_due ?? 0)).catch(() => {})
    f()
    const iv = setInterval(f, 30000)
    return () => clearInterval(iv)
  }, [])

  const counts: Record<string, number> = {
    queued: sum.counts[0],
    approved: sum.counts[1],
    followups_due: followupsDue,
  }

  return (
    <aside className="w-[64px] min-w-[64px] h-screen flex flex-col items-center py-4 gap-[2px] bg-bg border-r border-border-subtle z-10">
      {/* mark: a quiet ring holding one point — the machine around the business */}
      <NavLink to="/" className="mb-3 block" title="Web Machine">
        <div className="w-[26px] h-[26px] rounded-full border-[1.5px] border-primary/80 relative">
          <div className="absolute inset-0 m-auto w-[6px] h-[6px] rounded-full bg-primary" />
        </div>
      </NavLink>

      {nav.map(({ to, icon: Icon, label, badge }) => {
        const count = badge ? counts[badge] : undefined
        return (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={label}
            className={({ isActive }) =>
              `relative w-[54px] py-[7px] rounded-[10px] flex flex-col items-center gap-[3px] transition-colors duration-200 ${
                isActive ? 'text-primary bg-s2' : 'text-dim hover:text-primary hover:bg-s2/60'
              }`
            }
          >
            <Icon size={16} strokeWidth={1.6} />
            <span className="text-[7.5px] font-bold uppercase tracking-[0.14em] leading-none">
              {label}
            </span>
            {count != null && count > 0 && (
              <span className="absolute top-[2px] right-[4px] min-w-[14px] h-[14px] px-[3px] rounded-full bg-s3 text-primary text-[9px] font-bold leading-[14px] text-center num">
                {count > 99 ? '99' : count}
              </span>
            )}
          </NavLink>
        )
      })}

      <div className="flex-1" />

      <NavLink
        to="/settings"
        title="Settings"
        className={({ isActive }) =>
          `w-[54px] py-[7px] rounded-[10px] flex flex-col items-center gap-[3px] transition-colors duration-200 ${
            isActive ? 'text-primary bg-s2' : 'text-dim hover:text-primary hover:bg-s2/60'
          }`
        }
      >
        <SettingsIcon size={16} strokeWidth={1.6} />
        <span className="text-[7.5px] font-bold uppercase tracking-[0.14em] leading-none">Settings</span>
      </NavLink>

      <div className="mt-1 w-[28px] h-[28px] rounded-full bg-s3 text-muted text-[10px] font-bold flex items-center justify-center select-none">
        IG
      </div>
    </aside>
  )
}
