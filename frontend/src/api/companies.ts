import api from './client'
import type { Company, Paginated, Person } from './types'

export const companiesApi = {
  list: (limit = 20, offset = 0) =>
    api
      .get<Paginated<Company>>('/companies/', { params: { limit, offset } })
      .then((r) => r.data),

  get: (domain: string) => api.get<Company>(`/companies/${domain}`).then((r) => r.data),

  create: (data: { domain: string; name: string; industry?: string }) =>
    api.post<Company>('/companies/', data).then((r) => r.data),

  research: (domain: string) => api.post(`/companies/${domain}/research`).then((r) => r.data),

  delete: (domain: string) => api.delete(`/companies/${domain}`),

  persons: (companyId: string) =>
    api
      .get<Paginated<Person>>('/persons/', { params: { company_id: companyId } })
      .then((r) => r.data),
}
