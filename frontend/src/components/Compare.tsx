import { useState } from 'react'
import { api } from '../api'
import type { Classification, CompareOut } from '../types'

const EMO: Record<string, string> = { Angry: '😡', Frustrated: '😠', Neutral: '😐', Positive: '🙂' }

function Col({ title, c }: { title: string; c: Classification | null }) {
  return (
    <div className="card">
      <h3 style={{ fontSize: 14 }}>{title}</h3>
      {!c ? (
        <div className="muted">No AI result (add an API key in the backend .env to enable it).</div>
      ) : (
        <>
          <div style={{ marginBottom: 10 }}>
            <span className="badge type">{c.type}</span>
            <span className="badge sent">{EMO[c.sentiment] || '😐'} {c.sentiment}</span>
          </div>
          <div className="muted" style={{ fontSize: 13 }}>
            Urgency: <b style={{ color: 'var(--text)' }}>{c.urgency}</b> · Confidence:{' '}
            <b style={{ color: 'var(--text)' }}>{Math.round(c.confidence * 100)}%</b>
          </div>
          <div className="note" style={{ marginTop: 10 }}>{c.reasoning}</div>
        </>
      )}
    </div>
  )
}

export default function Compare() {
  const [message, setMessage] = useState('Oh great, no internet AGAIN. Wonderful service as always.')
  const [out, setOut] = useState<CompareOut | null>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true); setOut(null)
    try { setOut(await api.compare(message)) } finally { setBusy(false) }
  }

  return (
    <>
      <div className="card">
        <h3>AI vs rule-based — why the AI matters</h3>
        <div className="hint">Run both engines on the same message. The AI catches nuance and sarcasm that keyword rules miss.</div>
        <textarea value={message} onChange={e => setMessage(e.target.value)} />
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={run} disabled={busy}>
            {busy ? <><span className="spinner" /> Comparing…</> : '🔬 Compare engines'}
          </button>
        </div>
      </div>

      {out && (
        <>
          <div className="grid cols-2">
            <Col title="🤖 AI (OpenAI)" c={out.ai} />
            <Col title="📏 Rule-based" c={out.rules} />
          </div>
          {out.ai && out.ai.type !== out.rules.type && (
            <div className="card" style={{ borderColor: 'var(--low)' }}>
              ⚡ The engines <b>disagree</b>: AI said <b>{out.ai.type}</b>, rules said <b>{out.rules.type}</b>.
              This is exactly where the AI adds value.
            </div>
          )}
        </>
      )}
    </>
  )
}
