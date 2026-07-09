import { useEffect, useState } from 'react'
import { Save, Check, User } from 'lucide-react'
import { api } from '../api'

export default function Settings() {
  const [form, setForm] = useState({
    sender_name: '', positioning: '', calendar_link: '', site_link: '',
    sender_email: '', postal_address: '',
  })
  const [preview, setPreview] = useState('')
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getSettings().then((s) => {
      setForm({
        sender_name: s.sender_name, positioning: s.positioning,
        calendar_link: s.calendar_link, site_link: s.site_link ?? '',
        sender_email: s.sender_email, postal_address: s.postal_address ?? '',
      })
      setPreview(s.signature_preview)
    })
  }, [])

  const save = async () => {
    setLoading(true)
    try {
      const r = await api.saveSettings(form)
      setPreview(r.signature_preview)
      setSaved(true)
      setTimeout(() => setSaved(false), 1800)
    } finally {
      setLoading(false)
    }
  }

  const field = (key: keyof typeof form, label: string, placeholder: string, hint?: string) => (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs text-muted">{label}</label>
      <input
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
        className="px-3 py-2 bg-s2 border border-border rounded text-sm text-primary placeholder-dim focus:border-accent/50"
      />
      {hint && <span className="text-2xs text-dim">{hint}</span>}
    </div>
  )

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 py-4 border-b border-border">
        <h1 className="text-primary font-semibold text-xl">Settings</h1>
        <p className="text-muted text-xs mt-0.5">Your sender profile — auto-filled into the signature of every email</p>
      </div>

      <div className="p-6 max-w-xl flex flex-col gap-5">
        <div className="bg-surface border border-border rounded-lg p-5 flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm text-primary font-medium">
            <User size={14} /> Sender Profile
          </div>

          {field('sender_name', 'Your name', 'Ian Gavilan', 'Replaces "[Your name]" in every email')}
          {field('positioning', 'One-line positioning (optional)', 'I automate back-office workflows for small teams', 'Appended after your name as a credibility signal')}
          {field('calendar_link', 'Calendar link (optional)', 'cal.com/ian/15min', 'Only if it is a REAL booking page — a dead link kills trust')}
          {field('site_link', 'Studio site link (optional)', 'https://gavika.pages.dev', 'Shown in your signature (e.g. gavika.pages.dev)')}
          {field('sender_email', 'Sending email (optional)', 'ian@youragency.com', 'For your reference — used when exporting .eml')}
          {field('postal_address', 'Mailing address (CAN-SPAM)', 'Gavika · PO Box 123, Phoenix, AZ 85001', 'Required by law in every commercial email — a PO Box works and keeps your home address private')}

          <button
            onClick={save}
            disabled={loading}
            className="flex items-center justify-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded text-sm font-medium transition-colors disabled:opacity-50 self-start"
          >
            {saved ? <Check size={13} /> : <Save size={13} />}
            {saved ? 'Saved' : loading ? 'Saving…' : 'Save Profile'}
          </button>
        </div>

        {/* Live signature preview */}
        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-xs text-muted mb-3">Signature preview (how every email signs off)</div>
          <pre
            className="text-sm text-primary whitespace-pre-wrap leading-relaxed border-l-2 border-accent/40 pl-3"
            style={{ fontFamily: '-apple-system, BlinkMacSystemFont, Inter, system-ui, sans-serif' }}
          >
{`— ${preview || '[Your name]'}`}
          </pre>
          {(!form.sender_name) && (
            <div className="text-2xs text-yellow mt-3">
              Set your name above — until then, emails ship with the "[Your name]" placeholder.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
