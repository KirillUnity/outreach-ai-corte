import api from './client'
import type { Mailbox, WarmupEvent, WarmupTickResult, WarmupTimelinePoint } from './types'

export const warmupApi = {
  listMailboxes: (limit = 50, offset = 0, status?: string) =>
    api
      .get<{ items: Mailbox[]; total: number }>('/warmup/mailboxes', {
        params: { limit, offset, status },
      })
      .then((r) => r.data),

  getMailbox: (id: string) => api.get<Mailbox>(`/warmup/mailboxes/${id}`).then((r) => r.data),

  createMailbox: (email: string, display_name?: string) =>
    api.post<Mailbox>('/warmup/mailboxes', { email, display_name }).then((r) => r.data),

  deleteMailbox: (id: string) => api.delete(`/warmup/mailboxes/${id}`),

  startWarmup: (id: string, reset = false) =>
    api
      .post<Mailbox>(`/warmup/mailboxes/${id}/start`, null, { params: { reset } })
      .then((r) => r.data),

  pauseMailbox: (id: string) => api.post<Mailbox>(`/warmup/mailboxes/${id}/pause`).then((r) => r.data),

  resumeMailbox: (id: string) =>
    api.post<Mailbox>(`/warmup/mailboxes/${id}/resume`).then((r) => r.data),

  runTick: (id: string) => api.post(`/warmup/mailboxes/${id}/tick`).then((r) => r.data),

  tickAll: () => api.post<WarmupTickResult>('/warmup/tick-all').then((r) => r.data),

  getStats: (id: string) => api.get(`/warmup/mailboxes/${id}/stats`).then((r) => r.data),

  getEvents: (id: string, limit = 50) =>
    api
      .get<WarmupEvent[]>(`/warmup/mailboxes/${id}/events`, { params: { limit } })
      .then((r) => r.data),

  getTimeline: (id: string) =>
    api.get<WarmupTimelinePoint[]>(`/warmup/mailboxes/${id}/timeline`).then((r) => r.data),
}
