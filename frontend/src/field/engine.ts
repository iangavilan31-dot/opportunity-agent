import type { Lead } from '../types'
import { stageOf, ts } from '../lib/leads'

// ─────────────────────────────────────────────────────────────────────────────
// THE BUSINESS FIELD — the Web Machine particle language.
// One WebGL draw call. Every bright core is exactly one real business; ambient
// dust only gives a cluster atmosphere and scales only with real counts.
// Size = opportunity score. Brightness = confidence. Movement = alive.
// Red exists ONLY where real business activity exists (reply / meeting / won).
// Positions are deterministic per lead id — the field is a place, not confetti.
// ─────────────────────────────────────────────────────────────────────────────

export interface FieldNode {
  lead: Lead
  stage: number
  world: [number, number, number]
}

// funnel spiral: later stages spiral inward + up toward the WON core
export const CENTROIDS: [number, number, number][] = Array.from({ length: 6 }, (_, i) => {
  const a = i * 0.92 + 0.4
  const r = 6.4 - i * 1.05
  const y = (i - 2.4) * 0.62
  return [Math.cos(a) * r, y, Math.sin(a) * r]
})
// declined businesses are still real businesses — they live outside the
// funnel, dim and low, so "every point is one real company" is literally true
export const DECLINED_STAGE = 6
CENTROIDS.push([-6.8, -2.5, -3.0])

function hash(n: number): number {
  let x = (n | 0) + 0x9e3779b9
  x = Math.imul(x ^ (x >>> 16), 0x21f0aaad)
  x = Math.imul(x ^ (x >>> 15), 0x735a2d97)
  return ((x ^ (x >>> 15)) >>> 0) / 0xffffffff
}
// deterministic ~gaussian from three hashes
function g(seed: number, sd: number): number {
  return (hash(seed) + hash(seed * 31 + 7) + hash(seed * 131 + 13) - 1.5) * sd
}

const VERT = `
attribute vec3 aPos; attribute vec3 aCen; attribute float aStage;
attribute float aRand; attribute float aCore; attribute float aSize;
attribute float aAct;
uniform mat4 uVP; uniform float uTime; uniform float uFocus; uniform float uFocusMix;
uniform float uPulse[7]; uniform float uDpr; uniform float uBloom;
varying float vA; varying float vStage; varying float vCore; varying float vPulse;
varying float vBloom;
void main(){
  vec3 p = aPos;
  float drift = 0.14;
  p += drift*vec3(sin(uTime*0.30+aRand*6.28), cos(uTime*0.26+aRand*4.10), sin(uTime*0.34+aRand*2.30));
  int si = int(aStage+0.5);
  float pl = uPulse[si];
  vPulse = pl;
  vec3 outw = normalize(aPos-aCen+0.0001);
  p += outw*pl*1.7*(0.4+aRand);
  vec4 mv = uVP*vec4(p,1.0);
  gl_Position = mv;
  float focused = 1.0-uFocusMix*step(0.5, abs(aStage-uFocus));
  float act = aAct*(0.5+0.5*sin(uTime*2.2+aRand*6.28));
  float won = step(4.5, aStage)*(1.0-step(5.5, aStage));
  float dec = step(5.5, aStage);
  float base = mix(1.7, 4.2+3.2*aSize, aCore) + pl*3.0 + act*1.1 + won*2.6 - dec*1.4;
  base *= mix(1.0, 7.0, uBloom);
  gl_PointSize = base*uDpr*(10.5/max(mv.w,0.4));
  // luminance floor: every real business is unambiguously visible
  vA = (mix(0.30, 0.74+0.24*aSize, aCore)) * focused * mix(1.0, 0.13, uBloom) * mix(1.0, 0.42, dec);
  // dust never wears red — only a real business that answered may
  vStage = mix(min(aStage, 2.0), aStage, aCore); vCore = aCore; vBloom = uBloom;
}`

