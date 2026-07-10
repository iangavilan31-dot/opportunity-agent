import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { FieldEngine, CENTROIDS } from '../field/engine'
import { useRealLeads, summarize, STAGES } from '../lib/leads'
import type { Lead } from '../types'

async function post<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`, { method: 'POST' })
  if (!r.ok) throw new Error(String(r.status))
  return r.json()
}
async function get<T>(path: string): Promise<T> {
  const r = await fetch(`/api${path}`)
  if (!r.ok) throw new Error(String(r.status))
  return r.json()
}

const money = (n: number) => '$' + Math.round(n).toLocaleString()

export default function Field() {
  const { leads, live, refresh } = useRealLeads(20000)
  const sum = useMemo(() => summarize(leads), [leads])
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<FieldEngine | null>(null)
  const labelRefs = useRef<(HTMLDivElement | null)[]>([])
  const tipRef = useRef<HTMLDivElement>(null)
  const hoverNode = useRef<number>(-1)
  const [focus, setFocus] = useState(-1)
  const [tip, setTip] = useState<Lead | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [note, setNote] = useState('')
  const [gmailOk, setGmailOk] = useState(true)

  // engine lifecycle
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const engine = new FieldEngine(canvas)
    engineRef.current = engine
    const ok = engine.init()
    if (!ok) return () => engine.destroy()
    engine.onFrame = () => {
      // labels bind to the VISIBLE center of mass of their dots (mean of the
      // projected nodes), not the world centroid — perspective can put a
      // centroid's projection far from where the cluster appears on screen
      const sx = new Float32Array(7), sy = new Float32Array(7), sn = new Float32Array(7)
      for (const n of engine.nodes) {
        const p = engine.project(n.world)
        if (!p) continue
        sx[n.stage] += p.x; sy[n.stage] += p.y; sn[n.stage]++
      }
      for (let i = 0; i < 7; i++) {
        const el = labelRefs.current[i]
        if (!el) continue
        if (!sn[i]) { el.style.opacity = '0'; continue }
        el.style.opacity = ''
        el.style.left = sx[i] / sn[i] + 'px'
        el.style.top = sy[i] / sn[i] - 30 + 'px'
      }
      // the hovered business keeps its card pinned to its drifting point
      const t = tipRef.current
      if (t && hoverNode.current >= 0) {
        const n = engine.nodes[hoverNode.current]
        const p = n && engine.project(n.world)
        if (p) { t.style.left = p.x + 14 + 'px'; t.style.top = p.y - 10 + 'px' }
      }
    }
    return () => { engineRef.current = null; engine.destroy() }
  }, [])

  // data → buffers
  useEffect(() => {
    engineRef.current?.setData(leads, summarize(leads).counts)
  }, [leads])

  useEffect(() => {
    get<{ read_ok: boolean }>('/gmail/status').then((s) => setGmailOk(!!s.read_ok)).catch(() => {})
  }, [])

  const applyFocus = useCallback((i: number) => {
    engineRef.current?.setFocus(i)
    setFocus(i)
  }, [])

  const onMove = useCallback((e: React.MouseEvent) => {
    const engine = engineRef.current
    if (!engine) return
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const mx = e.clientX - rect.left, my = e.clientY - rect.top
    engine.setParallax(mx / rect.width)
    // nearest single business first — the closer you look, the more it tells you
    let bi = -1, bd = 14
    for (let i = 0; i < engine.nodes.length; i++) {
      const p = engine.project(engine.nodes[i].world)
      if (!p) continue
      const d = Math.hypot(p.x - mx, p.y - my)
      if (d < bd) { bd = d; bi = i }
    }
    if (bi !== hoverNode.current) {
      hoverNode.current = bi
      setTip(bi >= 0 ? engine.nodes[bi].lead : null)
    }
    if (engine.lockedFocus >= 0) return
    let bc = -1, bcd = 110
    for (let i = 0; i < 7; i++) {
      const p = engine.project(CENTROIDS[i])
      if (!p) continue
      const d = Math.hypot(p.x - mx, p.y - my)
      if (d < bcd) { bcd = d; bc = i }
    }
    applyFocus(bc)
  }, [applyFocus])

  const onLeave = useCallback(() => {
    hoverNode.current = -1
    setTip(null)
    if (engineRef.current && engineRef.current.lockedFocus < 0) applyFocus(-1)
  }, [applyFocus])

  const onClick = useCallback(() => {
    const engine = engineRef.current
    if (!engine) return
    engine.lockFocus(focus)
    if (engine.lockedFocus < 0) applyFocus(-1)
  }, [focus, applyFocus])

  const sync = useCallback(async () => {
    setSyncing(true)
    try {
      const r = await post<{ sent_detected?: number; replies_detected?: number; read_authorized?: boolean }>('/gmail/sync')
      await refresh()
      const engine = engineRef.current
      if (r.sent_detected) engine?.pulse(2)
      if (r.replies_detected) { engine?.pulse(3); engine?.pulse(4, 0.4) }
      let m = `${r.sent_detected || 0} newly sent · ${r.replies_detected || 0} replies`
      if (r.read_authorized === false) m += ' · read off'
      setNote(m)
    } catch {
      setNote('sync failed — is the backend up?')
    } finally {
      setSyncing(false)
      window.setTimeout(() => setNote(''), 4200)
    }
  }, [refresh])

  // the monumental readout only ever states the furthest REAL milestone
  const milestone = useMemo(() => {
    const c = sum.cumulative
    if (sum.earned > 0) return { ey: 'Revenue earned', big: money(sum.earned), hot: true }
    if (c.meeting > 0) return { ey: 'Meetings booked', big: String(c.meeting), hot: true }
    if (c.replied > 0) return { ey: 'Replies', big: String(c.replied), hot: true }
    if (c.sent > 0) return { ey: 'Businesses reached', big: String(c.sent), hot: false }
    return { ey: 'Drafts ready', big: String(sum.counts[0] + sum.counts[1]), hot: false }
  }, [sum])

  const focusName = focus === 6 ? 'Declined' : focus >= 0 ? STAGES[focus].name : ''
  const focusCount = focus === 6 ? sum.declined : focus >= 0 ? sum.counts[focus] : 0
  const focusInfo = focus >= 0
    ? { ey: focusName, big: String(focusCount), hot: focus >= 3 && focus <= 5 && focusCount > 0 }
    : milestone

  return (
    <div
      className="relative h-full w-full overflow-hidden select-none"
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onClick={onClick}
    >
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(120% 90% at 50% 42%, transparent 40%, rgba(0,0,0,.55) 100%)' }}
      />

      {/* cluster labels — empty stages stay silent until asked about */}
      {[...STAGES.map((s, i) => ({ name: s.name, count: sum.counts[i], i })), { name: 'Declined', count: sum.declined, i: 6 }].map(({ name, count, i }) => (
        <div
          key={name}
          ref={(el) => { labelRefs.current[i] = el }}
          className={`absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap pointer-events-none transition-all duration-300 text-[10.5px] font-bold uppercase tracking-[0.16em] ${
            // during focus the camera dives into the cloud and other centroids
            // can project ONTO the focused cluster's dots — only the focused
            // label may speak, or labels visually attach to the wrong dots
            (count === 0 || (focus >= 0 && focus !== i)) ? '!opacity-0' : ''
          } ${focus === i ? (i >= 3 && i <= 5 ? 'text-red' : 'text-primary') : i === 6 ? 'text-dim opacity-80' : 'text-muted opacity-90'}`}
          style={{ textShadow: '0 1px 8px #000' }}
        >
          {name}
          <i className={`not-italic ml-1.5 num ${focus === i ? 'text-primary' : 'text-dim'}`}>{count}</i>
        </div>
      ))}

      {/* single-business card — the moment "every dot is real" pays off */}
      {tip && (
        <div
          ref={tipRef}
          className="absolute z-10 pointer-events-none emerge bg-s3/95 border border-muted/40 rounded-[10px] px-4 py-3 backdrop-blur-md"
          style={{ maxWidth: 280, boxShadow: '0 10px 34px rgba(0,0,0,0.65)' }}
        >
          <div className="text-[13.5px] font-bold text-primary leading-tight">{tip.company_name}</div>
          <div className="text-[11px] text-muted mt-1">{tip.job_location || '—'}</div>
          <div className="flex items-baseline gap-5 mt-2.5">
            <span>
              <span className="eyebrow !text-[8.5px] mr-1.5">Stage</span>
              <b className="text-[11.5px] text-primary capitalize">{tip.status === 'rejected' ? 'Declined' : tip.status}</b>
            </span>
            <span>
              <span className="eyebrow !text-[8.5px] mr-1.5">Score</span>
              <b className="text-[11.5px] num text-primary">{tip.automation_score}</b>
            </span>
          </div>
        </div>
      )}

      {/* top */}
      <div className="absolute top-[22px] left-[28px] right-[26px] flex items-center gap-3.5">
        <div className="text-[13px] font-bold tracking-[0.28em] uppercase text-muted">
          Web&nbsp;<b className="text-primary">Machine</b>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 text-[11.5px] font-semibold text-muted">
          <span className={`w-[7px] h-[7px] rounded-full ${live ? 'bg-primary pulse-quiet' : 'bg-dim'}`} />
          {live == null ? 'Connecting…' : live ? 'Live' : 'Offline'}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); sync() }}
          disabled={syncing}
          className="inline-flex items-center gap-2 text-[11.5px] font-bold tracking-[0.08em] uppercase text-primary bg-s2 border border-border rounded-[9px] px-3.5 py-2 transition-colors hover:border-muted disabled:opacity-50"
        >
          <RefreshCw size={13} strokeWidth={2} className={syncing ? 'animate-spin' : ''} />
          Sync
        </button>
      </div>

      {/* the monumental readout */}
      <div className="absolute left-[28px] bottom-[40px] max-w-[min(46vw,560px)] pointer-events-none">
        <div className="eyebrow flex items-center gap-2.5 mb-2.5">
          <span className={`w-[9px] h-[9px] rounded-full transition-opacity duration-300 ${focusInfo.hot ? 'bg-red opacity-100' : 'opacity-0 bg-primary'}`} />
          {focusInfo.ey}
        </div>
        <div
          className={`monument transition-colors duration-300 ${focusInfo.hot ? 'text-red' : ''}`}
          style={{ fontSize: 'clamp(52px, 8.2vw, 116px)' }}
        >
          {focusInfo.big}
        </div>
        <div className="mt-4 text-[14px] font-medium text-muted max-w-[40ch] leading-relaxed min-h-[21px]">
          {focus >= 0
            ? `${focusCount} ${focusCount === 1 ? 'business' : 'businesses'} in ${focusName} right now.`
            : `${sum.discovered} real businesses discovered · ${sum.declined} declined · ${money(sum.earned)} earned. Every point is one real company.`}
        </div>
      </div>

      {/* stage ledger — swallow mousemove so hovering a row isn't immediately
          un-focused by the canvas picker underneath */}
      <div
        className="absolute right-[26px] bottom-[40px] flex flex-col gap-0.5 text-right"
        onMouseMove={(e) => e.stopPropagation()}
      >
        {STAGES.map((s, i) => (
          <div
            key={s.key}
            className={`grid grid-cols-[1fr_auto] items-baseline gap-4 py-[7px] cursor-pointer transition-opacity ${
              focus === i ? 'opacity-100' : 'opacity-85 hover:opacity-100'
            }`}
            onMouseEnter={() => applyFocus(i)}
            onMouseLeave={() => { if ((engineRef.current?.lockedFocus ?? -1) < 0) applyFocus(-1) }}
            onClick={(e) => { e.stopPropagation(); engineRef.current?.lockFocus(i) }}
          >
            <span className={`text-[11.5px] font-semibold tracking-[0.14em] uppercase ${
              focus === i ? (i >= 3 && i <= 5 && sum.counts[i] > 0 ? 'text-red' : 'text-primary') : 'text-muted'
            }`}>
              {s.name}
            </span>
            <span className="text-[19px] font-extrabold num text-primary min-w-[2ch]">{sum.counts[i]}</span>
          </div>
        ))}
        <div
          className={`grid grid-cols-[1fr_auto] items-baseline gap-4 pt-3 mt-1 border-t border-border-subtle cursor-pointer transition-opacity ${focus === 6 ? 'opacity-100' : 'opacity-75 hover:opacity-100'}`}
          onMouseEnter={() => applyFocus(6)}
          onMouseLeave={() => { if ((engineRef.current?.lockedFocus ?? -1) < 0) applyFocus(-1) }}
          onClick={(e) => { e.stopPropagation(); engineRef.current?.lockFocus(6) }}
        >
          <span className={`text-[10.5px] font-semibold tracking-[0.14em] uppercase ${focus === 6 ? 'text-primary' : 'text-muted'}`}>Declined</span>
          <span className="text-[13px] font-bold num text-muted">{sum.declined}</span>
        </div>
        {/* the encoding, stated on the screen it governs */}
        <div className="mt-4 text-right text-[10.5px] text-muted/90 leading-relaxed pointer-events-none">
          every glow is one real business · size = opportunity<br />
          red = only when a business answers
        </div>
      </div>

      {/* quiet footer line */}
      <div className="absolute left-1/2 bottom-[20px] -translate-x-1/2 text-[11.5px] font-medium text-dim text-center pointer-events-none">
        {note || (!gmailOk ? 'Replies off — run python gmail_read.py once to track them.' : '')}
      </div>
    </div>
  )
}
