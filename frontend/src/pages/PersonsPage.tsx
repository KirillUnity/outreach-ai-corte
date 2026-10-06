import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiErrorMessage } from '../api/errors'
import { personsApi } from '../api/persons'
import type { Person } from '../api/types'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Input } from '../components/ui/Input'

export default function PersonsPage() {
  const [persons, setPersons] = useState<Person[]>([])
  const [form, setForm] = useState({ linkedin_url: '', company_domain: '' })
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    personsApi
      .list(50, 0)
      .then((r) => setPersons(r.items))
      .catch((e) => setError(apiErrorMessage(e)))

  useEffect(() => {
    load()
  }, [])

  const handleResearch = async () => {
    try {
      await personsApi.research(form.linkedin_url, form.company_domain || undefined)
      setForm({ linkedin_url: '', company_domain: '' })
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Persons</h1>
      {error && <ErrorBox message={error} />}

      <Card>
        <CardTitle>Research by LinkedIn URL</CardTitle>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Input
            placeholder="https://linkedin.com/in/..."
            value={form.linkedin_url}
            onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })}
          />
          <Input
            placeholder="company domain (optional)"
            value={form.company_domain}
            onChange={(e) => setForm({ ...form, company_domain: e.target.value })}
          />
          <Button onClick={handleResearch}>Research</Button>
        </div>
      </Card>

      <Card>
        <CardTitle>All Persons ({persons.length})</CardTitle>
        <div className="divide-y divide-slate-800">
          {persons.map((p) => (
            <div key={p.id} className="py-3">
              <div className="text-white font-medium">
                <Link to={`/persons/${p.id}`} className="text-blue-400 hover:underline">
                  {p.first_name} {p.last_name}
                </Link>
              </div>
              <div className="text-slate-500 text-sm">
                {p.title || '—'} {p.email && `· ${p.email}`}
              </div>
            </div>
          ))}
          {!persons.length && <div className="text-slate-500 py-4">No persons yet</div>}
        </div>
      </Card>
    </div>
  )
}
