import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { companiesApi } from '../api/companies'
import { apiErrorMessage } from '../api/errors'
import type { Company } from '../api/types'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Input } from '../components/ui/Input'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({ domain: '', name: '', industry: '' })

  const load = () => {
    setLoading(true)
    companiesApi
      .list(50, 0)
      .then((r) => setCompanies(r.items))
      .catch((e) => setError(apiErrorMessage(e)))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleCreate = async () => {
    if (!form.domain || !form.name) {
      return
    }
    try {
      await companiesApi.create({
        domain: form.domain,
        name: form.name,
        industry: form.industry || undefined,
      })
      setForm({ domain: '', name: '', industry: '' })
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  const handleResearch = async (domain: string) => {
    try {
      await companiesApi.research(domain)
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Companies</h1>

      {error && <ErrorBox message={error} />}

      <Card>
        <CardTitle>Add Company</CardTitle>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <Input
            placeholder="domain.com"
            value={form.domain}
            onChange={(e) => setForm({ ...form, domain: e.target.value })}
          />
          <Input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            placeholder="Industry"
            value={form.industry}
            onChange={(e) => setForm({ ...form, industry: e.target.value })}
          />
          <Button onClick={handleCreate}>Create</Button>
        </div>
      </Card>

      <Card>
        <CardTitle>List {loading && '...'}</CardTitle>
        <div className="divide-y divide-slate-800">
          {companies.map((c) => (
            <div key={c.id} className="py-3 flex items-center justify-between">
              <div>
                <Link to={`/companies/${c.domain}`} className="text-blue-400 hover:underline font-medium">
                  {c.name}
                </Link>
                <div className="text-slate-500 text-sm">
                  {c.domain} {c.industry && `· ${c.industry}`}
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => handleResearch(c.domain)}>
                  Research
                </Button>
              </div>
            </div>
          ))}
          {!companies.length && !loading && <div className="text-slate-500 py-4">No companies yet</div>}
        </div>
      </Card>
    </div>
  )
}
