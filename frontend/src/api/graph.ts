import api from './client'
import type { CompetitorsResponse, GraphResponse, GraphStats, InfluenceScore, WarmIntroSearchResponse } from './types'

export const graphApi = {
  companyNetwork: (domain: string, depth = 2) =>
    api
      .get<GraphResponse>(`/graph/company/${domain}/network`, { params: { depth } })
      .then((r) => r.data),

  personNetwork: (personId: string, depth = 2) =>
    api
      .get<GraphResponse>(`/graph/person/${personId}/network`, { params: { depth } })
      .then((r) => r.data),

  path: (fromId: string, toId: string, maxDepth = 6) =>
    api
      .get(`/graph/path`, {
        params: { from_person_id: fromId, to_person_id: toId, max_depth: maxDepth },
      })
      .then((r) => r.data),

  influence: (personId: string) =>
    api.get<InfluenceScore>(`/graph/person/${personId}/influence`).then((r) => r.data),

  stats: () => api.get<GraphStats>('/graph/analytics/stats').then((r) => r.data),

  decisionMakers: (domain: string, limit = 10) =>
    api
      .get<unknown[]>(`/graph/company/${domain}/decision-makers`, { params: { limit } })
      .then((r) => r.data),

  competitors: (domain: string) =>
    api.get<CompetitorsResponse>(`/graph/company/${domain}/competitors`).then((r) => r.data),

  recommendedTargets: (domain: string, limit = 10) =>
    api
      .get<unknown[]>(`/graph/company/${domain}/recommended-targets`, { params: { limit } })
      .then((r) => r.data),

  warmIntroSearch: (senderId: string, targetDomain: string, maxDepth = 4) =>
    api
      .get<WarmIntroSearchResponse>('/graph/warm-intro/search', {
        params: {
          sender_person_id: senderId,
          target_company_domain: targetDomain,
          max_depth: maxDepth,
        },
      })
      .then((r) => r.data),
}
