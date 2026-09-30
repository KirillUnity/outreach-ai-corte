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
