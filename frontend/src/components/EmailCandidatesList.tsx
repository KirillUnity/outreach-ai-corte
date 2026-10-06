import type { EmailCandidate } from '../api/types'

const sourceBadge: Record<string, string> = {
  linkedin: 'bg-blue-900/50 text-blue-300',
  hunter: 'bg-purple-900/50 text-purple-300',
  pattern: 'bg-slate-700 text-slate-300',
  manual: 'bg-green-900/50 text-green-300',
  guess: 'bg-slate-700 text-slate-400',
  apollo: 'bg-indigo-900/50 text-indigo-300',
}

const statusBadge: Record<string, string> = {
  verified: 'text-green-400',
  invalid: 'text-red-400',
  catchall: 'text-yellow-400',
  unknown: 'text-slate-400',
  pending: 'text-slate-500',
}

interface Props {
  candidates: EmailCandidate[]
  onSetPrimary?: (id: string) => void
  onVerify?: (id: string) => void
}

export function EmailCandidatesList({ candidates, onSetPrimary, onVerify }: Props) {
  if (!candidates.length) {
    return <div className="text-slate-500 text-sm">No email candidates</div>
  }

  return (
    <div className="space-y-2">
      {candidates.map((c) => (
        <div
          key={c.id}
          className={`flex items-center justify-between p-2 rounded border ${
            c.is_primary ? 'border-blue-600 bg-blue-900/10' : 'border-slate-800'
          }`}
        >
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-white text-sm">{c.email}</span>
              {c.is_primary && <span className="text-xs text-blue-400">PRIMARY</span>}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`px-1.5 py-0.5 rounded text-xs ${sourceBadge[c.source] || ''}`}>
                {c.source}
              </span>
              <span className={`text-xs ${statusBadge[c.status] || ''}`}>{c.status}</span>
              <span className="text-xs text-slate-500">conf: {(c.confidence * 100).toFixed(0)}%</span>
              {c.pattern_used && <span className="text-xs text-slate-600">({c.pattern_used})</span>}
            </div>
          </div>
          <div className="flex gap-2">
            {!c.is_primary && onSetPrimary && (
              <button
                className="text-xs text-blue-400 hover:underline"
                onClick={() => onSetPrimary(c.id)}
              >
                Set primary
              </button>
            )}
            {c.status === 'pending' && onVerify && (
              <button
                className="text-xs text-slate-400 hover:underline"
                onClick={() => onVerify(c.id)}
              >
                Verify
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
