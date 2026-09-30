import { useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import { graphApi } from '../api/graph'
import type { WarmIntroSearchResponse } from '../api/types'
import { WarmIntroCard } from '../components/WarmIntroCard'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Input } from '../components/ui/Input'
import { Loading } from '../components/ui/Loading'

export default function WarmIntroPage() {
  const [senderId, setSenderId] = useState('')
  const [targetDomain, setTargetDomain] = useState('')
  const [data, setData] = useState<WarmIntroSearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = async () => {
    if (!senderId || !targetDomain) {
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await graphApi.warmIntroSearch(senderId, targetDomain, 4)
      setData(result)
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Warm Intro Paths</h1>

      <Card>
        <CardTitle>Find warm intro route</CardTitle>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Input
            placeholder="Sender person UUID"
            value={senderId}
            onChange={(e) => setSenderId(e.target.value)}
          />
          <Input
            placeholder="Target company domain"
            value={targetDomain}
            onChange={(e) => setTargetDomain(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
          <Button onClick={search}>Search</Button>
        </div>
      </Card>

      {error && <ErrorBox message={error} />}
      {loading && <Loading text="Searching for warm intro paths..." />}

      {data && (
        <div className="space-y-3">
          <div className="text-slate-400 text-sm">
            Found {data.total} candidates for {data.target_company_domain}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.candidates.map((c) => (
              <WarmIntroCard key={c.target_person.id} candidate={c} />
            ))}
          </div>
          {!data.candidates.length && (
            <Card>
              <div className="text-slate-500">No warm intro paths found. Try increasing depth.</div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
