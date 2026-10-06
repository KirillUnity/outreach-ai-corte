import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiErrorMessage } from '../api/errors'
import type { Mailbox, WarmupEvent, WarmupTimelinePoint } from '../api/types'
import { warmupApi } from '../api/warmup'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Loading } from '../components/ui/Loading'

export default function MailboxDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [mailbox, setMailbox] = useState<Mailbox | null>(null)
  const [events, setEvents] = useState<WarmupEvent[]>([])
  const [timeline, setTimeline] = useState<WarmupTimelinePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) {
      return
    }
    setLoading(true)
    Promise.all([warmupApi.getMailbox(id), warmupApi.getEvents(id, 50), warmupApi.getTimeline(id)])
      .then(([m, e, t]) => {
        setMailbox(m)
        setEvents(e)
        setTimeline(t)
      })
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <Loading />
  }
  if (!mailbox) {
    return <ErrorBox message={error || 'Not found'} />
  }

  const maxSent = Math.max(...timeline.map((t) => t.sent), 1)

  return (
    <div className="space-y-6">
      <Link to="/warmup" className="text-blue-400 text-sm hover:underline">
        ← Back
      </Link>
      <h1 className="text-3xl font-bold text-white">{mailbox.email}</h1>
      <div className="text-slate-400">
        {mailbox.status} · Day {mailbox.warmup_day}/30 · Reputation {mailbox.reputation_score.toFixed(0)}
      </div>

      <Card>
        <CardTitle>Warmup timeline</CardTitle>
        {timeline.length === 0 ? (
          <div className="text-slate-500 text-sm">No events yet. Run a tick from the list page.</div>
        ) : (
          <>
            <div className="flex items-end gap-1 h-40">
              {timeline.map((point) => (
                <div key={point.day} className="flex-1 flex flex-col items-center">
                  <div className="w-full flex flex-col justify-end" style={{ height: '100%' }}>
                    <div
                      className="bg-blue-500 w-full"
                      style={{ height: `${(point.sent / maxSent) * 60}%` }}
                      title={`Day ${point.day}: ${point.sent} sent`}
                    />
                    <div
                      className="bg-green-500 w-full"
                      style={{ height: `${(point.opened / maxSent) * 60}%` }}
                      title={`${point.opened} opened`}
                    />
                  </div>
                  <div className="text-xs text-slate-500 mt-1">{point.day}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-4 mt-3 text-xs text-slate-400">
              <span>
                <span className="inline-block w-3 h-3 bg-blue-500 mr-1" />
                Sent
              </span>
              <span>
                <span className="inline-block w-3 h-3 bg-green-500 mr-1" />
                Opened
              </span>
            </div>
          </>
        )}
      </Card>

      <Card>
        <CardTitle>Recent events ({events.length})</CardTitle>
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {events.map((e) => (
            <div key={e.id} className="flex justify-between text-sm py-1 border-b border-slate-800">
              <span className="text-slate-400">
                Day {e.warmup_day} · {e.event_type}
              </span>
              <span className="text-slate-500 text-xs">{e.peer_email}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
