import { geoPath } from 'd3-geo'
import { feature, mesh } from 'topojson-client'
import { MAP_W, MAP_H, projectHQ, type MapPoint } from '../lib/geo'
import { ts } from '../lib/leads'

// ─────────────────────────────────────────────────────────────────────────────
// GROWTH ATLAS — the living history of the agency on a quiet custom map.
// Everything drawn is a real event at a real time: a business discovered, an
// email sent (a connection grows from HQ and permanently remains), a reply
// (red ripple), a meeting (prominence), a win (permanent landmark).
// One time parameter T drives it all, so "live" and "replay" are the same code.
// ─────────────────────────────────────────────────────────────────────────────

interface TimedPoint extends MapPoint {
  tDisc: number | null
  tSent: number | null
  tReplied: number | null
  tMeeting: number | null
  rejected: boolean
  won: boolean
  breath: number // per-point phase so idle motion never syncs
}

export interface AtlasHover {
  x: number
  y: number
  point: TimedPoint
}

const EASE = (u: number) => 1 - Math.pow(1 - u, 3)
const clamp01 = (u: number) => Math.max(0, Math.min(1, u))

export class AtlasEngine {
  private ctx: CanvasRenderingContext2D
  private staticLayer: HTMLCanvasElement | null = null
  private topo: unknown = null
  private points: TimedPoint[] = []
  private raf = 0
  private hq = projectHQ()
  // fit transform map(975×610) → canvas
  private s = 1
  private ox = 0
  private oy = 0
  private dpr = 1
  /** replay/live time, epoch ms; live mode tracks Date.now() each frame */
  timeFn: () => number = () => Date.now()
  growMs = 1500
  onHover: ((h: AtlasHover | null) => void) | null = null
  onLayout: ((hqScreen: [number, number]) => void) | null = null
  private hovered: TimedPoint | null = null
  private mouse: [number, number] | null = null
  private visHandler = () => {
    if (document.hidden) { cancelAnimationFrame(this.raf); this.raf = 0 }
    else if (!this.raf) this.frame()
  }

  constructor(private canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')!
  }

  start() {
    window.addEventListener('resize', this.resizeBound)
    document.addEventListener('visibilitychange', this.visHandler)
    this.resize()
    this.frame()
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    window.removeEventListener('resize', this.resizeBound)
    document.removeEventListener('visibilitychange', this.visHandler)
  }

  setGeo(topo: unknown) {
    this.topo = topo
    this.staticLayer = null
    this.resize()
  }

  setPoints(pts: MapPoint[]) {
    this.points = pts.map((p, i) => {
      const status = p.lead.status as string
      return {
        ...p,
        tDisc: ts(p.lead.created_at),
        tSent: ts(p.lead.sent_at),
        tReplied: ts(p.lead.replied_at),
        tMeeting: ts(p.lead.meeting_booked_at),
        rejected: status === 'rejected',
        won: status === 'won' || status === 'closed',
        breath: (i * 0.618) % 1,
      }
    })
    const span = this.domain()
    this.growMs = Math.max(1200, (span[1] - span[0]) * 0.015)
  }

  domain(): [number, number] {
    let lo = Infinity
    for (const p of this.points) {
      if (p.tDisc) lo = Math.min(lo, p.tDisc)
      if (p.tSent) lo = Math.min(lo, p.tSent)
    }
    const now = Date.now()
    if (!Number.isFinite(lo)) lo = now - 3600_000
    return [lo, now]
  }

  countsAt(T: number): { discovered: number; reached: number; replies: number; won: number } {
    let discovered = 0, reached = 0, replies = 0, won = 0
    for (const p of this.points) {
      if (p.tDisc && p.tDisc <= T) discovered++
      if (p.tSent && p.tSent <= T) reached++
      if (p.tReplied && p.tReplied <= T) replies++
      if (p.won && ((p.tMeeting ?? p.tReplied ?? p.tSent ?? 0) <= T)) won++
    }
    return { discovered, reached, replies, won }
  }

  setMouse(m: [number, number] | null) { this.mouse = m }

