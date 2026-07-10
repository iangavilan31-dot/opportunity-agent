import { useState } from 'react'
import {
  ExternalLink, Mail, User, ChevronDown, ChevronUp,
  Check, X, Pencil, FileText, Copy, CheckCheck, Send,
  CheckCircle2, AlertTriangle, Ban,
} from 'lucide-react'
import type { Lead } from '../types'
import { api } from '../api'
import EmailModal from './EmailModal'

interface Props {
  lead: Lead
  onUpdate: (updated: Lead) => void
  onRemove: (id: number) => void
  focused?: boolean
  selected?: boolean
  onToggleSelect?: (id: number) => void
  onOpenEditor?: (lead: Lead) => void
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? 'text-score-high bg-s3 border-muted/30' :
    score >= 65 ? 'text-score-mid bg-s2 border-border' :
    score >= 50 ? 'text-score-low bg-s2 border-border-subtle' :
                  'text-score-fail bg-surface border-border-subtle'

  return (
    <div className={`font-mono font-semibold text-base px-2.5 py-0.5 rounded border ${color}`}>
      {score}
    </div>
  )
}

const CATEGORY_LABELS: Record<string, string> = {
  scheduling: 'Scheduling',
  coordination: 'Coordination',
  crm: 'CRM',
  reporting: 'Reporting',
  intake: 'Intake',
  data_entry: 'Data Entry',
  communication: 'Communication',
  admin: 'Admin',
  recruiting: 'Recruiting',
}

