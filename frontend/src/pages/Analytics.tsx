import { useMemo } from 'react'
import { TrendingUp, DollarSign, Send } from 'lucide-react'
import { useRealLeads, summarize, analyze, STAGES } from '../lib/leads'
import PageHeader from '../components/PageHeader'

function money(n: number): string {
  if (n >= 1000) return `$${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`
  return `$${n}`
}

// monochrome until the business answers — then red
const STAGE_COLOR = (idx: number, count: number) =>
  count === 0 ? '#2a2a30' : idx >= 3 ? '#e5484d' : idx === 2 ? '#f5f5f6' : '#8b8b93'

export default function Analytics() {
  // computed from the same canonical real leads as every other surface —
  // one count per business, no server-side drift, no demo rows
  const { leads, refresh } = useRealLeads(30000)
  const sum = useMemo(() => summarize(leads), [leads])
  const extra = useMemo(() => analyze(leads), [leads])

  const maxFunnel = Math.max(1, ...sum.counts)
  const maxNiche = Math.max(1, ...extra.nicheRows.map((n) => n.estValue))
  const maxBin = Math.max(1, ...extra.bins)
  const maxDay = Math.max(1, ...extra.sendsByDay.map(([, c]) => c))

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <PageHeader title="Analytics">
        <button
          onClick={refresh}
          className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors"
          title="Refresh"
        >
          <TrendingUp size={13} />
        </button>
      </PageHeader>

      <div className="p-6 flex flex-col gap-6">
        {/* the only headline numbers are REAL ones; dollars are labeled estimates */}
        <div className="grid grid-cols-3 gap-3">
          <div className="pt-4 border-t border-border-subtle flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Active Businesses</span>
              <TrendingUp size={13} className="text-dim" />
            </div>
            <div className="text-3xl font-semibold num text-primary">{sum.active}</div>
            <div className="text-2xs text-muted">{sum.discovered} discovered · {sum.declined} declined</div>
          </div>
          <div className="pt-4 border-t border-border-subtle flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Reached</span>
              <Send size={13} className="text-dim" />
            </div>
            <div className="text-3xl font-semibold num text-primary">{sum.cumulative.sent}</div>
            <div className="text-2xs text-muted">
              {sum.cumulative.replied} replied · {sum.cumulative.meeting} meetings · {sum.cumulative.won} won
            </div>
          </div>
          <div className="pt-4 border-t border-border-subtle flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Potential · estimate</span>
              <DollarSign size={13} className="text-dim" />
            </div>
            {/* projections never outrank real numbers on this screen */}
            <div className="text-xl font-semibold num text-muted">{money(extra.estPotential)}</div>
            <div className="text-2xs text-muted">Projection if every active lead closed — not earned money</div>
          </div>
        </div>

        {/* Funnel — live stage populations, plainly. No invented conversion math. */}
        <div className="pt-5 border-t border-border-subtle">
          <div className="eyebrow !text-[10px] mb-4">Funnel — where every business stands right now</div>
          <div className="flex flex-col gap-2.5">
            {STAGES.map((s, i) => {
              const count = sum.counts[i]
              return (
                <div key={s.key} className="flex items-center gap-3">
                  <span className="text-xs text-muted w-20 shrink-0">{s.name}</span>
                  <div className="flex-1 h-5 relative">
                    <div
                      className="h-full rounded transition-all flex items-center px-2"
                      style={{
                        width: `${Math.max(4, (count / maxFunnel) * 100)}%`,
                        background: STAGE_COLOR(i, count),
                        opacity: 0.8,
                      }}
                    >
                      <span className={`text-2xs num font-medium ${count > 0 && i === 2 ? 'text-bg' : 'text-primary'}`}>{count}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Estimated value by niche — a chart only when there is a comparison to make */}
        {extra.nicheRows.length === 1 && (
          <div className="pt-5 border-t border-border-subtle">
            <div className="eyebrow !text-[10px] mb-2">Estimated Value by Niche · projection, not earned</div>
            <div className="text-sm text-primary">
              {extra.nicheRows[0].label} — <span className="num">{money(extra.nicheRows[0].estValue)}</span>
              <span className="text-muted"> across {extra.nicheRows[0].count} leads · avg score {extra.nicheRows[0].avgScore}</span>
            </div>
            <div className="text-2xs text-dim mt-1.5">One niche so far — a comparison chart appears when a second niche exists.</div>
          </div>
        )}
        {extra.nicheRows.length > 1 && (
          <div className="pt-5 border-t border-border-subtle">
            <div className="eyebrow !text-[10px] mb-4">Estimated Value by Niche · projections, not earned</div>
            <div className="flex flex-col gap-2">
              {extra.nicheRows.map((n) => (
                <div key={n.niche} className="flex items-center gap-3">
                  <span className="text-xs text-muted w-40 shrink-0 truncate">{n.label}</span>
                  <div className="flex-1 h-1.5 relative">
                    <div
                      className="h-full rounded-full bg-primary/40"
                      style={{ width: `${(n.estValue / maxNiche) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted num w-14 text-right">{money(n.estValue)}</span>
                  <span className="text-2xs text-muted num w-16 text-right whitespace-nowrap">{n.count} leads</span>
                  <span className="text-2xs text-muted num w-16 text-right whitespace-nowrap">avg {n.avgScore}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {/* Quality distribution — equal-width score bands */}
          <div className="pt-5 border-t border-border-subtle">
            <div className="eyebrow !text-[10px] mb-4">Opportunity Score Distribution</div>
            <div className="flex items-end gap-2 h-28">
              {extra.bins.map((count, i) => (
                <div key={i} className="flex flex-col items-center gap-1.5 flex-1 h-full justify-end" style={{ maxWidth: 72 }}>
                  <span className="text-2xs num text-muted">{count}</span>
                  <div
                    className="w-full rounded-sm bg-primary/60 transition-all"
                    style={{ height: `${Math.max(3, (count / maxBin) * 72)}px` }}
                  />
                  <span className="text-2xs text-muted">{extra.binLabels[i]}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sends by day — real events only; a single day is a fact, not a chart */}
          <div className="pt-5 border-t border-border-subtle">
            <div className="eyebrow !text-[10px] mb-4">Emails Sent by Day</div>
            {extra.sendsByDay.length === 0 ? (
              <div className="text-muted text-xs py-6 text-center">No sends yet</div>
            ) : extra.sendsByDay.length === 1 ? (
              <div className="py-4">
                <div className="text-sm text-primary">
                  <span className="num font-semibold">{extra.sendsByDay[0][1]}</span> emails sent — all on{' '}
                  {new Date(extra.sendsByDay[0][0] + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>
                <div className="text-2xs text-dim mt-1.5">The daily chart appears once a second sending day exists.</div>
              </div>
            ) : (
              <div className="flex items-end gap-2 h-28 border-b border-border-subtle pb-px">
                {extra.sendsByDay.slice(-14).map(([day, count]) => (
                  <div key={day} className="flex flex-col items-center gap-1.5 flex-1 h-full justify-end" style={{ maxWidth: 72 }}>
                    <span className="text-2xs num text-muted">{count}</span>
                    <div
                      className="w-full rounded-sm bg-primary/60 transition-all"
                      style={{ height: `${Math.max(3, (count / maxDay) * 68)}px` }}
                    />
                    <span className="text-2xs text-muted whitespace-nowrap">{day.slice(5)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