const FRAG = `
precision mediump float;
varying float vA; varying float vStage; varying float vCore; varying float vPulse;
varying float vBloom;
void main(){
  vec2 d = gl_PointCoord-0.5; float r = length(d);
  if(r>0.5) discard;
  float won = step(4.5, vStage)*(1.0-step(5.5, vStage));
  float dec = step(5.5, vStage);
  // won nodes carry a permanent soft halo; the bloom pass is all halo
  // (edge order matters: reversed-edge smoothstep is undefined on some drivers)
  float fall = mix(mix(0.02, 0.30, won), 0.0, vBloom);
  float a = (1.0 - smoothstep(fall, 0.5, r))*vA;
  // monochrome until the business answers — then, and only then, red
  vec3 early = vec3(0.70, 0.72, 0.78);
  vec3 sent  = vec3(0.93, 0.93, 0.96);
  vec3 red   = vec3(0.898, 0.282, 0.302);
  vec3 redHi = vec3(1.0, 0.52, 0.50);
  vec3 col = mix(early, sent, smoothstep(0.8, 2.0, vStage));
  col = mix(col, red, smoothstep(2.2, 3.0, vStage));
  col = mix(col, redHi, won*0.65);
  col = mix(col, vec3(0.44, 0.45, 0.49), dec);
  col = mix(col, vec3(1.0), vPulse*0.5);
  col += vCore*0.12;
  gl_FragColor = vec4(col, a);
}`

function perspective(fovy: number, aspect: number, near: number, far: number): number[] {
  const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far)
  return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0]
}
function lookAt(eye: number[], ctr: number[], up: number[]): number[] {
  let z0 = eye[0] - ctr[0], z1 = eye[1] - ctr[1], z2 = eye[2] - ctr[2]
  const zl = 1 / Math.hypot(z0, z1, z2); z0 *= zl; z1 *= zl; z2 *= zl
  let x0 = up[1] * z2 - up[2] * z1, x1 = up[2] * z0 - up[0] * z2, x2 = up[0] * z1 - up[1] * z0
  let xl = Math.hypot(x0, x1, x2) || 1; xl = 1 / xl; x0 *= xl; x1 *= xl; x2 *= xl
  const y0 = z1 * x2 - z2 * x1, y1 = z2 * x0 - z0 * x2, y2 = z0 * x1 - z1 * x0
  return [x0, y0, z0, 0, x1, y1, z1, 0, x2, y2, z2, 0,
    -(x0 * eye[0] + x1 * eye[1] + x2 * eye[2]), -(y0 * eye[0] + y1 * eye[1] + y2 * eye[2]), -(z0 * eye[0] + z1 * eye[1] + z2 * eye[2]), 1]
}
function mul(a: number[], b: number[]): number[] {
  const o = new Array(16)
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let s = 0
    for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]
    o[c * 4 + r] = s
  }
  return o
}

export interface Projected { x: number; y: number; w: number }

export class FieldEngine {
  private gl: WebGLRenderingContext | null = null
  private prog: WebGLProgram | null = null
  private buffers: Record<string, WebGLBuffer> = {}
  private n = 0
  private raf = 0
  private t0 = performance.now()
  private vp: number[] | null = null
  private pulses = [0, 0, 0, 0, 0, 0, 0]
  private cam = { az: 0.5, el: 0.16, r: 15.5, azT: 0.5, elT: 0.16, rT: 15.5, cx: 0, cy: 0, cz: 0, cxT: 0, cyT: 0, czT: 0 }
  private mouseAz = 0
  nodes: FieldNode[] = []
  focus = -1
  private locked = -1
  onFrame: (() => void) | null = null
  private visHandler = () => {
    if (document.hidden) { cancelAnimationFrame(this.raf); this.raf = 0 }
    else if (!this.raf) this.frame()
  }

  constructor(private canvas: HTMLCanvasElement) {}

