import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { generateArticle, listArticles } from '../api/articles'
import type { SEOArticle } from '../api/types'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

export function ArticlesList({ articles }: { articles: SEOArticle[] }) {
  if (articles.length === 0) {
    return <p className="text-slate-400">No articles yet.</p>
  }
  return (
    <div className="space-y-3">
      {articles.map((article) => (
        <Link
          key={article.id}
          to={`/articles/${article.id}`}
          className="block rounded border border-slate-700 p-4 hover:border-blue-500"
        >
          <div className="flex justify-between gap-4">
            <span className="font-semibold">{article.title}</span>
            <span className="text-sm text-slate-400">{article.status}</span>
          </div>
          <p className="mt-1 text-sm text-slate-500">/{article.slug}</p>
        </Link>
      ))}
    </div>
  )
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<SEOArticle[]>([])
  const [domain, setDomain] = useState('')
  const [keyword, setKeyword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    listArticles()
      .then((result) => setArticles(result.items))
      .catch(() => setError('Could not load articles.'))
      .finally(() => setLoading(false))
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      const article = await generateArticle({ company_domain: domain, keyword })
      navigate(`/articles/${article.id}`)
    } catch {
      setError('Article generation failed. Check that the company exists.')
    }
  }

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-bold">Articles</h2>
      <form onSubmit={submit} className="grid max-w-3xl grid-cols-1 gap-3 md:grid-cols-3">
        <Input value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="company.com" required />
        <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="Target keyword" required />
        <Button type="submit">Generate draft</Button>
      </form>
      {error && <p role="alert" className="text-red-400">{error}</p>}
      {loading ? <p>Loading…</p> : <ArticlesList articles={articles} />}
    </section>
  )
}