export default function LeadCard({
  lead, onUpdate, onRemove, focused, selected, onToggleSelect, onOpenEditor,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showContactForm, setShowContactForm] = useState(false)
  const [cName, setCName] = useState(lead.contact_name ?? '')
  const [cTitle, setCTitle] = useState(lead.contact_title ?? '')
  const [cEmail, setCEmail] = useState(lead.contact_email ?? '')

  const saveContact = () =>
    act('contact', async () => {
      await api.setContact(lead.id, { contact_name: cName, contact_title: cTitle, contact_email: cEmail })
      const fresh = await api.getLead(lead.id)
      onUpdate(fresh)
      setShowContactForm(false)
    })

  const act = async (action: string, fn: () => Promise<unknown>) => {
    setLoading(action)
    try {
      await fn()
    } finally {
      setLoading(null)
    }
  }

  const handleApprove = () =>
    act('approve', async () => {
      await api.approveLead(lead.id)
      onUpdate({ ...lead, status: 'approved' })
    })

  const handleApproveAndGmail = () =>
    act('approve', async () => {
      await api.approveLead(lead.id)
      onUpdate({ ...lead, status: 'approved' })
      window.open(lead.gmail_compose_url, '_blank')
    })

  const handleReject = () =>
    act('reject', async () => {
      await api.rejectLead(lead.id)
      onRemove(lead.id)
    })

  const handleCopyEmail = () => {
    const text = `Subject: ${lead.subject_line}\n\n${lead.email_body}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const isApproved = lead.status === 'approved'
  const openEditor = () => (onOpenEditor ? onOpenEditor(lead) : setShowModal(true))

  const q = lead.quality
  // red belongs to real business activity only — a blocked draft is a
  // neutral workflow state, not a signal. And "Blocked" for a merely
  // contact-less lead reads like an error on your best prospects.
  const contactOnly = (q?.blocking ?? []).length > 0 &&
    (q?.blocking ?? []).every((b) => /contact|email|address/i.test(b))
  const qConfig = {
    ready: { icon: CheckCircle2, color: 'text-primary', label: 'Ready' },
    warn: { icon: AlertTriangle, color: 'text-muted', label: 'Check' },
    blocked: contactOnly
      ? { icon: AlertTriangle, color: 'text-muted', label: 'Needs contact' }
      : { icon: Ban, color: 'text-muted', label: 'Blocked' },
  }[q?.level ?? 'ready']
  const QIcon = qConfig.icon
  const qTip = [...(q?.blocking ?? []), ...(q?.warnings ?? [])].join(' · ')

  return (
    <>
      {/* editorial row, not a boxed card: hairline top, focus = left rule + lift */}
      <div
        data-lead-id={lead.id}
        className={`border-t border-border-subtle border-l-2 transition-all ${
          focused ? 'border-l-primary bg-s2/50' :
          selected ? 'border-l-muted bg-s2/30' :
          isApproved ? 'border-l-dim bg-transparent hover:bg-s2/25' : 'border-l-transparent bg-transparent hover:bg-s2/25'
        }`}
      >
        {/* Top Row */}
        <div className="flex items-start gap-3 p-4">
          {onToggleSelect && (
            <button
              onClick={() => onToggleSelect(lead.id)}
              className={`mt-0.5 w-4 h-4 rounded border shrink-0 flex items-center justify-center transition-colors ${
                selected ? 'bg-accent border-accent' : 'border-border hover:border-muted'
              }`}
            >
              {selected && <Check size={10} className="text-bg" />}
            </button>
          )}
          <ScoreBadge score={lead.automation_score} />

          <div className="flex-1 min-w-0">
            {/* Company */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-primary font-medium text-md leading-tight">
                {lead.company_name}
              </span>
              {lead.company_domain && (
                <span className="text-dim text-xs font-mono">{lead.company_domain}</span>
              )}
              {lead.company_size && (
                <span className="text-dim text-2xs border border-border rounded px-1.5 py-0.5">
                  {lead.company_size}
                </span>
              )}
              {lead.job_url && (
                <a
                  href={lead.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-dim hover:text-muted"
                >
                  <ExternalLink size={10} />
                </a>
              )}
            </div>

            {/* Job + Location */}
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-muted text-sm">{lead.job_title}</span>
              {lead.job_location && (
                <span className="text-dim text-xs">· {lead.job_location}</span>
              )}
            </div>

            {/* Niche + Pain category (short facts stay chips; never say one thing twice) */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              {lead.niche_label && lead.niche !== 'generic' && (
                <span className="text-2xs px-1.5 py-0.5 rounded bg-s3 text-muted border border-border font-medium">
                  {lead.niche_label}
                </span>
              )}
              {lead.pain_category &&
                (CATEGORY_LABELS[lead.pain_category] ?? lead.pain_category).toLowerCase() !== (lead.niche_label ?? '').toLowerCase() && (
                <span className="text-2xs px-1.5 py-0.5 rounded bg-s3 text-muted border border-border">
                  {CATEGORY_LABELS[lead.pain_category] ?? lead.pain_category}
                </span>
              )}
            </div>
            {/* Observations are sentences — set them as quiet lines, not tags */}
            {lead.inferred_workflows.length > 0 && (
              <div className="flex flex-col gap-0.5 mt-1.5">
                {lead.inferred_workflows.slice(0, 2).map((w, i) => (
                  <div key={i} className="text-2xs text-muted leading-snug flex gap-1.5">
                    <span className="text-dim shrink-0">—</span>
                    <span>{w}</span>
                  </div>
                ))}
                {lead.inferred_workflows.length > 2 && (
                  <span className="text-2xs text-dim ml-3.5">+{lead.inferred_workflows.length - 2} more</span>
                )}
              </div>
            )}
          </div>

          {/* Quality + Status */}
          <div className="flex items-center gap-2 shrink-0">
            {q && (
              <span
                className={`flex items-center gap-1 text-2xs ${qConfig.color}`}
                title={qTip || 'Looks good to send'}
              >
                <QIcon size={12} />
                {qConfig.label}
              </span>
            )}
            {isApproved && (
              <span className="text-2xs text-green border border-green/30 bg-green-dim rounded px-2 py-0.5">
                Approved
              </span>
            )}
          </div>
        </div>

        {/* Contact Row */}
        <div className="flex items-center gap-2.5 px-4 pb-3 flex-wrap">
          <User size={11} className="text-dim shrink-0" />
          {lead.contact_email || lead.contact_name ? (
            <>
              <span className="text-muted text-xs">
                {[lead.contact_name, lead.contact_title].filter(Boolean).join(' · ')}
              </span>
              {lead.contact_email && (
                <span className="text-xs text-muted font-mono">{lead.contact_email}</span>
              )}
              {/* Sendability + confidence */}
              {lead.sendability && (
                <span
                  className={`text-2xs px-1.5 py-0.5 rounded border ${
                    lead.sendability === 'ready' ? 'text-green border-green/30 bg-green-dim' :
                    lead.sendability === 'review' ? 'text-yellow border-yellow/30 bg-yellow/10' :
                    lead.sendability === 'risky' ? 'text-orange-400 border-score-low/30 bg-orange-900/20' :
                    'text-red border-red/30 bg-red-dim'
                  }`}
                  title={`verification: ${lead.contact_verified ?? 'n/a'} · source: ${lead.contact_source ?? 'n/a'}`}
                >
                  {lead.sendability} · {lead.contact_confidence}
                </span>
              )}
              {lead.contact_source === 'simulated' && (
                <span className="text-2xs text-dim" title="Simulated contact — add APOLLO_API_KEY for real discovery + verification">
                  (simulated)
                </span>
              )}
            </>
          ) : (
            <span className="text-dim text-xs italic">no contact yet</span>
          )}
          {lead.company_domain && (
            <button
              onClick={() => act('enrich', async () => {
                const r = await api.enrichLead(lead.id)
                if (r.ok) { const fresh = await api.getLead(lead.id); onUpdate(fresh) }
              })}
              disabled={loading === 'enrich'}
              className="text-2xs text-muted hover:text-accent border border-border rounded px-1.5 py-0.5 transition-colors disabled:opacity-50"
              title="Find / re-verify the decision-maker via Apollo/Hunter"
            >
              {loading === 'enrich' ? '…' : 'Find contact'}
            </button>
          )}
          <button
            onClick={() => setShowContactForm((s) => !s)}
            className="text-2xs text-muted hover:text-accent border border-border rounded px-1.5 py-0.5 transition-colors"
            title="Paste a contact from Apollo's web app / LinkedIn"
          >
            Paste contact
          </button>
        </div>

        {/* Manual contact entry (free path: Apollo web app / LinkedIn → paste here) */}
        {showContactForm && (
          <div className="mx-4 mb-3 p-2.5 bg-s2 border border-border rounded flex flex-col gap-2">
            <div className="flex gap-2">
              <input value={cName} onChange={(e) => setCName(e.target.value)} placeholder="Name"
                className="flex-1 px-2 py-1 bg-surface border border-border rounded text-xs text-primary placeholder-dim" />
              <input value={cTitle} onChange={(e) => setCTitle(e.target.value)} placeholder="Title"
                className="flex-1 px-2 py-1 bg-surface border border-border rounded text-xs text-primary placeholder-dim" />
            </div>
            <div className="flex gap-2">
              <input value={cEmail} onChange={(e) => setCEmail(e.target.value)} placeholder="email@company.com"
                className="flex-1 px-2 py-1 bg-surface border border-border rounded text-xs text-primary placeholder-dim font-mono" />
              <button onClick={saveContact} disabled={loading === 'contact' || !cEmail}
                className="px-3 py-1 text-xs bg-primary hover:bg-primary/90 text-bg rounded disabled:opacity-50">
                {loading === 'contact' ? '…' : 'Save + verify'}
              </button>
            </div>
          </div>
        )}

        {/* Email Preview — the artifact under review gets its first lines inline */}
        {lead.email_body && (
          <div className="mx-4 mb-3 border border-border rounded bg-s2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full flex flex-col items-stretch px-3 py-2 text-left text-muted hover:text-primary transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Mail size={11} className="shrink-0" />
                  <span className="text-xs font-medium text-primary truncate max-w-[440px]">
                    {lead.subject_line || 'No subject'}
                  </span>
                </div>
                {expanded ? <ChevronUp size={11} className="shrink-0" /> : <ChevronDown size={11} className="shrink-0" />}
              </div>
              {!expanded && (
                <div className="text-2xs text-muted mt-1 leading-relaxed overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {lead.email_body}
                </div>
              )}
            </button>

            {expanded && (
              <div className="border-t border-border px-3 py-3">
                <pre
                  className="text-muted text-xs leading-relaxed whitespace-pre-wrap"
                  style={{ fontFamily: '-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif' }}
                >
                  {lead.email_body}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Suggested Offer */}
        {lead.offer?.name && (
          <div className="mx-4 mb-3 flex items-center gap-2 text-2xs">
            <span className="text-dim">Suggested offer:</span>
            <span className="text-primary font-medium">{lead.offer.name}</span>
            {lead.offer.setup != null && (
              <span className="text-green font-mono">
                ${lead.offer.setup.toLocaleString()} + ${lead.offer.monthly}/mo
              </span>
            )}
          </div>
        )}

        {/* Score Reasoning */}
        {lead.score_reasoning && (
          <div className="mx-4 mb-3 text-2xs text-dim leading-relaxed">
            {lead.score_reasoning}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 px-4 pb-4 pt-1">
          <button
            onClick={openEditor}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-primary border border-border rounded transition-colors"
          >
            <Pencil size={11} />
            Edit
          </button>

          <button
            onClick={handleCopyEmail}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-primary border border-border rounded transition-colors"
          >
            {copied ? <CheckCheck size={11} className="text-green" /> : <Copy size={11} />}
            {copied ? 'Copied' : 'Copy'}
          </button>

          <div className="flex-1" />

          {!isApproved ? (
            <>
              <button
                onClick={handleReject}
                disabled={loading === 'reject'}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-primary border border-border hover:border-muted rounded transition-colors disabled:opacity-50"
              >
                <X size={11} />
                Reject
              </button>
              <button
                onClick={handleApprove}
                disabled={loading === 'approve'}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-green hover:bg-green/10 border border-green/30 rounded transition-colors disabled:opacity-50"
              >
                <Check size={11} />
                {loading === 'approve' ? '…' : 'Approve'}
              </button>
              <button
                onClick={handleApproveAndGmail}
                disabled={loading === 'approve'}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary hover:bg-primary/90 text-bg rounded transition-colors disabled:opacity-50 font-semibold"
                title="Approve and open a pre-filled Gmail draft"
              >
                <Send size={11} />
                Approve → Gmail
              </button>
            </>
          ) : (
            <a
              href={lead.gmail_compose_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => act('sent', async () => {
                await api.markSent(lead.id)
                onUpdate({ ...lead, status: 'sent' })
              })}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue/10 hover:bg-blue/20 text-blue border border-blue/30 rounded transition-colors font-medium"
            >
              <Send size={11} />
              Open in Gmail
            </a>
          )}
        </div>
      </div>

      {showModal && (
        <EmailModal
          lead={lead}
          onClose={() => setShowModal(false)}
          onSave={(updated) => {
            onUpdate(updated)
            setShowModal(false)
          }}
        />
      )}
    </>
  )
}
