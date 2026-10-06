import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiErrorMessage } from '../api/errors'
import { emailFinderApi } from '../api/emailFinder'
import { personsApi } from '../api/persons'
import type { EmailCandidate, Person } from '../api/types'
import { EmailCandidatesList } from '../components/EmailCandidatesList'
import { InfluenceBadge } from '../components/InfluenceBadge'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Loading } from '../components/ui/Loading'

export default function PersonDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [person, setPerson] = useState<Person | null>(null)
  const [candidates, setCandidates] = useState<EmailCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    if (!id) {
      return
    }
    setLoading(true)
    Promise.all([personsApi.get(id), emailFinderApi.getCandidates(id).catch(() => [])])
      .then(([p, c]) => {
        setPerson(p)
        setCandidates(c)
      })
      .catch((e) => setError(apiErrorMessage(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [id])

  const handleFind = async () => {
    if (!id) {
      return
    }
    setSearching(true)
    try {
      const result = await emailFinderApi.findForPerson(id)
      setCandidates(result.candidates)
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    } finally {
      setSearching(false)
    }
  }

  const handleSetPrimary = async (candidateId: string) => {
    try {
      await emailFinderApi.setPrimary(candidateId)
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  const handleVerify = async (candidateId: string) => {
    try {
      await emailFinderApi.verify(candidateId)
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  if (loading) {
    return <Loading />
  }
  if (!person) {
    return <ErrorBox message={error || 'Not found'} />
  }

  return (
    <div className="space-y-6">
      <Link to="/persons" className="text-blue-400 text-sm hover:underline">
        ← Back
      </Link>

      <div>
        <h1 className="text-3xl font-bold text-white">
          {person.first_name} {person.last_name}
        </h1>
        <div className="text-slate-400 flex items-center gap-3 mt-1">
          {person.title && <span>{person.title}</span>}
          <InfluenceBadge personId={person.id} showDetails />
        </div>
      </div>

      {error && <ErrorBox message={error} />}

      <Card>
        <div className="flex justify-between items-center mb-4">
          <CardTitle>Email candidates ({candidates.length})</CardTitle>
          <Button onClick={handleFind} disabled={searching}>
            {searching ? 'Searching...' : 'Find emails'}
          </Button>
        </div>
        <EmailCandidatesList
          candidates={candidates}
          onSetPrimary={handleSetPrimary}
          onVerify={handleVerify}
        />
      </Card>
    </div>
  )
}
