import { useEffect, useMemo, useState } from 'react'
import { Inbox, Send, MessageSquare, Calendar, MapPin, Zap } from 'lucide-react'
import type { PipelineRun } from '../types'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'
import { useRealLeads, summarize, analyze, STAGES } from '../lib/leads'
import PageHeader from '../components/PageHeader'

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
      <div className={`text-3xl font-semibold num ${color}`}>{value}</div>
      {sub && <div className="text-2xs text-muted">{sub}</div>}
    </div>
  )
}

function RunRow({ run }: { run: PipelineRun }) {
  const date = run.started_at
    ? new Date(run.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—'
  const statusColor = run.status === 'completed' ? 'text-primary' : 'text-muted'

  return (
    <div className="flex items-center gap-4 py-2.5 border-b border-border last:border-0">
      <span className={`text-xs font-mono ${statusColor}`}>{run.status}</span>
      <span className="text-muted text-xs flex-1">{date}</span>
      <span className="text-muted text-xs font-mono">
        {run.scraped} scraped → {run.passed} passed → {run.emailed} queued
      </span>
    </div>
  )
}

export default function Dashboard() {
  // the same canonical real leads every other surface renders
  const { leads } = useRealLeads(20000)
  const sum = useMemo(() => summarize(leads), [leads])
  const extra = useMemo(() => analyze(leads), [leads])
  const [history, setHistory] = useState<PipelineRun[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    api.pipelineHistory().then(setHistory).catch(console.error)
  }, [])

  const replyRate = sum.cumulative.sent > 0
    ? Math.round((sum.cumulative.replied / sum.cumulative.sent) * 1000) / 10
    : 0

  const funnel = STAGES.map((s, i) => ({ label: s.name, value: sum.counts[i], idx: i }))
  const maxFunnel = Math.max(1, ...funnel.map((f) => f.value))

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <PageHeader title="Overview" />

      <div className="p-6 flex flex-col gap-6">
        {/* Stats Grid — every number is a real business count */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard icon={Zap} label="Discovered" value={sum.discovered} sub={`${sum.declined} declined`} />
          <StatCard icon={Inbox} label="In Queue" value={sum.counts[0]} sub="Awaiting review" color="text-muted" />
          <StatCard icon={Send} label="Reached" value={sum.cumulative.sent} sub="Real emails sent" />
          <StatCard icon={MessageSquare} label="Replies" value={sum.cumulative.replied} sub={`${replyRate}% of reached`} color={sum.cumulative.replied > 0 ? 'text-red' : 'text-muted'} />
          <StatCard icon={Calendar} label="Meetings" value={sum.cumulative.meeting} sub="Booked from replies" color={sum.cumulative.meeting > 0 ? 'text-red' : 'text-muted'} />
          <StatCard icon={MapPin} label="Cities" value={extra.cityCount} sub="Real locations reached" />
        </div>

        {/* Funnel — red exists only where real activity exists */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-4">Funnel — live stage populations</div>
          <div className="flex items-end gap-3">
            {funnel.map(({ label, value, idx }) => {
              const pct = Math.max(4, (value / maxFunnel) * 100)
              return (
                <div key={label} className="flex flex-col items-center gap-2 flex-1">
                  <span className="text-primary num text-md font-semibold">{value}</span>
                  <div
                    className="w-full rounded-sm transition-all"
                    style={{
                      height: `${pct * 0.6}px`,
                      background: value === 0 ? '#2a2a30' : idx >= 3 ? '#e5484d' : idx === 2 ? '#f5f5f6' : '#8b8b93',
                      opacity: 0.75,
                      minHeight: 4,
                    }}
                  />
                  <span className="text-2xs text-muted text-center leading-tight">{label}</span>
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
            Review Queue ({sum.counts[0]})
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
        {extra.nicheRows.length > 0 && (
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="text-xs text-muted mb-3">Businesses by Niche</div>
            <div className="flex flex-col gap-2">
              {extra.nicheRows.map((n) => {
                const max = extra.nicheRows[0].count || 1
                return (
                  <div key={n.niche} className="flex items-center gap-3">
                    <span className="text-xs text-muted w-40 shrink-0 truncate">{n.label}</span>
                    <div className="flex-1 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary/50"
                        style={{ width: `${(n.count / max) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted num w-8 text-right">{n.count}</span>
                    <span className="text-2xs text-muted num w-16 text-right whitespace-nowrap">avg {n.avgScore}</span>
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
            <div className="text-muted text-xs py-4 text-center">No runs yet</div>
          ) : (
            history.slice(0, 8).map((run) => <RunRow key={run.id} run={run} />)
          )}
        </div>
      </div>
    </div>
  )
}
