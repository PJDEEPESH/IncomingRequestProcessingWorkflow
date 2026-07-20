import { useEffect, useState } from 'react'
import { api } from '../api'
import type { CaseRow } from '../types'

const U: Record<string, string> = { Critical: 'crit', High: 'high', Medium: 'med', Low: 'low' }

export default function Approvals() {
  const [rows, setRows] = useState<CaseRow[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setRows(await api.pending())
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  async function decide(id: number, decision: string) {
    await api.approve(id, decision)
    load()
  }

  if (loading) return <div className="card"><div className="loading"><span className="spinner" /> Loading…</div></div>

  return (
    <div className="card">
      <h3>Human approval queue</h3>
      <div className="hint">Escalations and low-confidence cases are held here for a human decision — the human-in-the-loop step.</div>
      {rows.length === 0 ? (
        <div className="muted center" style={{ padding: 22 }}>✅ No cases waiting for approval.</div>
      ) : (
        rows.map(r => (
          <div className="inbox-item" key={r.id as number}>
            <div className="inbox-head">
              <div className="inbox-from">
                <span className="badge type">{r.type}</span>
                <span className={`badge ${U[r.urgency as string] || 'low'}`}>{r.urgency}</span>
                <span className="muted" style={{ fontSize: 12 }}>#{r.id} · {r.source} · {r.sender}</span>
              </div>
              <div className="row" style={{ flex: 'none', gap: 8 }}>
                <button className="btn ok sm" onClick={() => decide(r.id as number, 'Approved')}>✔ Approve</button>
                <button className="btn no sm" onClick={() => decide(r.id as number, 'Rejected')}>✕ Reject</button>
              </div>
            </div>
            <div className="inbox-msg">“{r.message}”</div>
            <div className="note">{r.triage_note}</div>
          </div>
        ))
      )}
    </div>
  )
}