  private resizeBound = () => this.resize()
  private resize() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight
    if (!w || !h) return
    this.dpr = Math.min(window.devicePixelRatio || 1, 2)
    this.canvas.width = Math.floor(w * this.dpr)
    this.canvas.height = Math.floor(h * this.dpr)
    // fit the 975×610 map with editorial margins; extra room below for the timeline
    const mx = 56, mtop = 64, mbot = 132
    this.s = Math.min((w - mx * 2) / MAP_W, (h - mtop - mbot) / MAP_H)
    this.ox = (w - MAP_W * this.s) / 2
    this.oy = mtop + (h - mtop - mbot - MAP_H * this.s) / 2
    this.renderStatic()
    this.onLayout?.(this.toScreen(this.hq[0], this.hq[1]))
  }

  private toScreen(x: number, y: number): [number, number] {
    return [this.ox + x * this.s, this.oy + y * this.s]
  }

  /** hit-test in CSS pixels */
  pick(mx: number, my: number): TimedPoint | null {
    const T = this.timeFn()
    let best: TimedPoint | null = null, bd = 11
    for (const p of this.points) {
      if (!p.tDisc || p.tDisc > T) continue
      const [sx, sy] = this.toScreen(p.x, p.y)
      const d = Math.hypot(sx - mx, sy - my)
      if (d < bd) { bd = d; best = p }
    }
    return best
  }

  private renderStatic() {
    if (!this.topo) return
    const w = this.canvas.width, h = this.canvas.height
    const layer = document.createElement('canvas')
    layer.width = w; layer.height = h
    const c = layer.getContext('2d')!
    c.scale(this.dpr, this.dpr)
    c.translate(this.ox, this.oy)
    c.scale(this.s, this.s)
    const t = this.topo as { objects: { states: object; nation: object } }
    const path = geoPath(null, c)
    // the country sits barely above the void — presence, not decoration
    c.beginPath(); path(feature(t as never, t.objects.nation as never) as never)
    c.fillStyle = '#0a0a0c'; c.fill()
    c.beginPath(); path(mesh(t as never, t.objects.states as never, ((a: unknown, b: unknown) => a !== b) as never) as never)
    c.strokeStyle = '#1a1a1f'; c.lineWidth = 0.7 / this.s; c.stroke()
    c.beginPath(); path(feature(t as never, t.objects.nation as never) as never)
    c.strokeStyle = '#2b2b33'; c.lineWidth = 1.1 / this.s; c.stroke()
    this.staticLayer = layer
  }

  private frame = () => {
    this.raf = requestAnimationFrame(this.frame)
    const ctx = this.ctx
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight
    const T = this.timeFn()
    const now = performance.now() / 1000

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    if (this.staticLayer) ctx.drawImage(this.staticLayer, 0, 0, w, h)

    const [hx, hy] = this.toScreen(this.hq[0], this.hq[1])

    // connections first — the network under the businesses
    for (const p of this.points) {
      if (!p.tSent || p.tSent > T) continue
      const u = EASE(clamp01((T - p.tSent) / this.growMs))
      const [px, py] = this.toScreen(p.x, p.y)
      this.connection(ctx, hx, hy, px, py, u, p)
    }

    // businesses
    for (const p of this.points) {
      if (!p.tDisc || p.tDisc > T) continue
      const [px, py] = this.toScreen(p.x, p.y)
      const born = clamp01((T - p.tDisc) / 900)
      const replied = !!p.tReplied && p.tReplied <= T
      const meeting = !!p.tMeeting && p.tMeeting <= T
      const sent = !!p.tSent && p.tSent <= T
      const breath = 0.5 + 0.5 * Math.sin(now * 1.1 + p.breath * Math.PI * 2)

      if (p.won) {
        // permanent landmark
        const halo = 9 + breath * 2
        const grad = ctx.createRadialGradient(px, py, 0, px, py, halo)
        grad.addColorStop(0, 'rgba(229,72,77,0.5)')
        grad.addColorStop(1, 'rgba(229,72,77,0)')
        ctx.fillStyle = grad
        ctx.beginPath(); ctx.arc(px, py, halo, 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = '#ff8a86'
        ctx.beginPath(); ctx.arc(px, py, 3.6, 0, Math.PI * 2); ctx.fill()
        continue
      }
      if (replied || meeting) {
        // an open conversation ripples, quietly, forever
        const period = 7, tt = (now + p.breath * period) % period
        if (tt < 2.6) {
          const ru = tt / 2.6
          ctx.strokeStyle = `rgba(229,72,77,${0.28 * (1 - ru)})`
          ctx.lineWidth = 1
          ctx.beginPath(); ctx.arc(px, py, 4 + ru * (meeting ? 22 : 15), 0, Math.PI * 2); ctx.stroke()
        }
        // the strong crossing ripple when replay passes the reply moment
        const rt = p.tReplied ? (T - p.tReplied) / 2200 : 2
        if (rt >= 0 && rt < 1) {
          ctx.strokeStyle = `rgba(229,72,77,${0.5 * (1 - rt)})`
          ctx.lineWidth = 1.4
          ctx.beginPath(); ctx.arc(px, py, 4 + rt * 30, 0, Math.PI * 2); ctx.stroke()
        }
        ctx.fillStyle = meeting ? '#f0605f' : '#e5484d'
        ctx.beginPath(); ctx.arc(px, py, (meeting ? 3.1 : 2.6) * born, 0, Math.PI * 2); ctx.fill()
        continue
      }
      if (sent) {
        ctx.fillStyle = `rgba(242,242,245,${(0.75 + breath * 0.2) * born})`
        ctx.beginPath(); ctx.arc(px, py, 2.1 * born, 0, Math.PI * 2); ctx.fill()
        continue
      }
      // discovered (or declined — history stays, barely there)
      ctx.fillStyle = p.rejected ? 'rgba(116,116,126,0.15)' : `rgba(138,138,148,${0.6 * born})`
      ctx.beginPath(); ctx.arc(px, py, 2.1 * born, 0, Math.PI * 2); ctx.fill()
    }

    // HQ — where every line begins
    ctx.strokeStyle = 'rgba(245,245,246,0.55)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.arc(hx, hy, 5.5 + Math.sin(now * 1.4) * 0.8, 0, Math.PI * 2); ctx.stroke()
    ctx.fillStyle = '#f5f5f6'
    ctx.beginPath(); ctx.arc(hx, hy, 2.2, 0, Math.PI * 2); ctx.fill()

    // hover reporting (DOM card lives in React)
    if (this.mouse) {
      const hit = this.pick(this.mouse[0], this.mouse[1])
      if (hit !== this.hovered) {
        this.hovered = hit
        const sp = hit ? this.toScreen(hit.x, hit.y) : null
        this.onHover?.(hit && sp ? { x: sp[0], y: sp[1], point: hit } : null)
      } else if (hit) {
        const sp = this.toScreen(hit.x, hit.y)
        this.onHover?.({ x: sp[0], y: sp[1], point: hit })
      }
    } else if (this.hovered) {
      this.hovered = null
      this.onHover?.(null)
    }
  }

  private connection(
    ctx: CanvasRenderingContext2D,
    x0: number, y0: number, x1: number, y1: number,
    u: number, p: TimedPoint,
  ) {
    if (u <= 0) return
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2
    const dx = x1 - x0, dy = y1 - y0
    const d = Math.hypot(dx, dy) || 1
    // perpendicular lift, always arcing upward; per-business variance feathers
    // the bundle apart so 34 sends read as 34 strands, not one rope
    let nx = -dy / d, ny = dx / d
    if (ny > 0) { nx = -nx; ny = -ny }
    const lift = Math.min(d * (0.10 + p.breath * 0.14), 78)
    const cx = mx + nx * lift, cy = my + ny * lift
    const hot = (!!p.tReplied || p.won)
    ctx.strokeStyle = p.won
      ? 'rgba(229,72,77,0.55)'
      : hot ? 'rgba(229,72,77,0.35)' : 'rgba(238,238,242,0.16)'
    ctx.lineWidth = p.won ? 1.3 : 0.8
    ctx.beginPath()
    const steps = 26
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * u
      const a = 1 - t
      const qx = a * a * x0 + 2 * a * t * cx + t * t * x1
      const qy = a * a * y0 + 2 * a * t * cy + t * t * y1
      if (i === 0) ctx.moveTo(qx, qy); else ctx.lineTo(qx, qy)
    }
    ctx.stroke()
    // a bright head while the line is still traveling
    if (u < 1) {
      const a = 1 - u
      const qx = a * a * x0 + 2 * a * u * cx + u * u * x1
      const qy = a * a * y0 + 2 * a * u * cy + u * u * y1
      ctx.fillStyle = 'rgba(245,245,246,0.9)'
      ctx.beginPath(); ctx.arc(qx, qy, 1.6, 0, Math.PI * 2); ctx.fill()
    }
  }
}
