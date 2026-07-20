import { useEffect, useState } from 'react'
import { api } from '../api'
import type { InboxItem, Result } from '../types'
import ResultCard from './ResultCard'

const ICON: Record<string, string> = { Email: '📧', 'Web Form': '📝', 'Shared Inbox': '📥', Chat: '💬', Manual: '⌨️' }

export default function Inbox() {
  const [items, setItems] = useState<InboxItem[]>([])
  const [openIdx, setOpenIdx] = useState<number | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [busyIdx, setBusyIdx] = useState<number | null>(null)
  const [batchBusy, setBatchBusy] = useState(false)
  const [summary, setSummary] = useState<Record<string, string>[] | null>(null)

  useEffect(() => { api.inbox().then(setItems).catch(() => setItems([])) }, [])

  async function processOne(it: InboxItem, i: number) {
    setBusyIdx(i); setOpenIdx(i); setResult(null)
    try {
      const r = await api.process({ message: it.message, source: it.source, sender: it.sender, subject: it.subject })
      setResult(r)
    } finally {
      setBusyIdx(null)
    }
  }

  async function processAll() {
    setBatchBusy(true); setSummary(null)
    try { setSummary(await api.processInbox()) } finally { setBatchBusy(false) }
  }

  return (
    <div className="card">
      <h3>Simulated inbox</h3>
      <div className="hint">Requests arriving from multiple channels — exactly as the brief describes: email, web forms, a shared inbox, and live chat.</div>

      <button className="btn" onClick={processAll} disabled={batchBusy} style={{ marginBottom: 14 }}>
        {batchBusy ? <><span className="spinner" /> Processing all…</> : '⚡ Process entire inbox'}
      </button>

      {summary && (
        <div className="tablewrap" style={{ marginBottom: 16 }}>
          <table className="table">
            <thead><tr><th>Source</th><th>Sender</th><th>Type</th><th>Urgency</th><th>Sentiment</th><th>Routed to</th><th>Approval</th></tr></thead>
            <tbody>
              {summary.map((r, i) => (
                <tr key={i}><td>{r.source}</td><td>{r.sender}</td><td>{r.type}</td><td>{r.urgency}</td><td>{r.sentiment}</td><td>{r.routed_team}</td><td>{r.approval}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {items.map((it, i) => (
        <div className="inbox-item" key={i}>
          <div className="inbox-head">
            <div className="inbox-from">
              <span className="chip">{ICON[it.source] || '⌨️'} {it.source}</span>
              <b>{it.sender}</b>
              <span className="muted" style={{ fontSize: 12 }}>· {it.subject}</span>
            </div>
            <button className="btn sm" onClick={() => processOne(it, i)} disabled={busyIdx === i}>
              {busyIdx === i ? <><span className="spinner" /> …</> : '▶ Process'}
            </button>
          </div>
          <div className="inbox-msg">“{it.message}”</div>
          {openIdx === i && result && <ResultCard res={result} />}
        </div>
      ))}
    </div>
  )
}
