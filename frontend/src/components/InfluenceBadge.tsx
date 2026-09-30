import { useEffect, useState } from 'react'
import { graphApi } from '../api/graph'
import type { InfluenceScore } from '../api/types'

interface Props {
  personId: string
  showDetails?: boolean
}

export function InfluenceBadge({ personId, showDetails = false }: Props) {
  const [data, setData] = useState<InfluenceScore | null>(null)

  useEffect(() => {
    if (!personId) {
      return
    }
    graphApi
      .influence(personId)
      .then(setData)
      .catch(() => setData(null))
  }, [personId])

  if (!data) {
    return null
  }

  const score = data.influence_score || 0
  const level = score > 50 ? 'high' : score > 20 ? 'medium' : 'low'
  const colors = {
    high: 'bg-green-900/40 text-green-300 border-green-700',
    medium: 'bg-yellow-900/40 text-yellow-300 border-yellow-700',
    low: 'bg-slate-800 text-slate-400 border-slate-700',
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs ${colors[level]}`}>
      <span className="font-semibold">{score.toFixed(0)}</span>
      <span>influence</span>
      {showDetails && (
        <span className="text-slate-500 ml-1">
          · {data.direct_connections} direct, {data.second_degree_connections} 2nd
        </span>
      )}
    </span>
  )
}
