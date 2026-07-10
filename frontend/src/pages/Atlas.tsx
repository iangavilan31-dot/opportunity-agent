import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Play, Pause } from 'lucide-react'
import statesUrl from 'us-atlas/states-albers-10m.json?url'
import { AtlasEngine, type AtlasHover } from '../atlas/engine'
import { projectLeads, HQ } from '../lib/geo'
import { useRealLeads, ts as tsOf } from '../lib/leads'

const PLAY_SECONDS = 22

const fmtDate = (t: number) => {
  const d = new Date(t)
  const day = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  return `${day} · ${time}`
}

export default function Atlas() {
  const { leads, live } = useRealLeads(30000)
  const { points, unmapped } = useMemo(() => projectLeads(leads), [leads])
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<AtlasEngine | null>(null)
  const [hover, setHover] = useState<AtlasHover | null>(null)
  const [hqScreen, setHqScreen] = useState<[number, number] | null>(null)

  // one time parameter drives the whole map
  const [mode, setMode] = useState<'live' | 'scrub' | 'play'>('live')
  const modeRef = useRef(mode)
  modeRef.current = mode
  const tRef = useRef(Date.now())
  const [tLabel, setTLabel] = useState(Date.now())
  const playStart = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const engine = new AtlasEngine(canvas)
    engineRef.current = engine
    engine.onHover = setHover
    engine.onLayout = setHqScreen
    engine.timeFn = () => {
      if (modeRef.current === 'live') { tRef.current = Date.now(); return tRef.current }
      if (modeRef.current === 'play') {
        const [lo, hi] = engine.domain()
        const u = Math.min(1, (performance.now() - playStart.current) / (PLAY_SECONDS * 1000))
        tRef.current = lo + (hi - lo) * u
        if (u >= 1) setMode('live')
      }
      return tRef.current
    }
    engine.start()
    fetch(statesUrl)
      .then((r) => r.json())
      .then((topo) => engine.setGeo(topo))
      .catch(() => {})
    return () => { engineRef.current = null; engine.destroy() }
  }, [])

  useEffect(() => {
    engineRef.current?.setPoints(points)
  }, [points])

  // the date label breathes with the replay without re-rendering the map
  useEffect(() => {
    const iv = window.setInterval(() => setTLabel(tRef.current), 120)
    return () => window.clearInterval(iv)
  }, [])

  const onMove = useCallback((e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    engineRef.current?.setMouse([e.clientX - rect.left, e.clientY - rect.top])
  }, [])
  const onLeave = useCallback(() => engineRef.current?.setMouse(null), [])

  const scrubTo = useCallback((clientX: number, el: HTMLElement) => {
    const rect = el.getBoundingClientRect()
    const u = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    const engine = engineRef.current
    if (!engine) return
    const [lo, hi] = engine.domain()
    tRef.current = lo + (hi - lo) * u
    setTLabel(tRef.current)
    setMode(u >= 0.999 ? 'live' : 'scrub')
  }, [])

  const trackRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const onTrackDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
    if (trackRef.current) scrubTo(e.clientX, trackRef.current)
  }, [scrubTo])
  const onTrackMove = useCallback((e: React.PointerEvent) => {
    if (dragging.current && trackRef.current) scrubTo(e.clientX, trackRef.current)
  }, [scrubTo])
  const onTrackUp = useCallback(() => { dragging.current = false }, [])

  const togglePlay = useCallback(() => {
    if (mode === 'play') { setMode('scrub'); return }
    playStart.current = performance.now()
    setMode('play')
  }, [mode])

  const goLive = useCallback(() => setMode('live'), [])

  const engine = engineRef.current
  const domain = engine ? engine.domain() : [Date.now() - 1, Date.now()]
  const u = Math.max(0, Math.min(1, (tLabel - domain[0]) / Math.max(1, domain[1] - domain[0])))
  const counts = engine ? engine.countsAt(tLabel) : { discovered: 0, reached: 0, replies: 0, won: 0 }

  return (
    <div className="relative h-full w-full overflow-hidden select-none" onMouseMove={onMove} onMouseLeave={onLeave}>
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />

      {/* header */}
      <div className="absolute top-[22px] left-[28px] right-[26px] flex items-center pointer-events-none">
        <div className="text-[13px] font-bold tracking-[0.28em] uppercase text-muted">
          Growth&nbsp;<b className="text-primary">Atlas</b>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 text-[11.5px] font-semibold text-muted">
          <span className={`w-[7px] h-[7px] rounded-full ${mode === 'live' && live ? 'bg-primary pulse-quiet' : 'bg-dim'}`} />
          {mode === 'live' ? (live ? 'Live' : 'Offline') : 'Replay'}
        </div>
      </div>

      {/* HQ label — flips to the left when the point sits near the right edge */}
      {hqScreen && (
        <div
          className="absolute pointer-events-none eyebrow !text-[9.5px] !text-muted whitespace-nowrap"
          style={
            hqScreen[0] > window.innerWidth - 320
              ? { left: hqScreen[0] - 12, top: hqScreen[1] - 6, transform: 'translateX(-100%)' }
              : { left: hqScreen[0] + 12, top: hqScreen[1] - 6 }
          }
        >
          {HQ.label} · HQ
        </div>
      )}

      {/* business card on hover */}
      {hover && (
        <div
          className="absolute z-10 pointer-events-none emerge bg-surface/90 border border-border rounded-[10px] px-3.5 py-2.5 backdrop-blur-sm"
          style={{ left: hover.x + 14, top: hover.y - 10, maxWidth: 260 }}
        >
          <div className="text-[13px] font-bold text-primary leading-tight">{hover.point.lead.company_name}</div>
          <div className="text-[11px] text-muted mt-0.5">{hover.point.city}</div>
          <div className="eyebrow !text-[9px] mt-1.5">{hover.point.lead.status}</div>
        </div>
      )}

      {/* timeline — drag through the company's history */}
      <div className="absolute left-1/2 bottom-[34px] -translate-x-1/2 w-[min(620px,72vw)] flex flex-col gap-3">
        <div className="flex items-baseline justify-between pointer-events-none">
          <div className="eyebrow !text-[10px]">{fmtDate(tLabel)}</div>
          <div className="text-[11.5px] font-medium text-muted num">
            {counts.discovered} discovered · {counts.reached} reached ·{' '}
            <span className={counts.replies > 0 ? 'text-red font-semibold' : ''}>{counts.replies} replies</span>
            {counts.won > 0 && <span className="text-red font-semibold"> · {counts.won} won</span>}
            {unmapped.length > 0 && <span className="text-dim"> · {unmapped.length} unmapped</span>}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={togglePlay}
            title={mode === 'play' ? 'Pause' : 'Replay the growth'}
            className="w-[34px] h-[34px] rounded-full border border-border bg-s2/80 text-primary flex items-center justify-center transition-colors hover:border-muted"
          >
            {mode === 'play' ? <Pause size={13} strokeWidth={2} /> : <Play size={13} strokeWidth={2} className="ml-[2px]" />}
          </button>
          <div
            ref={trackRef}
            className="relative flex-1 h-[26px] cursor-ew-resize"
            onPointerDown={onTrackDown}
            onPointerMove={onTrackMove}
            onPointerUp={onTrackUp}
          >
            <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-[2px] bg-border rounded-full" />
            {/* every real event leaves a notch on the track — sends white, replies red */}
            {points.map((p) => {
              const t = tsOf(p.lead.sent_at)
              if (!t) return null
              const tu = (t - domain[0]) / Math.max(1, domain[1] - domain[0])
              return (
                <div
                  key={`s${p.lead.id}`}
                  className="absolute top-1/2 -translate-y-1/2 w-px h-[8px] bg-primary/30"
                  style={{ left: `${Math.max(0, Math.min(1, tu)) * 100}%` }}
                />
              )
            })}
            {points.map((p) => {
              const t = tsOf(p.lead.replied_at)
              if (!t) return null
              const tu = (t - domain[0]) / Math.max(1, domain[1] - domain[0])
              return (
                <div
                  key={`r${p.lead.id}`}
                  className="absolute top-1/2 -translate-y-1/2 w-[2px] h-[11px] bg-red/80"
                  style={{ left: `${Math.max(0, Math.min(1, tu)) * 100}%` }}
                />
              )
            })}
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 h-[2px] bg-primary/70 rounded-full"
              style={{ width: `${u * 100}%` }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[11px] h-[11px] rounded-full bg-primary"
              style={{ left: `${u * 100}%` }}
            />
          </div>
          <button
            onClick={goLive}
            className={`text-[10.5px] font-bold tracking-[0.18em] uppercase px-3 py-1.5 rounded-[8px] border transition-colors ${
              mode === 'live'
                ? 'text-primary border-border bg-s2/80'
                : 'text-muted border-transparent hover:text-primary'
            }`}
          >
            Live
          </button>
        </div>
      </div>
    </div>
  )
}
