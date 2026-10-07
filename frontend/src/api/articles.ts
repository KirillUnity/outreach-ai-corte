import api from './client'
import type { Paginated, SEOArticle } from './types'

export async function listArticles(): Promise<Paginated<SEOArticle>> {
  const { data } = await api.get<Paginated<SEOArticle>>('/articles/')
  return data
}

export async function getArticle(id: string): Promise<SEOArticle> {
  const { data } = await api.get<SEOArticle>(`/articles/${id}`)
  return data
}

export async function generateArticle(payload: {
  company_domain: string
  keyword: string
  language?: string
  max_words?: number
}): Promise<SEOArticle> {
  const { data } = await api.post<SEOArticle>('/articles/generate', payload)
  return data
}

export async function scheduleArticle(id: string, scheduledAt: string): Promise<SEOArticle> {
  const { data } = await api.post<SEOArticle>(`/articles/${id}/schedule`, {
    scheduled_at: new Date(scheduledAt).toISOString(),
  })
  return data
}

export async function publishArticle(id: string): Promise<SEOArticle> {
  const { data } = await api.post<SEOArticle>(`/articles/${id}/publish`)
  return data
}

export async function optimizeArticle(id: string): Promise<SEOArticle> {
  const { data } = await api.post<SEOArticle>(`/articles/${id}/optimize?use_llm=false`)
  return data
}
