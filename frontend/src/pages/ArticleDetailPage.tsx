import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getArticle,
  optimizeArticle,
  publishArticle,
  scheduleArticle,
} from '../api/articles'
import type { SEOArticle } from '../api/types'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

export default function ArticleDetailPage() {
  const { id = '' } = useParams()
  const [article, setArticle] = useState<SEOArticle | null>(null)
  const [scheduledAt, setScheduledAt] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getArticle(id).then(setArticle).catch(() => setError('Article not found.'))
  }, [id])

  async function run(action: () => Promise<SEOArticle>) {
    setError('')
    try {
      setArticle(await action())
    } catch {
      setError('The requested article action failed.')
    }
  }

  if (!article) return <p>{error || 'Loading…'}</p>

  return (
    <article className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">{article.title}</h2>
          <p className="text-slate-400">{article.status} · /{article.slug}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => run(() => optimizeArticle(article.id))}>Optimize</Button>
          <Button onClick={() => run(() => publishArticle(article.id))}>Publish</Button>
        </div>
      </div>
      <div className="flex max-w-xl gap-2">
        <Input
          aria-label="Schedule date"
          type="datetime-local"
          value={scheduledAt}
          onChange={(event) => setScheduledAt(event.target.value)}
        />
        <Button
          variant="secondary"
          disabled={!scheduledAt}
          onClick={() => run(() => scheduleArticle(article.id, scheduledAt))}
        >
          Schedule
        </Button>
      </div>
      {error && <p role="alert" className="text-red-400">{error}</p>}
      <section className="rounded border border-slate-700 p-4">
        <h3 className="mb-2 font-semibold">SEO metadata</h3>
        <p><strong>Title:</strong> {article.meta_title || 'Not optimized'}</p>
        <p><strong>Description:</strong> {article.meta_description || 'Not optimized'}</p>
        <p><strong>Keywords:</strong> {article.keywords.join(', ') || 'None'}</p>
        <ul className="mt-2 list-disc pl-5">
          {article.internal_links.map((link) => (
            <li key={link.url}>{link.anchor}: {link.url}</li>
          ))}
        </ul>
      </section>
      <pre className="whitespace-pre-wrap rounded bg-slate-950 p-5 font-sans text-slate-200">
        {article.body_markdown}
      </pre>
    </article>
  )
}
