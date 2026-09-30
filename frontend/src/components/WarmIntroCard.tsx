import type { WarmIntroCandidate } from '../api/types'

interface Props {
  candidate: WarmIntroCandidate
  onSelect?: (candidate: WarmIntroCandidate) => void
}

export function WarmIntroCard({ candidate, onSelect }: Props) {
  const distanceColor =
    candidate.distance === 1
      ? 'text-green-400'
      : candidate.distance === 2
        ? 'text-blue-400'
        : candidate.distance === 3
          ? 'text-yellow-400'
          : 'text-slate-400'

  return (
    <div
      className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-blue-600 cursor-pointer transition"
      onClick={() => onSelect?.(candidate)}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="text-white font-medium">{candidate.target_person.name}</div>
          <div className="text-slate-500 text-sm">
            {String(candidate.target_person.properties.title || '—')}
          </div>
        </div>
        <div className={`text-sm font-semibold ${distanceColor}`}>
          {candidate.distance >= 0 ? `${candidate.distance} hops` : 'no path'}
        </div>
      </div>

      {candidate.distance > 0 && (
        <div className="mb-2">
          <div className="text-xs text-slate-500 mb-1">Intro path:</div>
          <div className="flex flex-wrap items-center gap-1 text-xs">
            {candidate.path.map((node, i) => (
              <span key={node.id} className="flex items-center gap-1">
                {i > 0 && <span className="text-slate-600">→</span>}
                <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">{node.name}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 text-xs text-slate-400">
        <span>🤝 {candidate.mutual_connections} mutual</span>
        <span>⚡ {candidate.influence_score.toFixed(0)} influence</span>
      </div>
    </div>
  )
}
