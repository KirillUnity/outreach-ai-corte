import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiErrorMessage } from '../api/errors'
import { graphApi } from '../api/graph'
import type { GraphResponse } from '../api/types'
import { GraphView } from '../components/GraphView'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Input } from '../components/ui/Input'
import { Loading } from '../components/ui/Loading'

export default function GraphPage() {
  const [params] = useSearchParams()
  const [domain, setDomain] = useState(params.get('domain') || '')
  const [data, setData] = useState<GraphResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    if (!domain) {
      return
    }
    setLoading(true)
    setError(null)
    graphApi
      .companyNetwork(domain, 2)
      .then(setData)
      .catch((e) => {
        setData(null)
        setError(apiErrorMessage(e))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (params.get('domain')) {
      load()
    }
    // Initial load from ?domain= only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Graph Explorer</h1>

      <Card>
        <div className="flex gap-3">
          <Input
            placeholder="company domain (e.g. stripe.com)"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load()}
          />
          <Button onClick={load}>Load graph</Button>
        </div>
      </Card>

      {error && <ErrorBox message={error} />}
      {loading && <Loading text="Loading graph..." />}

      {data && data.nodes.length === 0 && !loading && (
        <Card>
          <p className="text-slate-400 text-sm">
            No nodes for this domain. Sync Postgres → Neo4j, then retry. An empty canvas is easy to
            confuse with a broken layout.
          </p>
        </Card>
      )}

      {data && data.nodes.length > 0 && (
        <Card>
          <CardTitle>
            Network: {data.nodes.length} nodes, {data.edges.length} edges
          </CardTitle>
          <GraphView data={data} />
        </Card>
      )}
    </div>
  )
}
