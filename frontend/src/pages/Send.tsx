import { useEffect, useState, useCallback, useRef } from 'react'
import { Send as SendIcon, RefreshCw, ExternalLink, Check, Download, AlertCircle, Keyboard } from 'lucide-react'
import { api } from '../api'

type Draft = Awaited<ReturnType<typeof api.drafts>>[number]

export default function Send() {
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [loading, setLoading] = useState(false)
  const [focusedIdx, setFocusedIdx] = useState(0)
  const [sentCount, setSentCount] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await api.drafts('approved')
      setDrafts(d)
      setFocusedIdx(0)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const sendDraft = async (draft: Draft) => {
    window.open(draft.gmail_compose_url, '_blank')
    await api.markSent(draft.id)
    setDrafts((prev) => prev.filter((d) => d.id !== draft.id))
    setSentCount((c) => c + 1)
    setFocusedIdx((i) => Math.min(i, drafts.length - 2))
  }

  const scrollToFocused = (idx: number) => {
    const el = containerRef.current?.querySelector(`[data-draft-id="${drafts[idx]?.id}"]`)
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }

  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (!drafts.length) return
      const draft = drafts[focusedIdx]
      switch (e.key.toLowerCase()) {
        case 'j': case 'arrowdown':
          e.preventDefault(); { const n = Math.min(drafts.length - 1, focusedIdx + 1); setFocusedIdx(n); scrollToFocused(n) } break
        case 'k': case 'arrowup':
          e.preventDefault(); { const p = Math.max(0, focusedIdx - 1); setFocusedIdx(p); scrollToFocused(p) } break
        case 'enter': case 'g':
          if (draft) { e.preventDefault(); await sendDraft(draft) } break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [drafts, focusedIdx])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-[13px] font-bold tracking-[0.28em] uppercase text-primary">Send</h1>
          <span className="text-muted text-sm font-mono">{drafts.length} ready</span>
          {sentCount > 0 && (
            <span className="text-green text-sm font-mono">{sentCount} sent this session</span>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Help bar */}
      <div className="px-6 py-2 bg-s2 border-b border-border flex items-center gap-4 text-2xs text-muted">
        <Keyboard size={12} />
        {[['J / K', 'navigate'], ['Enter / G', 'open in Gmail + mark sent']].map(([k, d]) => (
          <span key={k}>
            <kbd className="font-mono text-primary bg-s3 px-1 rounded">{k}</kbd>
            <span className="ml-1">{d}</span>
          </span>
        ))}
        <span className="ml-auto text-dim">One click opens a pre-filled Gmail draft — review, hit send, move on.</span>
      </div>

      {/* Content */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4">
        {drafts.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <SendIcon size={32} className="text-dim mb-3" strokeWidth={1} />
            <div className="text-muted text-sm">No approved drafts</div>
            <div className="text-muted text-xs mt-1">Approve leads in the Queue and they'll appear here ready to send</div>
            <a
              href="/queue"
              className="mt-4 px-4 py-2 bg-primary hover:bg-primary/90 text-bg rounded text-xs font-semibold transition-colors"
            >
              Review the Queue
            </a>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {drafts.map((draft, i) => (
              <div
                key={draft.id}
                data-draft-id={draft.id}
                className={`bg-surface border rounded-lg p-3.5 flex items-center gap-4 transition-all ${
                  i === focusedIdx ? 'border-accent ring-1 ring-accent/40' : 'border-border'
                }`}
              >
                {/* Score */}
                <div className="font-mono font-semibold text-sm text-green w-8 text-center shrink-0">
                  {draft.automation_score}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-primary text-sm font-medium">{draft.company_name}</span>
                    {!draft.has_email && (
                      <span className="flex items-center gap-1 text-2xs text-yellow" title="No contact email found — add one before sending">
                        <AlertCircle size={10} /> no email
                      </span>
                    )}
                  </div>
                  <div className="text-muted text-xs truncate mt-0.5">{draft.subject_line}</div>
                  {draft.contact_email && (
                    <div className="text-dim text-2xs font-mono mt-0.5">{draft.contact_email}</div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <a
                    href={`/api/leads/${draft.id}/eml`}
                    className="p-1.5 text-dim hover:text-muted border border-border rounded transition-colors"
                    title="Download .eml draft"
                  >
                    <Download size={12} />
                  </a>
                  <button
                    onClick={() => sendDraft(draft)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue/15 hover:bg-blue/25 text-blue border border-blue/40 rounded transition-colors font-medium"
                  >
                    <ExternalLink size={11} />
                    Open in Gmail
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
