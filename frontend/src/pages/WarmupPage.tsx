import { useEffect, useState } from 'react'
import { apiErrorMessage } from '../api/errors'
import type { Mailbox } from '../api/types'
import { warmupApi } from '../api/warmup'
import { MailboxCard } from '../components/MailboxCard'
import { Button } from '../components/ui/Button'
import { Card, CardTitle } from '../components/ui/Card'
import { ErrorBox } from '../components/ui/ErrorBox'
import { Input } from '../components/ui/Input'
import { Loading } from '../components/ui/Loading'

export default function WarmupPage() {
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([])
  const [newEmail, setNewEmail] = useState('')
  const [newName, setNewName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ticking, setTicking] = useState(false)
  const [tickMessage, setTickMessage] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    warmupApi
      .listMailboxes(50, 0)
      .then((r) => setMailboxes(r.items))
      .catch((e) => setError(apiErrorMessage(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async () => {
    if (!newEmail) {
      return
    }
    try {
      await warmupApi.createMailbox(newEmail, newName || undefined)
      setNewEmail('')
      setNewName('')
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  const handleStart = async (id: string) => {
    try {
      await warmupApi.startWarmup(id)
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  const handleTick = async () => {
    setTicking(true)
    setTickMessage(null)
    try {
      const result = await warmupApi.tickAll()
      setTickMessage(
        `Tick done: ${result.events_created} events, ${result.mailboxes_processed} mailboxes`,
      )
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    } finally {
      setTicking(false)
    }
  }

  const handleTickOne = async (id: string) => {
    try {
      await warmupApi.runTick(id)
      load()
    } catch (e: unknown) {
      setError(apiErrorMessage(e))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Mailbox Warmup</h1>
        <Button variant="secondary" onClick={handleTick} disabled={ticking}>
          {ticking ? 'Ticking...' : 'Run tick (all)'}
        </Button>
      </div>

      {error && <ErrorBox message={error} />}
      {tickMessage && <div className="text-sm text-green-400">{tickMessage}</div>}

      <Card>
        <CardTitle>Add mailbox</CardTitle>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Input
            placeholder="sender@yourdomain.com"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
          />
          <Input placeholder="Display name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <Button onClick={handleCreate}>Add</Button>
        </div>
      </Card>

      {loading && <Loading />}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mailboxes.map((m) => (
          <div key={m.id}>
            <MailboxCard mailbox={m} />
            <div className="flex gap-2 mt-2">
              {m.status === 'new' && (
                <Button
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation()
                    void handleStart(m.id)
                  }}
                >
                  Start warmup
                </Button>
              )}
              {m.status === 'warming' && (
                <Button
                  variant="secondary"
                  onClick={(e) => {
                    e.stopPropagation()
                    void handleTickOne(m.id)
                  }}
                >
                  Tick
                </Button>
              )}
            </div>
          </div>
        ))}
        {!mailboxes.length && !loading && (
          <Card>
            <div className="text-slate-500">No mailboxes yet</div>
          </Card>
        )}
      </div>
    </div>
  )
}
