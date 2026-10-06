import api from './client'
import type { EmailCandidate, EmailFindResponse } from './types'

export const emailFinderApi = {
  findForPerson: (personId: string, domain?: string, useHunter = true, useSmtp = false) =>
    api
      .post<EmailFindResponse>('/email/find', {
        person_id: personId,
        domain,
        use_hunter: useHunter,
        use_smtp: useSmtp,
      })
      .then((r) => r.data),

  getCandidates: (personId: string) =>
    api.get<EmailCandidate[]>(`/email/candidates/${personId}`).then((r) => r.data),

  setPrimary: (candidateId: string) =>
    api.post<EmailCandidate>(`/email/candidates/${candidateId}/set-primary`).then((r) => r.data),

  verify: (candidateId: string) =>
    api.post<EmailCandidate>(`/email/candidates/${candidateId}/verify`).then((r) => r.data),

  deleteCandidate: (candidateId: string) => api.delete(`/email/candidates/${candidateId}`),
}
