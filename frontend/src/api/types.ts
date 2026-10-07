export interface Company {
  id: string
  domain: string
  name: string
  description?: string | null
  industry?: string | null
  size?: string | null
  created_at: string
}

export interface Person {
  id: string
  first_name: string
  last_name: string
  linkedin_url?: string | null
  email?: string | null
  title?: string | null
  company_id?: string | null
  created_at: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  limit?: number
  offset?: number
}

export interface GraphNode {
  id: string
  label: string
  name: string
  properties: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  properties: Record<string, unknown>
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphStats {
  nodes: Record<string, number>
  relationships: Record<string, number>
}

export interface InfluenceScore {
  id?: string | null
  direct_connections: number
  second_degree_connections: number
  influence_score: number
}

export interface CompetitorsResponse {
  competitors: Array<{
    competitor?: Record<string, unknown>
    top_people?: unknown[]
  }>
}

export interface WarmIntroCandidate {
  target_person: GraphNode
  target_company: GraphNode
  path: GraphNode[]
  distance: number
  mutual_connections: number
  influence_score: number
  has_prior_contact: boolean
}

export interface WarmIntroSearchResponse {
  sender_person_id: string | null
  target_company_domain: string
  candidates: WarmIntroCandidate[]
  total: number
}

export type MailboxStatus = 'new' | 'warming' | 'warmed' | 'paused' | 'banned'

export interface Mailbox {
  id: string
  email: string
  domain: string
  display_name?: string | null
  status: MailboxStatus
  warmup_day: number
  daily_limit: number
  emails_sent_today: number
  total_sent: number
  total_opened: number
  total_replied: number
  total_bounced: number
  total_spam_reports: number
  reputation_score: number
  open_rate: number
  reply_rate: number
  bounce_rate: number
  warmup_started_at?: string | null
  last_warmup_event_at?: string | null
  created_at: string
}

export interface WarmupEvent {
  id: string
  mailbox_id: string
  peer_email: string
  event_type: string
  warmup_day: number
  created_at: string
}

export interface WarmupTimelinePoint {
  day: number
  sent: number
  opened: number
  replied: number
}

export interface WarmupTickResult {
  mailboxes_processed: number
  events_created: number
  mailboxes_banned: number
  mailboxes_warmed: number
  duration_seconds: number
}

export type EmailCandidateSource = 'pattern' | 'hunter' | 'apollo' | 'manual' | 'linkedin' | 'guess'
export type EmailCandidateStatus = 'pending' | 'verified' | 'invalid' | 'catchall' | 'unknown'

export interface EmailCandidate {
  id: string
  person_id: string
  email: string
  source: EmailCandidateSource
  status: EmailCandidateStatus
  confidence: number
  pattern_used?: string
  is_primary: boolean
  verified_at?: string
  verification_details?: Record<string, unknown>
  created_at: string
}

export interface EmailFindResponse {
  person_id: string
  candidates: EmailCandidate[]
  primary_email?: string
  best_confidence: number
  sources_used: string[]
  duration_seconds: number
}

export type ArticleStatus = 'draft' | 'ready' | 'scheduled' | 'published' | 'failed'

export interface SEOArticle {
  id: string
  company_id?: string | null
  title: string
  slug: string
  body_markdown: string
  language: string
  status: ArticleStatus
  keywords: string[]
  keyword_primary?: string | null
  meta_title?: string | null
  meta_description?: string | null
  internal_links: Array<{ anchor: string; url: string }>
  rag_context_used: Array<Record<string, unknown>>
  tokens_input: number
  tokens_output: number
  estimated_cost_usd: string
  generation_prompt_version: string
  scheduled_at?: string | null
  published_at?: string | null
  publish_channel: 'mock' | 'webhook'
  publish_url?: string | null
  created_at: string
  updated_at: string
}
