import { useState, useEffect } from 'react'
import { X, Save, Copy, Check } from 'lucide-react'
import type { Lead } from '../types'
import { api } from '../api'

type PlaybookEntry = { label: string; when: string; response: string }

interface Props {
  lead: Lead
  onClose: () => void
  onSave: (updated: Lead) => void
}

const tabs = [
  { key: 'email_body', label: 'Initial Email' },
  { key: 'email_long', label: 'Long Version' },
  { key: 'mini_audit', label: 'Mini-Audit' },
  { key: 'follow_up_1', label: 'Follow-up 1' },
  { key: 'follow_up_2', label: 'Follow-up 2' },
  { key: 'breakup_email', label: 'Breakup' },
] as const

type EmailField = (typeof tabs)[number]['key']

export default function EmailModal({ lead, onClose, onSave }: Props) {
  const [activeTab, setActiveTab] = useState<EmailField>('email_body')
  const [subject, setSubject] = useState(lead.subject_line ?? '')
  const [fields, setFields] = useState<Record<EmailField, string>>({
    email_body: lead.email_body ?? '',
    email_long: lead.email_long ?? '',
    mini_audit: lead.mini_audit ?? '',
    follow_up_1: lead.follow_up_1 ?? '',
    follow_up_2: lead.follow_up_2 ?? '',
    breakup_email: lead.breakup_email ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [playbook, setPlaybook] = useState<Record<string, PlaybookEntry> | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const hasObjections = lead.objection_responses && Object.keys(lead.objection_responses).length > 0

  useEffect(() => {
    if ((activeTab as string) === 'replies' && !playbook) {
      api.replyPlaybook(lead.id).then((r) => setPlaybook(r.playbook)).catch(() => {})
    }
  }, [activeTab, playbook, lead.id])

  const copyScenario = (key: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 1500)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.updateLead(lead.id, {
        subject_line: subject,
        ...fields,
      })
      onSave(updated)
    } finally {
      setSaving(false)
    }
  }

  const handleCopy = () => {
    if ((activeTab as string) === 'objections' || (activeTab as string) === 'replies') return
    const text =
      activeTab === 'email_body'
        ? `Subject: ${subject}\n\n${fields[activeTab]}`
        : fields[activeTab]
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-surface border border-border rounded-lg w-[720px] max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
          <div>
            <div className="text-primary font-medium text-md">{lead.company_name}</div>
            <div className="text-muted text-xs mt-0.5">{lead.job_title}</div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-primary p-1 rounded">
            <X size={14} />
          </button>
        </div>

        {/* Subject */}
        <div className="px-5 pt-4 pb-2">
          <label className="text-2xs text-dim uppercase tracking-wider block mb-1.5">Subject Line</label>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full bg-s2 border border-border rounded px-3 py-2 text-sm text-primary placeholder-dim focus:border-accent/50"
            placeholder="Subject line..."
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0 px-5 pt-2 border-b border-border overflow-x-auto">
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-3 py-2 text-xs border-b-2 transition-colors -mb-px whitespace-nowrap ${
                activeTab === key
                  ? 'border-accent text-primary'
                  : 'border-transparent text-muted hover:text-primary'
              }`}
            >
              {label}
            </button>
          ))}
          {hasObjections && (
            <button
              onClick={() => setActiveTab('objections' as EmailField)}
              className={`px-3 py-2 text-xs border-b-2 transition-colors -mb-px whitespace-nowrap ${
                (activeTab as string) === 'objections'
                  ? 'border-accent text-primary'
                  : 'border-transparent text-muted hover:text-primary'
              }`}
            >
              Objections
            </button>
          )}
          <button
            onClick={() => setActiveTab('replies' as EmailField)}
            className={`px-3 py-2 text-xs border-b-2 transition-colors -mb-px whitespace-nowrap ${
              (activeTab as string) === 'replies'
                ? 'border-accent text-primary'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            Reply Playbook
          </button>
        </div>

        {/* Editor / Objections / Reply Playbook */}
        <div className="flex-1 px-5 py-4 overflow-y-auto">
          {(activeTab as string) === 'replies' ? (
            <div className="flex flex-col gap-2.5 min-h-[280px]">
              <div className="text-2xs text-dim mb-1">Copy-paste responses for whatever they reply. Niche-tuned, give-first, built for an operator with no testimonials yet.</div>
              {!playbook ? (
                <div className="text-muted text-xs">Loading playbook…</div>
              ) : (
                Object.entries(playbook).map(([key, entry]) => (
                  <div key={key} className="border border-border rounded bg-s2 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-cyan font-medium">{entry.label}</span>
                      <button
                        onClick={() => copyScenario(key, entry.response)}
                        className="flex items-center gap-1 text-2xs text-dim hover:text-primary transition-colors"
                      >
                        {copiedKey === key ? <Check size={10} className="text-green" /> : <Copy size={10} />}
                        {copiedKey === key ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    <div className="text-2xs text-dim mb-1.5 italic">{entry.when}</div>
                    <pre className="text-xs text-muted leading-relaxed whitespace-pre-wrap" style={{ fontFamily: 'inherit' }}>{entry.response}</pre>
                  </div>
                ))
              )}
            </div>
          ) : (activeTab as string) === 'objections' ? (
            <div className="flex flex-col gap-3 min-h-[280px]">
              {Object.entries(lead.objection_responses || {}).map(([obj, resp]) => (
                <div key={obj} className="border border-border rounded bg-s2 p-3">
                  <div className="text-xs text-yellow font-medium mb-1.5">“{obj}”</div>
                  <div className="text-xs text-muted leading-relaxed">{resp}</div>
                </div>
              ))}
            </div>
          ) : (
            <textarea
              value={fields[activeTab]}
              onChange={(e) => setFields((f) => ({ ...f, [activeTab]: e.target.value }))}
              className="w-full h-full min-h-[280px] bg-s2 border border-border rounded p-3 text-sm text-primary resize-none leading-relaxed focus:border-accent/50"
              placeholder="Email content..."
              style={{ fontFamily: '-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif' }}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-muted hover:text-primary transition-colors"
          >
            {copied ? <Check size={12} className="text-green" /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy to clipboard'}
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-muted hover:text-primary border border-border rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary hover:bg-primary/90 text-bg rounded transition-colors disabled:opacity-50"
            >
              <Save size={11} />
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
