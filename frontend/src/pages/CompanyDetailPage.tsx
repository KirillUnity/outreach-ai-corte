import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { companiesApi } from '../api/companies'
import { apiErrorMessage } from '../api/errors'
import { graphApi } from '../api/graph'
import type { Company, CompetitorsResponse, Person } from '../api/types'
import { InfluenceBadge } from '../components/InfluenceBadge'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Loading } from '../components/ui/Loading'

function personLabel(row: unknown): { name: string; title: string } {
  if (!row || typeof row !== 'object') {
    return { name: '—', title: '—' }
  }
  const rec = row as Record<string, unknown>
  const person = (rec.person && typeof rec.person === 'object' ? rec.person : rec) as Record<
    string,
    unknown
  >
  const first = String(person.first_name || person.name || '')
  const last = String(person.last_name || '')
  const name = `${first} ${last}`.trim() || '—'
  const title = String(person.title || rec.title || '—')
  return { name, title }
}

export default function CompanyDetailPage() {
  const { domain } = useParams<{ domain: string }>()
  const [company, setCompany] = useState<Company | null>(null)
  const [persons, setPersons] = useState<Person[]>([])
  const [decisionMakers, setDecisionMakers] = useState<unknown[]>([])
  const [competitors, setCompetitors] = useState<CompetitorsResponse | null>(null)
  const [recommendedTargets, setRecommendedTargets] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!domain) {
      return
    }
    setLoading(true)
    companiesApi
      .get(domain)
      .then(async (c) => {
        setCompany(c)
        const [p, dm, comp, rec] = await Promise.all([
          companiesApi.persons(c.id).catch(() => ({ items: [] as Person[] })),
          graphApi.decisionMakers(domain).catch(() => []),
          graphApi.competitors(domain).catch(() => null),
          graphApi.recommendedTargets(domain).catch(() => []),
        ])
        setPersons(p.items || [])
        setDecisionMakers(dm)
        setCompetitors(comp)
        setRecommendedTargets(Array.isArray(rec) ? rec : [])
      })
      .catch((e) => setError(apiErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [domain])

  if (loading) {
    return <Loading />
  }
  if (!company) {
    return <ErrorBox message={error || 'Not found'} />
  }

  const competitorRows = competitors?.competitors || []

  return (
    <div className="space-y-6">
      <Link to="/companies" className="text-blue-400 text-sm hover:underline">
        ← Back
      </Link>
      <h1 className="text-3xl font-bold text-white">{company.name}</h1>
      <div className="text-slate-400">
        {company.domain} {company.industry && `· ${company.industry}`}
      </div>

      {error && <ErrorBox message={error} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardTitle>Persons ({persons.length})</CardTitle>
          {persons.length ? (
            persons.map((p) => (
              <div key={p.id} className="py-2 border-b border-slate-800 last:border-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-white">
                    <Link to={`/persons/${p.id}`} className="text-blue-400 hover:underline">
                      {p.first_name} {p.last_name}
                    </Link>
                  </div>
                  <InfluenceBadge personId={p.id} />
                </div>
                <div className="text-slate-500 text-sm">{p.title || '—'}</div>
              </div>
            ))
          ) : (
            <div className="text-slate-500">No persons</div>
          )}
        </Card>

        <Card>
          <CardTitle>Decision Makers</CardTitle>
          {decisionMakers.length ? (
            decisionMakers.map((row, i) => {
              const { name, title } = personLabel(row)
              return (
                <div key={i} className="py-2 border-b border-slate-800 last:border-0">
                  <div className="text-white">{name}</div>
                  <div className="text-slate-500 text-sm">{title}</div>
                </div>
              )
            })
          ) : (
            <div className="text-slate-500">No decision makers found</div>
          )}
        </Card>

        <Card>
          <CardTitle>Competitors</CardTitle>
          {competitorRows.length ? (
            competitorRows.map((row, i) => {
              const comp = row.competitor || {}
              return (
                <div key={i} className="py-2 border-b border-slate-800 last:border-0">
                  <div className="text-white">{String(comp.name || '—')}</div>
                  <div className="text-slate-500 text-sm">{String(comp.domain || '')}</div>
                </div>
              )
            })
          ) : (
            <div className="text-slate-500">No competitors tracked</div>
          )}
        </Card>

        <Card>
          <CardTitle>Recommended targets</CardTitle>
          {recommendedTargets.length ? (
            recommendedTargets.map((row, i) => {
              const rec = row as Record<string, unknown>
              const person =
                rec.person && typeof rec.person === 'object'
                  ? (rec.person as Record<string, unknown>)
                  : rec
              const name =
                String(person.name || '').trim() ||
                `${person.first_name || ''} ${person.last_name || ''}`.trim() ||
                '—'
              return (
                <div
                  key={i}
                  className="py-2 border-b border-slate-800 last:border-0 flex justify-between items-center"
                >
                  <div>
                    <div className="text-white">{name}</div>
                    <div className="text-slate-500 text-sm">{String(person.title || rec.title || '—')}</div>
                  </div>
                  <div className="text-xs text-slate-400">{String(rec.connections_count ?? 0)} connections</div>
                </div>
              )
            })
          ) : (
            <div className="text-slate-500">No recommendations</div>
          )}
        </Card>

        <Card>
          <CardTitle>Quick Actions</CardTitle>
          <div className="space-y-2">
            <Button variant="secondary" onClick={() => companiesApi.research(domain!)}>
              Re-research site
            </Button>
            <Link to={`/graph?domain=${domain}`} className="block">
              <Button variant="secondary" className="w-full">
                View graph
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  )
}
