import { useNavigate } from 'react-router-dom'
import type { Mailbox } from '../api/types'

const statusColors: Record<string, string> = {
  new: 'bg-slate-700 text-slate-300',
  warming: 'bg-blue-900/50 text-blue-300 border-blue-700',
  warmed: 'bg-green-900/50 text-green-300 border-green-700',
  paused: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  banned: 'bg-red-900/50 text-red-300 border-red-700',
}

export function MailboxCard({ mailbox, onClick }: { mailbox: Mailbox; onClick?: () => void }) {
  const navigate = useNavigate()
  const repColor =
    mailbox.reputation_score > 70
      ? 'text-green-400'
      : mailbox.reputation_score > 40
        ? 'text-yellow-400'
        : 'text-red-400'

  return (
    <div
      className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-blue-600 cursor-pointer"
      onClick={() => (onClick ? onClick() : navigate(`/warmup/${mailbox.id}`))}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="text-white font-medium">{mailbox.email}</div>
        <span className={`px-2 py-0.5 rounded text-xs border ${statusColors[mailbox.status] || ''}`}>
          {mailbox.status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-slate-400 mb-2">
        <div>
          <div className="text-slate-500">Day</div>
          <div className="text-white text-sm">{mailbox.warmup_day}/30</div>
        </div>
        <div>
          <div className="text-slate-500">Reputation</div>
          <div className={`text-sm font-semibold ${repColor}`}>{mailbox.reputation_score.toFixed(0)}</div>
        </div>
        <div>
          <div className="text-slate-500">Daily</div>
          <div className="text-white text-sm">
            {mailbox.emails_sent_today}/{mailbox.daily_limit}
          </div>
        </div>
      </div>

      <div className="flex gap-3 text-xs">
        <span className="text-green-400">Open {(mailbox.open_rate * 100).toFixed(0)}%</span>
        <span className="text-blue-400">Reply {(mailbox.reply_rate * 100).toFixed(0)}%</span>
        {mailbox.bounce_rate > 0.02 && (
          <span className="text-red-400">Bounce {(mailbox.bounce_rate * 100).toFixed(1)}%</span>
        )}
      </div>

      <div className="mt-3 w-full bg-slate-800 rounded-full h-1.5">
        <div
          className="bg-blue-500 h-1.5 rounded-full transition-all"
          style={{ width: `${Math.min(100, (mailbox.warmup_day / 30) * 100)}%` }}
        />
      </div>
    </div>
  )
}
