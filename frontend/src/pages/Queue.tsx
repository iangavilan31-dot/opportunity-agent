import { useEffect, useState, useCallback, useRef } from 'react'
import { Search, RefreshCw, Inbox, Check, X, Send, Keyboard } from 'lucide-react'
import type { Lead, LeadStatus } from '../types'
import { api } from '../api'
import LeadCard from '../components/LeadCard'
import EmailModal from '../components/EmailModal'

const FILTER_TABS: { key: string; label: string; statuses: LeadStatus[] }[] = [
  { key: 'pending', label: 'Pending Review', statuses: ['queued'] },
  { key: 'approved', label: 'Approved', statuses: ['approved'] },
  { key: 'all', label: 'All Scored', statuses: ['queued', 'scored', 'researched', 'email_generated', 'approved'] },
]

export default function Queue() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [activeFilter, setActiveFilter] = useState('pending')
  const [search, setSearch] = useState('')
  const [nicheFilter, setNicheFilter] = useState('')
  const [nicheOptions, setNicheOptions] = useState<Array<{ niche: string; label: string; count: number }>>([])
  const [loading, setLoading] = useState(false)

  const [focusedIdx, setFocusedIdx] = useState(0)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [editorLead, setEditorLead] = useState<Lead | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const filter = FILTER_TABS.find((t) => t.key === activeFilter)!
      const res = await api.leads({
        status: filter.statuses.join(','),
        search: search || undefined,
        niche: nicheFilter || undefined,
        page,
        limit: 25,
      })
      setLeads(res.leads)
      setTotal(res.total)
      setPages(res.pages)
      setFocusedIdx(0)
    } finally {
      setLoading(false)
    }
  }, [activeFilter, search, nicheFilter, page])

  useEffect(() => { setPage(1) }, [activeFilter, search, nicheFilter])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    api.stats().then((s) => setNicheOptions(s.niches.filter((n) => n.niche !== 'generic'))).catch(() => {})
  }, [])

  const handleUpdate = (updated: Lead) =>
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)))

  const handleRemove = (id: number) => {
    setLeads((prev) => prev.filter((l) => l.id !== id))
    setTotal((t) => t - 1)
    setSelected((prev) => { const n = new Set(prev); n.delete(id); return n })
  }

  const toggleSelect = (id: number) =>
    setSelected((prev) => {
      const n = new Set(prev)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })

  const scrollToFocused = (idx: number) => {
    const el = containerRef.current?.querySelector(`[data-lead-id="${leads[idx]?.id}"]`)
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }

  // Keyboard-driven review
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      if (editorLead) return
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (!leads.length) return

      const lead = leads[focusedIdx]

      switch (e.key.toLowerCase()) {
        case 'j': case 'arrowdown': {
          e.preventDefault()
          const next = Math.min(leads.length - 1, focusedIdx + 1)
          setFocusedIdx(next); scrollToFocused(next); break
        }
        case 'k': case 'arrowup': {
          e.preventDefault()
          const prev = Math.max(0, focusedIdx - 1)
          setFocusedIdx(prev); scrollToFocused(prev); break
        }
        case 'a': {
          if (!lead || lead.status === 'approved') return
          e.preventDefault()
          await api.approveLead(lead.id)
          handleUpdate({ ...lead, status: 'approved' })
          break
        }
        case 'g': {
          if (!lead) return
          e.preventDefault()
          if (lead.status !== 'approved') {
            await api.approveLead(lead.id)
            handleUpdate({ ...lead, status: 'approved' })
          }
          window.open(lead.gmail_compose_url, '_blank')
          break
        }
        case 'r': {
          if (!lead) return
          e.preventDefault()
          await api.rejectLead(lead.id)
          handleRemove(lead.id)
          setFocusedIdx((i) => Math.min(i, leads.length - 2))
          break
        }
        case 'e': {
          if (!lead) return
          e.preventDefault(); setEditorLead(lead); break
        }
        case 'x': case ' ': {
          if (!lead) return
          e.preventDefault(); toggleSelect(lead.id); break
        }
        case '?': {
          e.preventDefault(); setShowHelp((s) => !s); break
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [leads, focusedIdx, editorLead])

  const bulkApprove = async () => {
    const ids = [...selected]
    await api.bulkApprove(ids)
    setLeads((prev) => prev.map((l) => (selected.has(l.id) ? { ...l, status: 'approved' } : l)))
    setSelected(new Set())
  }

  const bulkReject = async () => {
    const ids = [...selected]
    await api.bulkReject(ids)
    setLeads((prev) => prev.filter((l) => !selected.has(l.id)))
    setTotal((t) => t - ids.length)
    setSelected(new Set())
  }

  const selectAll = () => setSelected(new Set(leads.map((l) => l.id)))

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-primary font-semibold text-xl">Queue</h1>
          <span className="text-muted text-sm font-mono">{total} leads</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHelp((s) => !s)}
            className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-muted hover:text-primary border border-border rounded transition-colors"
            title="Keyboard shortcuts"
          >
            <Keyboard size={13} />
          </button>
          <select
            value={nicheFilter}
            onChange={(e) => setNicheFilter(e.target.value)}
            className="px-2 py-1.5 bg-s2 border border-border rounded text-sm text-primary focus:border-accent/50 cursor-pointer"
          >
            <option value="">All niches</option>
            {nicheOptions.map((n) => (
              <option key={n.niche} value={n.niche}>{n.label} ({n.count})</option>
            ))}
          </select>
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-dim" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search companies…"
              className="pl-7 pr-3 py-1.5 bg-s2 border border-border rounded text-sm text-primary placeholder-dim focus:border-accent/50 w-44"
            />
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="p-1.5 text-muted hover:text-primary border border-border rounded transition-colors disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between px-6 border-b border-border shrink-0">
        <div className="flex gap-0">
          {FILTER_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveFilter(key)}
              className={`px-3 py-2.5 text-xs border-b-2 transition-colors -mb-px ${
                activeFilter === key
                  ? 'border-accent text-primary'
                  : 'border-transparent text-muted hover:text-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {leads.length > 0 && (
          <button onClick={selectAll} className="text-2xs text-dim hover:text-muted">
            Select all
          </button>
        )}
      </div>

      {/* Keyboard help */}
      {showHelp && (
        <div className="px-6 py-2 bg-s2 border-b border-border flex flex-wrap gap-x-4 gap-y-1 text-2xs text-muted">
          {[
            ['J / ↓', 'next'], ['K / ↑', 'prev'], ['A', 'approve'],
            ['G', 'approve + Gmail'], ['R', 'reject'], ['E', 'edit'],
            ['X / Space', 'select'], ['?', 'toggle help'],
          ].map(([key, desc]) => (
            <span key={key}>
              <kbd className="font-mono text-primary bg-s3 px-1 rounded">{key}</kbd>
              <span className="ml-1">{desc}</span>
            </span>
          ))}
        </div>
      )}

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="px-6 py-2 bg-accent-dim/30 border-b border-accent/20 flex items-center gap-3">
          <span className="text-xs text-primary font-medium">{selected.size} selected</span>
          <div className="flex-1" />
          <button
            onClick={bulkReject}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-muted hover:text-red border border-border rounded transition-colors"
          >
            <X size={11} /> Reject all
          </button>
          <button
            onClick={bulkApprove}
            className="flex items-center gap-1.5 px-3 py-1 text-xs bg-green/15 hover:bg-green/25 text-green border border-green/40 rounded transition-colors font-medium"
          >
            <Check size={11} /> Approve {selected.size}
          </button>
          <button onClick={() => setSelected(new Set())} className="text-2xs text-dim hover:text-muted">
            Clear
          </button>
        </div>
      )}

      {/* Content */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4">
        {leads.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Inbox size={32} className="text-dim mb-3" strokeWidth={1} />
            <div className="text-muted text-sm">No leads in queue</div>
            <div className="text-dim text-xs mt-1">Run the pipeline to discover opportunities</div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {leads.map((lead, i) => (
              <LeadCard
                key={lead.id}
                lead={lead}
                focused={i === focusedIdx}
                selected={selected.has(lead.id)}
                onToggleSelect={toggleSelect}
                onOpenEditor={setEditorLead}
                onUpdate={handleUpdate}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}

        {pages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6 pb-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 text-xs text-muted hover:text-primary border border-border rounded disabled:opacity-30"
            >
              Prev
            </button>
            <span className="text-muted text-xs font-mono">{page} / {pages}</span>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="px-3 py-1.5 text-xs text-muted hover:text-primary border border-border rounded disabled:opacity-30"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {editorLead && (
        <EmailModal
          lead={editorLead}
          onClose={() => setEditorLead(null)}
          onSave={(updated) => { handleUpdate(updated); setEditorLead(null) }}
        />
      )}
    </div>
  )
}
