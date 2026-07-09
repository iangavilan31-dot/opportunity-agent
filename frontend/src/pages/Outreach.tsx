import { useEffect, useState, useCallback } from 'react'
import { Send, MessageSquare, Calendar, RefreshCw, ChevronDown, ChevronUp, Copy, CheckCheck } from 'lucide-react'
import type { Lead } from '../types'
import { api } from '../api'

// red appears exactly when a business answers — never before
const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  approved: { label: 'Approved', color: 'text-muted border-border bg-s2' },
  sent: { label: 'Sent', color: 'text-primary border-border bg-s2' },
  replied: { label: 'Replied', color: 'text-red border-red/30 bg-red-dim' },
  meeting: { label: 'Meeting', color: 'text-red border-red/40 bg-red-dim' },
}

function OutreachRow({ lead, onUpdate }: { lead: Lead; onUpdate: (l: Lead) => void }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)

  const badge = STATUS_CONFIG[lead.status] ?? { label: lead.status, color: 'text-muted border-border' }

  const daysSinceSent = lead.sent_at
    ? Math.floor((Date.now() - new Date(lead.sent_at).getTime()) / 86400000)
    : null

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const act = async (action: string, fn: () => Promise<unknown>) => {
    setLoading(action)
    try {
      await fn()
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div className="flex items-center gap-4 p-4">
        {/* Company */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-primary font-medium text-sm">{lead.company_name}</span>
            <span className={`text-2xs px-1.5 py-0.5 rounded border ${badge.color}`}>
              {badge.label}
            </span>
          </div>
          <div className="text-muted text-xs mt-0.5">{lead.contact_email || lead.job_title}</div>
        </div>

        {/* Meta */}
        <div className="text-dim text-xs font-mono shrink-0">
          {daysSinceSent !== null ? `${daysSinceSent}d ago` : '—'}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          {lead.status === 'sent' && (
            <>
              <button
                onClick={() => act('replied', async () => {
                  await api.markReplied(lead.id)
                  onUpdate({ ...lead, status: 'replied' })
                })}
                disabled={loading === 'replied'}
                className="flex items-center gap-1 px-2 py-1 text-2xs text-muted hover:text-cyan border border-border rounded transition-colors"
              >
                <MessageSquare size={10} />
                Replied
              </button>

              {/* Follow-up copy */}
              {daysSinceSent !== null && daysSinceSent >= 3 && lead.follow_up_1 && (
                <button
                  onClick={() => handleCopy(`Subject: Re: ${lead.subject_line}\n\n${lead.follow_up_1}`)}
                  className="flex items-center gap-1 px-2 py-1 text-2xs text-muted hover:text-primary border border-border rounded transition-colors"
                >
                  {copied ? <CheckCheck size={10} className="text-green" /> : <Copy size={10} />}
                  FU1
                </button>
              )}
            </>
          )}

          {lead.status === 'replied' && (
            <button
              onClick={() => act('meeting', async () => {
                await api.markMeeting(lead.id)
                onUpdate({ ...lead, status: 'meeting' })
              })}
              disabled={loading === 'meeting'}
              className="flex items-center gap-1 px-2 py-1 text-2xs text-muted hover:text-green border border-border rounded transition-colors"
            >
              <Calendar size={10} />
              Meeting
            </button>
          )}

          {lead.status === 'approved' && (
            <button
              onClick={() => act('sent', async () => {
                await api.markSent(lead.id)
                onUpdate({ ...lead, status: 'sent' })
              })}
              disabled={loading === 'sent'}
              className="flex items-center gap-1 px-2 py-1 text-2xs bg-blue/10 hover:bg-blue/20 text-blue border border-blue/30 rounded transition-colors font-medium"
            >
              <Send size={10} />
              Mark Sent
            </button>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-dim hover:text-muted rounded transition-colors"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border px-4 py-3 bg-s2 flex flex-col gap-3">
          <div>
            <div className="text-2xs text-dim mb-1">Subject</div>
            <div className="text-xs text-muted">{lead.subject_line}</div>
          </div>
          <div>
            <div className="text-2xs text-dim mb-1 flex items-center justify-between">
              <span>Email</span>
              <button
                onClick={() => handleCopy(`Subject: ${lead.subject_line}\n\n${lead.email_body}`)}
                className="flex items-center gap-1 text-dim hover:text-muted transition-colors"
              >
                {copied ? <CheckCheck size={10} className="text-green" /> : <Copy size={10} />}
                Copy
              </button>
            </div>
            <pre
              className="text-xs text-muted leading-relaxed whitespace-pre-wrap"
              style={{ fontFamily: 'inherit' }}
            >
              {lead.email_body}
            </pre>
          </div>
          {lead.notes && (
            <div>
              <div className="text-2xs text-dim mb-1">Notes</div>
              <div className="text-xs text-muted">{lead.notes}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Outreach() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [activeTab, setActiveTab] = useState('active')
  const [loading, setLoading] = useState(false)

  const TABS = [
    { key: 'active', label: 'Active', statuses: 'approved,sent,replied,meeting' },
    { key: 'sent', label: 'Sent', statuses: 'sent' },
    { key: 'replied', label: 'Replied', statuses: 'replied,meeting' },
  ]

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const tab = TABS.find((t) => t.key === activeTab)!
      const res = await api.leads({ status: tab.statuses, limit: 50 })
      setLeads(res.leads)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => { load() }, [load])

  const handleUpdate = (updated: Lead) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-primary font-semibold text-xl">Outreach</h1>
          <span className="text-muted text-sm font-mono">{total}</span>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex gap-0 px-6 border-b border-border shrink-0">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-3 py-2.5 text-xs border-b-2 transition-colors -mb-px ${
              activeTab === key
                ? 'border-accent text-primary'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-2">
        {leads.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <Send size={28} className="text-dim mb-3" strokeWidth={1} />
            <div className="text-muted text-sm">Nothing here yet</div>
            <div className="text-dim text-xs mt-1">Approve leads in Queue to get started</div>
          </div>
        ) : (
          leads.map((lead) => (
            <OutreachRow key={lead.id} lead={lead} onUpdate={handleUpdate} />
          ))
        )}
      </div>
    </div>
  )
}
