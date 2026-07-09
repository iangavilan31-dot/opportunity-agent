import { useEffect, useState } from 'react'
import { Inbox, Send, MessageSquare, Calendar, TrendingUp, Zap } from 'lucide-react'
import type { Stats, PipelineRun } from '../types'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-primary',
}: {
  icon: React.ElementType
  label: string
  value: number | string
  sub?: string
  color?: string
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted">{label}</span>
        <Icon size={13} className="text-dim" strokeWidth={1.5} />
      </div>
      <div className={`text-3xl font-semibold font-mono ${color}`}>{value}</div>
      {sub && <div className="text-2xs text-dim">{sub}</div>}
    </div>
  )
}

function RunRow({ run }: { run: PipelineRun }) {
  const date = run.started_at
    ? new Date(run.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'
  const statusColor =
    run.status === 'completed' ? 'text-green' :
    run.status === 'failed' ? 'text-red' : 'text-yellow'

  return (
    <div className="flex items-center gap-4 py-2.5 border-b border-border last:border-0">
      <span className={`text-xs font-mono ${statusColor}`}>{run.status}</span>
      <span className="text-muted text-xs flex-1">{date}</span>
      <span className="text-dim text-xs font-mono">
        {run.scraped} scraped → {run.passed} passed → {run.emailed} queued
      </span>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [history, setHistory] = useState<PipelineRun[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    api.stats().then(setStats).catch(console.error)
    api.pipelineHistory().then(setHistory).catch(console.error)
  }, [])

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted text-sm">Loading…</div>
      </div>
    )
  }

  const funnel = [
    { label: 'Total Leads', value: stats.total_leads },
    { label: 'In Queue', value: stats.queued },
    { label: 'Sent', value: stats.sent },
    { label: 'Replied', value: stats.replied },
    { label: 'Meetings', value: stats.meetings },
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 py-4 border-b border-border">
        <h1 className="text-primary font-semibold text-xl">Dashboard</h1>
      </div>

      <div className="p-6 flex flex-col gap-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard icon={Inbox} label="In Queue" value={stats.queued} sub="Awaiting review" color="text-yellow" />
          <StatCard icon={Send} label="Emails Sent" value={stats.sent} sub="Total sent" />
          <StatCard icon={MessageSquare} label="Replies" value={stats.replied} sub={`${stats.reply_rate}% reply rate`} color="text-cyan" />
          <StatCard icon={Calendar} label="Meetings" value={stats.meetings} sub={`${stats.meeting_rate}% from replies`} color="text-green" />
          <StatCard icon={TrendingUp} label="Reply Rate" value={`${stats.reply_rate}%`} sub="Across all sends" />
          <StatCard icon={Zap} label="Total Leads" value={stats.total_leads} sub={`${stats.rejected} rejected`} color="text-accent" />
        </div>

        {/* Funnel */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-4">Funnel Overview</div>
          <div className="flex items-end gap-3">
            {funnel.map(({ label, value }, i) => {
              const max = funnel[0].value || 1
              const pct = Math.max(4, (value / max) * 100)
              return (
                <div key={label} className="flex flex-col items-center gap-2 flex-1">
                  <span className="text-primary font-mono text-md font-semibold">{value}</span>
                  <div
                    className="w-full rounded-sm transition-all"
                    style={{
                      height: `${pct * 0.6}px`,
                      background: i === 0 ? '#6366f1' :
                                  i === 1 ? '#eab308' :
                                  i === 2 ? '#3b82f6' :
                                  i === 3 ? '#06b6d4' : '#22c55e',
                      opacity: 0.7,
                      minHeight: 4,
                    }}
                  />
                  <span className="text-2xs text-dim text-center leading-tight">{label}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/queue')}
            className="flex-1 flex items-center justify-center gap-2 py-3 bg-s2 hover:bg-s3 border border-border rounded-lg text-sm text-muted hover:text-primary transition-colors"
          >
            <Inbox size={14} />
            Review Queue ({stats.queued})
          </button>
          <button
            onClick={() => navigate('/pipeline')}
            className="flex-1 flex items-center justify-center gap-2 py-3 bg-s2 hover:bg-s3 border border-border rounded-lg text-sm text-muted hover:text-primary transition-colors"
          >
            <Zap size={14} />
            Run Pipeline
          </button>
        </div>

        {/* Niche Breakdown */}
        {stats.niches && stats.niches.length > 0 && (
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="text-xs text-muted mb-3">Leads by Niche</div>
            <div className="flex flex-col gap-2">
              {stats.niches.map((n) => {
                const max = stats.niches[0].count || 1
                return (
                  <div key={n.niche} className="flex items-center gap-3">
                    <span className="text-xs text-muted w-40 shrink-0 truncate">{n.label}</span>
                    <div className="flex-1 h-1.5 bg-s3 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-purple/60"
                        style={{ width: `${(n.count / max) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-dim font-mono w-8 text-right">{n.count}</span>
                    <span className="text-2xs text-dim font-mono w-14 text-right">avg {n.avg_score}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Pipeline History */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-3">Pipeline History</div>
          {history.length === 0 ? (
            <div className="text-dim text-xs py-4 text-center">No runs yet</div>
          ) : (
            history.slice(0, 8).map((run) => <RunRow key={run.id} run={run} />)
          )}
        </div>
      </div>
    </div>
  )
}
