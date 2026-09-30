import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { companiesApi } from '../api/companies'
import { apiErrorMessage } from '../api/errors'
import { graphApi } from '../api/graph'
import type { Company, GraphStats, Paginated } from '../api/types'
import { Card, CardTitle } from '../components/ui/Card'

export default function Dashboard() {
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [companies, setCompanies] = useState<Paginated<Company> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([graphApi.stats().catch(() => null), companiesApi.list(5, 0)])
      .then(([s, c]) => {
        setStats(s)
        setCompanies(c)
      })
      .catch((e) => setError(apiErrorMessage(e)))
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Dashboard</h1>
      {error && <div className="text-red-400">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-slate-400 text-sm">Total Companies</div>
          <div className="text-3xl font-bold text-white mt-2">{stats?.nodes?.Company ?? '—'}</div>
        </Card>
        <Card>
          <div className="text-slate-400 text-sm">Total Persons</div>
          <div className="text-3xl font-bold text-white mt-2">{stats?.nodes?.Person ?? '—'}</div>
        </Card>
        <Card>
          <div className="text-slate-400 text-sm">Email Threads</div>
          <div className="text-3xl font-bold text-white mt-2">{stats?.nodes?.EmailThread ?? '—'}</div>
        </Card>
      </div>

      <Card>
        <CardTitle>Recent Companies</CardTitle>
        {companies?.items?.length ? (
          <ul className="space-y-2">
            {companies.items.map((c) => (
              <li key={c.id} className="flex justify-between border-b border-slate-800 pb-2">
                <Link to={`/companies/${c.domain}`} className="text-blue-400 hover:underline">
                  {c.name}
                </Link>
                <span className="text-slate-500 text-sm">{c.domain}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-slate-500">No companies yet</div>
        )}
      </Card>
    </div>
  )
}
