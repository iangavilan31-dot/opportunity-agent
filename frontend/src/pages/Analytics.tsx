import { useEffect, useState } from 'react'
import { TrendingUp, DollarSign, Target, RefreshCw } from 'lucide-react'
import { api } from '../api'

type Data = Awaited<ReturnType<typeof api.analytics>>

// monochrome until the business answers — then red
const FUNNEL_STAGES = [
  { key: 'queued', label: 'Queued', color: '#4a4a52' },
  { key: 'approved', label: 'Approved', color: '#8b8b93' },
  { key: 'sent', label: 'Sent', color: '#f5f5f6' },
  { key: 'replied', label: 'Replied', color: '#e5484d' },
  { key: 'meeting', label: 'Meeting', color: '#f0605f' },
]

function money(n: number): string {
  if (n >= 1000) return `$${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`
  return `$${n}`
}

export default function Analytics() {
  const [data, setData] = useState<Data | null>(null)
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    api.analytics().then(setData).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  if (!data) {
    return <div className="flex items-center justify-center h-full text-muted text-sm">Loading…</div>
  }

  const maxFunnel = Math.max(...FUNNEL_STAGES.map((s) => data.funnel[s.key] || 0), 1)
  const maxNiche = Math.max(...data.by_niche.map((n) => n.potential), 1)

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <h1 className="text-primary font-semibold text-xl">Analytics</h1>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="p-6 flex flex-col gap-6">
        {/* Pipeline value — the headline numbers */}
        <div className="grid grid-cols-3 gap-3">
          {/* the only headline number is a REAL one; dollars here are estimates
              and must say so — earned money lives on the Field, not in analytics */}
          <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Active Leads</span>
              <TrendingUp size={13} className="text-dim" />
            </div>
            <div className="text-3xl font-semibold font-mono text-primary">
              {Object.values(data.funnel).reduce((a, b) => a + b, 0)}
            </div>
            <div className="text-2xs text-dim">In the funnel right now</div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Weighted Pipeline · estimate</span>
              <DollarSign size={13} className="text-dim" />
            </div>
            <div className="text-3xl font-semibold font-mono text-muted">{money(data.pipeline.weighted)}</div>
            <div className="text-2xs text-dim">Projection, probability-weighted by stage — not earned money</div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Total Potential · estimate</span>
              <Target size={13} className="text-dim" />
            </div>
            <div className="text-3xl font-semibold font-mono text-muted">{money(data.pipeline.total_potential)}</div>
            <div className="text-2xs text-dim">Projection if every active lead closed — not earned money</div>
          </div>
        </div>

        {/* Funnel with conversion */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-4">Conversion Funnel</div>
          <div className="flex flex-col gap-2.5">
            {FUNNEL_STAGES.map((s, i) => {
              const count = data.funnel[s.key] || 0
              const prev = i > 0 ? (data.funnel[FUNNEL_STAGES[i - 1].key] || 0) : null
              const conv = prev && prev > 0 ? Math.round((count / prev) * 100) : null
              return (
                <div key={s.key} className="flex items-center gap-3">
                  <span className="text-xs text-muted w-20 shrink-0">{s.label}</span>
                  <div className="flex-1 h-5 bg-s3 rounded overflow-hidden relative">
                    <div
                      className="h-full rounded transition-all flex items-center px-2"
                      style={{
                        width: `${Math.max(3, (count / maxFunnel) * 100)}%`,
                        // red is earned by real activity — an empty stage stays gray
                        background: count > 0 ? s.color : '#3c3c44',
                        opacity: 0.75,
                      }}
                    >
                      <span className={`text-2xs font-mono font-medium ${count > 0 && (s.key === 'sent' || s.key === 'approved') ? 'text-bg' : 'text-primary'}`}>{count}</span>
                    </div>
                  </div>
                  <span className="text-2xs text-dim font-mono w-16 text-right">
                    {conv != null ? `${conv}% conv` : ''}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Niche performance */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-4">Estimated Value by Niche · projections, not earned</div>
          <div className="flex flex-col gap-2.5">
            {data.by_niche.map((n) => (
              <div key={n.niche} className="flex items-center gap-3">
                <span className="text-xs text-muted w-40 shrink-0 truncate">{n.label}</span>
                <div className="flex-1 h-1.5 bg-s3 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-green/60" style={{ width: `${(n.potential / maxNiche) * 100}%` }} />
                </div>
                <span className="text-xs text-green font-mono w-14 text-right">{money(n.potential)}</span>
                <span className="text-2xs text-dim font-mono w-12 text-right">{n.count} ld</span>
                <span className="text-2xs text-dim font-mono w-14 text-right">avg {n.avg_score}</span>
                <span className="text-2xs text-cyan font-mono w-16 text-right">
                  {n.reply_rate != null ? `${n.reply_rate}% rep` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Score distribution */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-4">Lead Quality Distribution</div>
          <div className="flex items-end gap-3 h-28">
            {data.score_bands.map((b) => {
              const max = Math.max(...data.score_bands.map((x) => x.count), 1)
              return (
                <div key={b.band} className="flex-1 flex flex-col items-center gap-2 justify-end h-full">
                  <span className="text-xs font-mono text-primary">{b.count}</span>
                  <div
                    className="w-full rounded-sm bg-accent/60 transition-all"
                    style={{ height: `${Math.max(2, (b.count / max) * 80)}%` }}
                  />
                  <span className="text-2xs text-dim">{b.band}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
