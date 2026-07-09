import { useCallback, useEffect, useRef, useState } from 'react'
import type { Lead } from '../types'
import { api } from '../api'

// The Web Machine renders REAL businesses only. Mock/demo rows (source !== ///
// 'website_autopilot') never reach a pixel, and no projected money is ever
// shown as money — the only dollars rendered are deals actually closed.
export const REAL_SOURCE = 'website_autopilot'

export const STAGES = [
  { key: 'queued', name: 'Queued' },
  { key: 'approved', name: 'Approved' },
  { key: 'sent', name: 'Sent' },
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

/** '2026-07-09 13:05:11.326829' → epoch ms (null-safe). */
export function ts(s: string | null | undefined): number | null {
  if (!s) return null
  const t = new Date(s.replace(' ', 'T')).getTime()
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
