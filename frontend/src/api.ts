import type { Lead, Stats, LeadListResponse, PipelineStatus, PipelineRun } from './types'

const BASE = '/api'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  stats: () => req<Stats>('/stats'),

  leads: (params: {
    status?: string
    search?: string
    niche?: string
    page?: number
    limit?: number
  } = {}) => {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.search) qs.set('search', params.search)
    if (params.niche) qs.set('niche', params.niche)
    if (params.page) qs.set('page', String(params.page))
    if (params.limit) qs.set('limit', String(params.limit))
    return req<LeadListResponse>(`/leads?${qs}`)
  },

  getLead: (id: number) => req<Lead>(`/leads/${id}`),

  updateLead: (id: number, body: Partial<Lead>) =>
    req<Lead>(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),

  enrichLead: (id: number) =>
    req<{ ok: boolean; message?: string; contact_confidence?: number; sendability?: string }>(
      `/leads/${id}/enrich`, { method: 'POST' }),

  setContact: (id: number, body: { contact_name?: string; contact_title?: string; contact_email: string }) =>
    req<{ ok: boolean; sendability: string; contact_confidence: number; contact_verified: string }>(
      `/leads/${id}/set-contact`, { method: 'POST', body: JSON.stringify(body) }),

  replyPlaybook: (id: number) =>
    req<{
      lead_id: number; company: string; niche: string | null
      playbook: Record<string, { label: string; when: string; response: string }>
    }>(`/leads/${id}/replies`),

  approveLead: (id: number) =>
    req(`/leads/${id}/approve`, { method: 'POST' }),

  rejectLead: (id: number) =>
    req(`/leads/${id}/reject`, { method: 'POST' }),

  markSent: (id: number) =>
    req(`/leads/${id}/mark-sent`, { method: 'POST' }),

  markReplied: (id: number) =>
    req(`/leads/${id}/mark-replied`, { method: 'POST' }),

  markMeeting: (id: number) =>
    req(`/leads/${id}/mark-meeting`, { method: 'POST' }),

  deleteLead: (id: number) =>
    req(`/leads/${id}`, { method: 'DELETE' }),

  addManualLead: (body: {
    company_name: string
    company_domain?: string
    job_title: string
    job_description?: string
    job_location?: string
    contact_name?: string
    contact_title?: string
    contact_email?: string
    notes?: string
  }) => req<Lead>('/leads/manual', { method: 'POST', body: JSON.stringify(body) }),

  bulkApprove: (ids: number[]) =>
    req<{ ok: boolean; approved: number }>('/leads/bulk-approve', {
      method: 'POST', body: JSON.stringify({ ids }),
    }),

  bulkReject: (ids: number[]) =>
    req<{ ok: boolean; rejected: number }>('/leads/bulk-reject', {
      method: 'POST', body: JSON.stringify({ ids }),
    }),

  drafts: (status = 'approved') =>
    req<Array<{
      id: number
      company_name: string
      contact_name: string | null
      contact_email: string | null
      subject_line: string
      email_body: string
      automation_score: number
      status: string
      gmail_compose_url: string
      has_email: boolean
    }>>(`/drafts?status=${status}`),

  followups: () =>
    req<{
      due: FollowupItem[]
      upcoming: FollowupItem[]
      due_count: number
    }>('/followups'),

  getSettings: () =>
    req<{
      sender_name: string
      positioning: string
      calendar_link: string
      sender_email: string
      configured: boolean
      signature_preview: string
    }>('/settings'),

  saveSettings: (body: {
    sender_name?: string
    positioning?: string
    calendar_link?: string
    sender_email?: string
  }) => req<{ configured: boolean; signature_preview: string }>('/settings', {
    method: 'PUT', body: JSON.stringify(body),
  }),

  analytics: () =>
    req<{
      funnel: Record<string, number>
      pipeline: {
        total_potential: number
        weighted: number
        by_stage: Record<string, { count: number; potential: number }>
      }
      by_niche: Array<{ niche: string; label: string; count: number; avg_score: number; potential: number; reply_rate: number | null }>
      score_bands: Array<{ band: string; count: number }>
      sends_by_day: Record<string, number>
    }>('/analytics'),

  advanceFollowup: (id: number) =>
    req<{ ok: boolean; followup_stage: number }>(`/leads/${id}/advance-followup`, { method: 'POST' }),

  startPipeline: (queries?: string[]) =>
    req('/pipeline/run', { method: 'POST', body: JSON.stringify({ queries: queries ?? null }) }),

  pipelineStatus: () => req<PipelineStatus>('/pipeline/status'),

  pipelineHistory: () => req<PipelineRun[]>('/pipeline/history'),
}
