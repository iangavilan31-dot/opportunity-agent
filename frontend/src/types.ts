export type LeadStatus =
  | 'new'
  | 'scored'
  | 'researched'
  | 'email_generated'
  | 'queued'
  | 'approved'
  | 'sent'
  | 'replied'
  | 'meeting'
  | 'rejected'

export interface Lead {
  id: number
  source: string
  job_id: string
  job_url: string | null
  company_name: string
  company_domain: string | null
  company_size: string | null
  company_industry: string | null
  company_research: Record<string, unknown> | null
  job_title: string
  job_description: string | null
  job_location: string | null
  job_posted_at: string | null
  automation_score: number
  pain_category: string | null
  pain_points: string[]
  inferred_workflows: string[]
  score_reasoning: string | null
  niche: string | null
  niche_label: string | null
  offer: {
    name?: string
    deliverables?: string[]
    setup?: number
    monthly?: number
    pitch?: string
  }
  contact_name: string | null
  contact_title: string | null
  contact_email: string | null
  contact_source: string | null
  contact_verified: string | null
  verification_score: number
  contact_confidence: number
  sendability: 'ready' | 'review' | 'risky' | 'blocked' | null
  subject_line: string | null
  email_body: string | null
  email_long: string | null
  mini_audit: string | null
  follow_up_1: string | null
  follow_up_2: string | null
  breakup_email: string | null
  objection_responses: Record<string, string>
  gmail_compose_url: string
  quality: {
    level: 'ready' | 'warn' | 'blocked'
    warnings: string[]
    blocking: string[]
  }
  status: LeadStatus
  sent_at: string | null
  opened_at: string | null
  replied_at: string | null
  meeting_booked_at: string | null
  notes: string | null
  created_at: string | null
}

export interface Stats {
  total_leads: number
  queued: number
  approved: number
  sent: number
  replied: number
  meetings: number
  rejected: number
  reply_rate: number
  meeting_rate: number
  followups_due: number
  sender_configured: boolean
  niches: Array<{ niche: string; label: string; count: number; avg_score: number }>
  last_run: {
    id: number
    status: string
    scraped: number
    queued: number
    started_at: string | null
  } | null
}

export interface PipelineStatus {
  status: 'idle' | 'running'
  run_id: number | null
  log: string[]
  progress: {
    scraped: number
    scored: number
    passed: number
    researched: number
    emailed: number
  }
}

export interface PipelineRun {
  id: number
  status: string
  scraped: number
  scored: number
  passed: number
  researched: number
  emailed: number
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface LeadListResponse {
  total: number
  page: number
  pages: number
  leads: Lead[]
}

export interface FollowupItem {
  id: number
  company_name: string
  contact_name: string | null
  contact_email: string | null
  niche_label: string | null
  stage: number
  stage_label: string
  days_waiting: number
  days_until_due: number
  subject_line: string
  body: string
  gmail_compose_url: string
  has_email: boolean
}
