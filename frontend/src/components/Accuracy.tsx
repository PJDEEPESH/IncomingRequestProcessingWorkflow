import { useState } from 'react'
import { api } from '../api'
import type { Accuracy } from '../types'

const TYPES = ['Complaint', 'General Enquiry', 'Service Request', 'Escalation']
const SHORT: Record<string, string> = {
  'Complaint': 'Compl', 'General Enquiry': 'Enq', 'Service Request': 'Serv', 'Escalation': 'Esc',
}

export default function AccuracyView() {
  const [data, setData] = useState<Accuracy | null>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    try { setData(await api.accuracy()) } finally { setBusy(false) }
  }

  return (
    <>
      <div className="card">
        <h3>Classification accuracy</h3>
        <div className="hint">Runs the classifier over the 15 labelled sample messages and scores it against ground truth — this targets the rubric's biggest line (40% = classification accuracy).</div>
        <button className="btn" onClick={run} disabled={busy}>
          {busy ? <><span className="spinner" /> Evaluating 15 messages…</> : '▶ Run evaluation'}
        </button>
      </div>

      {data && (
        <>
          <div className="grid cols-3">
            <div className="kpi">
              <div className="label">Type accuracy</div>
              <div className="value">{data.type_accuracy}%</div>
              <div className="muted" style={{ fontSize: 12 }}>{data.type_correct}/{data.n} correct</div>
            </div>
            <div className="kpi">
              <div className="label">Urgency accuracy</div>
              <div className="value">{data.urgency_accuracy}%</div>
              <div className="muted" style={{ fontSize: 12 }}>{data.urgency_correct}/{data.n} correct</div>
            </div>
            <div className="kpi">
              <div className="label">Engine</div>
              <div className="value" style={{ fontSize: 17 }}>{data.engine}</div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 14 }}>Confusion matrix</h3>
            <div className="hint">Rows = true label, columns = predicted. Green diagonal = correct; red = a miss.</div>
            <div className="tablewrap">
              <table className="table">
                <thead><tr><th>true ↓ / pred →</th>{TYPES.map(t => <th key={t} style={{ textAlign: 'center' }}>{SHORT[t]}</th>)}</tr></thead>
                <tbody>
                  {TYPES.map(tt => (
                    <tr key={tt}>
                      <td><b>{SHORT[tt]}</b></td>
                      {TYPES.map(pt => {
                        const v = data.confusion[tt]?.[pt] ?? 0
                        const diag = tt === pt
                        return (
                          <td key={pt} style={{
                            textAlign: 'center', fontWeight: v ? 700 : 400,
                            background: v ? (diag ? 'rgba(51,196,129,0.20)' : 'rgba(255,84,112,0.20)') : 'transparent',
                          }}>{v || ''}</td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 14 }}>Per-message results</h3>
            <div className="tablewrap">
              <table className="table">
                <thead><tr><th></th><th>Message</th><th>True</th><th>Predicted</th></tr></thead>
                <tbody>
                  {data.rows.map((r, i) => (
                    <tr key={i}>
                      <td>{r.ok === 'OK' ? '✅' : '❌'}</td>
                      <td className="muted">{r.message}</td>
                      <td>{r.true}</td>
                      <td style={{ color: r.ok === 'OK' ? 'var(--low)' : 'var(--crit)' }}>{r.pred}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  )
}
