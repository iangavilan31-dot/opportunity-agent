import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Repeat, ExternalLink, Clock, AlertCircle, MessageSquare } from 'lucide-react'
import type { FollowupItem } from '../types'
import { api } from '../api'

// urgency reads as brightness, not hue
const STAGE_COLOR: Record<number, string> = {
  0: 'text-muted border-border bg-s2',
  1: 'text-primary/80 border-border bg-s2',
  2: 'text-primary border-muted/40 bg-s3',
}

function Row({ item, due, onSent, onReplied }: {
  item: FollowupItem
  due: boolean
  onSent: (id: number) => void
  onReplied: (id: number) => void
}) {
  const [loading, setLoading] = useState(false)

  const send = async () => {
    setLoading(true)
    try {
      window.open(item.gmail_compose_url, '_blank')
      await api.advanceFollowup(item.id)
      onSent(item.id)
    } finally {
      setLoading(false)
    }
  }

  const markReplied = async () => {
    await api.markReplied(item.id)
    onReplied(item.id)
  }

  return (
    <div className={`bg-surface border rounded-lg p-3.5 flex items-center gap-4 ${due ? 'border-border' : 'border-border/50 opacity-80'}`}>
      <span className={`text-2xs px-1.5 py-0.5 rounded border shrink-0 ${STAGE_COLOR[item.stage]}`}>
        {item.stage_label}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-primary text-sm font-medium">{item.company_name}</span>
          {item.niche_label && (
            <span className="text-2xs text-purple">{item.niche_label}</span>
          )}
          {!item.has_email && (
            <span className="flex items-center gap-1 text-2xs text-yellow"><AlertCircle size={10} /> no email</span>
          )}
        </div>
        <div className="text-muted text-xs truncate mt-0.5">{item.subject_line}</div>
      </div>

      <div className="flex items-center gap-1.5 text-2xs text-muted shrink-0">
        <Clock size={11} />
        {due ? `${Math.round(item.days_waiting)}d waiting` : `due in ${Math.max(1, Math.round(item.days_until_due))}d`}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={markReplied}
          className="flex items-center gap-1 px-2 py-1.5 text-2xs text-muted hover:text-primary border border-border hover:border-muted rounded transition-colors"
          title="They replied — stop the sequence"
        >
          <MessageSquare size={10} /> Mark replied
        </button>
        {due && (
          <button
            onClick={send}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue/15 hover:bg-blue/25 text-blue border border-blue/40 rounded transition-colors font-medium disabled:opacity-50"
          >
            <ExternalLink size={11} />
            Send {item.stage_label}
          </button>
        )}
      </div>
    </div>
  )
}

export default function Followups() {
  const [due, setDue] = useState<FollowupItem[]>([])
  const [upcoming, setUpcoming] = useState<FollowupItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.followups()
      setDue(r.due)
      setUpcoming(r.upcoming)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const removeFromDue = (id: number) => setDue((p) => p.filter((x) => x.id !== id))
  const removeEverywhere = (id: number) => {
    setDue((p) => p.filter((x) => x.id !== id))
    setUpcoming((p) => p.filter((x) => x.id !== id))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-[13px] font-bold tracking-[0.28em] uppercase text-primary">Follow-ups</h1>
          <span className="text-muted text-sm font-mono">{due.length} due · {upcoming.length} upcoming</span>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="px-6 py-2 bg-s2 border-b border-border text-2xs text-muted">
        Cadence: Follow-up 1 at 3 days, Follow-up 2 at +4, breakup at +7. A reply stops the sequence. ~80% of cold-outreach replies come from follow-ups — this is where the money is.
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-5">
        {due.length === 0 && upcoming.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Repeat size={32} className="text-dim mb-3" strokeWidth={1} />
            <div className="text-muted text-sm">No follow-ups scheduled</div>
            <div className="text-dim text-xs mt-1">Once you send emails, follow-ups appear here on cadence</div>
          </div>
        ) : (
          <>
            {due.length > 0 && (
              <div>
                <div className="text-xs text-primary font-medium mb-2 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue" /> Due now ({due.length})
                </div>
                <div className="flex flex-col gap-2">
                  {due.map((item) => (
                    <Row key={item.id} item={item} due onSent={removeFromDue} onReplied={removeEverywhere} />
                  ))}
                </div>
              </div>
            )}

            {upcoming.length > 0 && (
              <div>
                <div className="text-xs text-muted mb-2">Upcoming ({upcoming.length})</div>
                <div className="flex flex-col gap-2">
                  {upcoming.map((item) => (
                    <Row key={item.id} item={item} due={false} onSent={removeFromDue} onReplied={removeEverywhere} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
