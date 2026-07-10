import { useCallback, useEffect, useRef, useState } from 'react'
import type { Lead } from '../types'
import { api } from '../api'

// The Web Machine renders REAL businesses only. Mock/demo rows (source !== ///
// 'website_autopilot') never reach a pixel, and no projected money is ever
// shown as money — the only dollars rendered are deals actually closed.
export const REAL_SOURCE = 'website_autopilot'

// One canonical word per stage, used verbatim on every surface.
export const STAGES = [
  { key: 'queued', name: 'Queued' },
  { key: 'approved', name: 'Approved' },
  { key: 'sent', name: 'Reached' },
  { key: 'replied', name: 'Replied' },
  { key: 'meeting', name: 'Meeting' },
  { key: 'won', name: 'Won' },
] as const

/** Funnel stage index 0..5, or -1 if the lead is out of the funnel (rejected). */
export function stageOf(lead: Lead): number {
  switch (lead.status) {
    case 'rejected': return -1
    case 'approved': return 1
    case 'sent': return 2
    case 'replied': return 3
    case 'meeting': return 4
    // pre-queue pipeline states sit in the first cloud — they are real
    // discovered businesses that simply haven't been drafted yet
    case 'new': case 'scored': case 'researched': case 'email_generated':
    case 'queued': return 0
    default:
      return (lead.status as string) === 'won' || (lead.status as string) === 'closed' ? 5 : 0
  }
}

/** '2026-07-09 13:05:11.326829' → epoch ms. DB timestamps are UTC (backend
 * writes datetime.now(timezone.utc)) but are serialized without an offset —
 * parsing them as local silently shifts every event by the TZ offset. */
export function ts(s: string | null | undefined): number | null {
  if (!s) return null
  const iso = s.replace(' ', 'T')
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso)
  const t = new Date(hasTz ? iso : iso + 'Z').getTime()
  return Number.isFinite(t) ? t : null
}

export interface FunnelSummary {
  counts: number[]              // per stage 0..5
  cumulative: { sent: number; replied: number; meeting: number; won: number }
  discovered: number            // all real leads incl. rejected
  active: number                // non-rejected
  declined: number
  earned: number                // real closed deal value only
  recentlyActive: number        // activity in the last 24h
}

export function summarize(leads: Lead[]): FunnelSummary {
  const counts = [0, 0, 0, 0, 0, 0]
  let declined = 0
  let earned = 0
  let recentlyActive = 0
  const dayAgo = Date.now() - 24 * 3600 * 1000
  for (const l of leads) {
    const s = stageOf(l)
    if (s < 0) { declined++; continue }
    counts[s]++
    if (s === 5) earned += Number(l.offer?.setup) || 0
    const last = ts(l.sent_at) ?? ts(l.replied_at) ?? ts(l.created_at)
    if (last && last > dayAgo) recentlyActive++
  }
  const cumulative = {
    won: counts[5],
    meeting: counts[4] + counts[5],
    replied: counts[3] + counts[4] + counts[5],
    sent: counts[2] + counts[3] + counts[4] + counts[5],
  }
  return {
    counts, cumulative, declined, earned, recentlyActive,
    discovered: leads.length, active: leads.length - declined,
  }
}

export interface NicheRow {
  niche: string
  label: string
  count: number
  avgScore: number
  estValue: number
}

/** Everything analytics needs, computed from the same real leads every other
 * surface renders — one canonical count per business, no server-side drift. */
export function analyze(leads: Lead[]) {
  const active = leads.filter((l) => stageOf(l) >= 0)
  const niches = new Map<string, { label: string; count: number; score: number; est: number }>()
  const cities = new Set<string>()
  const bins = [0, 0, 0, 0, 0] // 90+, 80s, 70s, 60s, <60 — equal-width, honest
  const sendsByDay = new Map<string, number>()
  let estPotential = 0
  for (const l of active) {
    const key = l.niche || 'other'
    const cur = niches.get(key) || { label: l.niche_label || 'Other', count: 0, score: 0, est: 0 }
    const est = (Number(l.offer?.setup) || 0) + (Number(l.offer?.monthly) || 0) * 12
    cur.count++; cur.score += l.automation_score || 0; cur.est += est
    niches.set(key, cur)
    estPotential += est
    if (l.job_location) cities.add(l.job_location.trim().toLowerCase())
    const s = l.automation_score || 0
    // ascending, equal-width decades; the catch-all is labeled as an aggregate
    bins[s < 60 ? 0 : s < 70 ? 1 : s < 80 ? 2 : s < 90 ? 3 : 4]++
    const sent = ts(l.sent_at)
    if (sent) {
      const day = new Date(sent).toISOString().slice(0, 10)
      sendsByDay.set(day, (sendsByDay.get(day) || 0) + 1)
    }
  }
  const nicheRows: NicheRow[] = [...niches.entries()]
    .map(([niche, v]) => ({ niche, label: v.label, count: v.count, avgScore: Math.round(v.score / v.count), estValue: v.est }))
    .sort((a, b) => b.estValue - a.estValue)
  return {
    nicheRows,
    cityCount: cities.size,
    bins,
    binLabels: ['<60 · agg', '60s', '70s', '80s', '90+'],
    sendsByDay: [...sendsByDay.entries()].sort(([a], [b]) => a.localeCompare(b)),
    estPotential,
  }
}

export function useRealLeads(pollMs = 30000) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [live, setLive] = useState<boolean | null>(null)
  const timer = useRef<number>()

  const refresh = useCallback(async () => {
    try {
      const res = await api.leads({ limit: 500 })
      setLeads(res.leads.filter((l) => l.source === REAL_SOURCE))
      setLive(true)
    } catch {
      setLive(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    timer.current = window.setInterval(refresh, pollMs)
    return () => window.clearInterval(timer.current)
  }, [refresh, pollMs])

  return { leads, live, refresh }
}