  init(): boolean {
    const gl = this.canvas.getContext('webgl', { antialias: true, alpha: false, premultipliedAlpha: false })
    if (!gl) return false
    this.gl = gl
    const sh = (type: number, src: string) => {
      const s = gl.createShader(type)!
      gl.shaderSource(s, src); gl.compileShader(s)
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(s))
      return s
    }
    const prog = gl.createProgram()!
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT))
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG))
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { console.error(gl.getProgramInfoLog(prog)); return false }
    gl.useProgram(prog)
    this.prog = prog
    gl.disable(gl.DEPTH_TEST)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
    this.resize()
    window.addEventListener('resize', this.resizeBound)
    document.addEventListener('visibilitychange', this.visHandler)
    this.frame()
    return true
  }

  private resizeBound = () => this.resize()
  resize() {
    const gl = this.gl; if (!gl) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight
    this.canvas.width = Math.floor(w * dpr); this.canvas.height = Math.floor(h * dpr)
    gl.viewport(0, 0, this.canvas.width, this.canvas.height)
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    this.raf = 0
    window.removeEventListener('resize', this.resizeBound)
    document.removeEventListener('visibilitychange', this.visHandler)
    // NEVER loseContext() here: React StrictMode re-runs effects on the same
    // canvas, and a deliberately-lost context leaves the remounted engine dead
    // (Chrome composites the lost alpha:false canvas as solid white).
    this.gl = null
  }

  /** Rebuild attribute buffers from real leads. Deterministic per lead id. */
  setData(leads: Lead[], counts: number[]) {
    const gl = this.gl, prog = this.prog
    const pos: number[] = [], cen: number[] = [], stg: number[] = [], rnd: number[] = []
    const core: number[] = [], size: number[] = [], act: number[] = []
    const dayAgo = Date.now() - 24 * 3600 * 1000
    this.nodes = []
    const declinedCount = leads.reduce((n, l) => n + (stageOf(l) < 0 ? 1 : 0), 0)
    for (const lead of leads) {
      let s = stageOf(lead)
      if (s < 0) s = DECLINED_STAGE
      const c = CENTROIDS[s]
      const n = s === DECLINED_STAGE ? declinedCount : counts[s]
      const spread = 0.7 + Math.min(n, 80) * 0.013
      const w: [number, number, number] = [
        c[0] + g(lead.id, spread) * 1.6,
        c[1] + g(lead.id * 3 + 1, spread),
        c[2] + g(lead.id * 5 + 2, spread) * 1.6,
      ]
      this.nodes.push({ lead, stage: s, world: w })
      const last = ts(lead.sent_at) ?? ts(lead.replied_at) ?? ts(lead.created_at)
      pos.push(...w); cen.push(...c); stg.push(s); rnd.push(hash(lead.id * 17 + 3))
      core.push(1)
      size.push(Math.max(0.25, Math.min(1, (lead.automation_score || 40) / 100)))
      act.push(last && last > dayAgo ? 1 : 0)
    }
    // NO ambient dust. The caption promises "every point is one real
    // company" — so every point IS one. Atmosphere comes from the bloom pass,
    // which only ever halos real businesses.
    this.n = stg.length
    if (!gl || !prog) return
    const mk = (name: string, arr: number[], sz: number) => {
      const b = this.buffers[name] || (this.buffers[name] = gl.createBuffer()!)
      gl.bindBuffer(gl.ARRAY_BUFFER, b)
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW)
      const loc = gl.getAttribLocation(prog, name)
      gl.enableVertexAttribArray(loc)
      gl.vertexAttribPointer(loc, sz, gl.FLOAT, false, 0, 0)
    }
    mk('aPos', pos, 3); mk('aCen', cen, 3); mk('aStage', stg, 1)
    mk('aRand', rnd, 1); mk('aCore', core, 1); mk('aSize', size, 1); mk('aAct', act, 1)
  }

  pulse(stage: number, amount = 1) {
    if (stage >= 0 && stage < 6) this.pulses[stage] = Math.max(this.pulses[stage], amount)
  }

  /** Cursor parallax — a few milliradians, felt not seen. */
  setParallax(nx: number) { this.mouseAz = (nx - 0.5) * 0.07 }

  setFocus(i: number) {
    if (this.focus === i) return
    this.focus = i
    const cam = this.cam
    if (i >= 0) {
      const c = CENTROIDS[i]
      cam.cxT = c[0] * 0.55; cam.cyT = c[1] * 0.6; cam.czT = c[2] * 0.55
      cam.rT = 12.5; cam.elT = 0.24
      cam.azT = Math.atan2(c[2], c[0]) + 1.4
    } else {
      cam.cxT = 0; cam.cyT = 0; cam.czT = 0; cam.rT = 15.5; cam.elT = 0.16
    }
  }
  lockFocus(i: number) { this.locked = this.locked === i ? -1 : i }
  get lockedFocus() { return this.locked }

  project(p: [number, number, number]): Projected | null {
    const VP = this.vp; if (!VP) return null
    const x = VP[0] * p[0] + VP[4] * p[1] + VP[8] * p[2] + VP[12]
    const y = VP[1] * p[0] + VP[5] * p[1] + VP[9] * p[2] + VP[13]
    const w = VP[3] * p[0] + VP[7] * p[1] + VP[11] * p[2] + VP[15]
    if (w <= 0) return null
    const cw = this.canvas.clientWidth, ch = this.canvas.clientHeight
    return { x: (x / w * 0.5 + 0.5) * cw, y: (-y / w * 0.5 + 0.5) * ch, w }
  }

  private frame = () => {
    this.raf = requestAnimationFrame(this.frame)
    const gl = this.gl, prog = this.prog
    if (!gl || !prog) return
    const t = (performance.now() - this.t0) / 1000
    const cam = this.cam, k = 0.06
    cam.az += (cam.azT + this.mouseAz - cam.az) * k
    cam.el += (cam.elT - cam.el) * k
    cam.r += (cam.rT - cam.r) * k
    cam.cx += (cam.cxT - cam.cx) * k; cam.cy += (cam.cyT - cam.cy) * k; cam.cz += (cam.czT - cam.cz) * k
    if (this.focus < 0) cam.azT += 0.0016
    for (let i = 0; i < 6; i++) this.pulses[i] *= 0.94

    const aspect = this.canvas.clientWidth / Math.max(this.canvas.clientHeight, 1)
    const proj = perspective(Math.PI / 4.2, aspect, 0.1, 100)
    const eye = [
      cam.cx + Math.cos(cam.az) * Math.cos(cam.el) * cam.r,
      cam.cy + Math.sin(cam.el) * cam.r,
      cam.cz + Math.sin(cam.az) * Math.cos(cam.el) * cam.r,
    ]
    this.vp = mul(proj, lookAt(eye, [cam.cx, cam.cy, cam.cz], [0, 1, 0]))

    gl.clearColor(0.03, 0.03, 0.035, 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.useProgram(prog)
    gl.uniformMatrix4fv(gl.getUniformLocation(prog, 'uVP'), false, new Float32Array(this.vp))
    gl.uniform1f(gl.getUniformLocation(prog, 'uTime'), t)
    gl.uniform1f(gl.getUniformLocation(prog, 'uFocus'), this.focus)
    gl.uniform1f(gl.getUniformLocation(prog, 'uFocusMix'), this.focus < 0 ? 0.0 : 0.8)
    gl.uniform1f(gl.getUniformLocation(prog, 'uDpr'), Math.min(window.devicePixelRatio || 1, 2))
    gl.uniform1fv(gl.getUniformLocation(prog, 'uPulse[0]'), new Float32Array(this.pulses))
    if (this.n > 0) {
      // pass 1: soft atmosphere (same buffers, big faint sprites = cheap bloom)
      gl.uniform1f(gl.getUniformLocation(prog, 'uBloom'), 1)
      gl.drawArrays(gl.POINTS, 0, this.n)
      // pass 2: the businesses themselves, crisp
      gl.uniform1f(gl.getUniformLocation(prog, 'uBloom'), 0)
      gl.drawArrays(gl.POINTS, 0, this.n)
    }
    this.onFrame?.()
  }
}
