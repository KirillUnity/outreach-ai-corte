import api from './client'
import type { Paginated, Person } from './types'

export const personsApi = {
  list: (limit = 20, offset = 0, companyId?: string) =>
    api
      .get<Paginated<Person>>('/persons/', {
        params: { limit, offset, company_id: companyId },
      })
      .then((r) => r.data),

  get: (id: string) => api.get<Person>(`/persons/${id}`).then((r) => r.data),

  research: (linkedinUrl: string, companyDomain?: string) =>
    api
      .post('/persons/research', {
        linkedin_url: linkedinUrl,
        company_domain: companyDomain,
      })
      .then((r) => r.data),

  generateEmail: (
    personId: string,
    payload: {
      goal: string
      sender_name: string
      sender_title: string
      sender_company: string
    },
  ) =>
    api
      .post(`/persons/${personId}/generate-email`, { ...payload, person_id: personId })
      .then((r) => r.data),
}
