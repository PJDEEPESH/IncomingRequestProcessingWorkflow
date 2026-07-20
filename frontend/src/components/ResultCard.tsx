import { useEffect, useState } from 'react'
import type { Result } from '../types'

const U: Record<string, string> = { Critical: 'crit', High: 'high', Medium: 'med', Low: 'low' }
const EMO: Record<string, string> = { Angry: '😡', Frustrated: '😠', Neutral: '😐', Positive: '🙂' }
const pct = (n: number) => `${Math.round((n || 0) * 100)}%`

export default function ResultCard({ res, animate = true }: { res: Result; animate?: boolean }) {
  const [visible, setVisible] = useState(animate ? 0 : res.steps.length)
  const [thinking, setThinking] = useState(animate)

  useEffect(() => {
    if (!animate) { setVisible(res.steps.length); setThinking(false); return }
    setThinking(true); setVisible(0)
    const t = setTimeout(() => {
      setThinking(false)
      let i = 0
      const iv = setInterval(() => {
        i += 1
        setVisible(i)
        if (i >= res.steps.length) clearInterval(iv)
      }, 400)
    }, 750)
    return () => clearTimeout(t)
  }, [res, animate])

  return (
    <div>
      <div>
        <span className="badge type">{res.type}</span>
        <span className={`badge ${U[res.urgency] || 'low'}`}>{res.urgency} urgency</span>
        <span className="badge sent">{EMO[res.sentiment] || '😐'} {res.sentiment} {pct(res.sentiment_score)}</span>
      </div>

      {!res.engine?.startsWith('AI') && (
        <div className="warn" style={{ marginTop: 12 }}>
          ⚠ Degraded — the AI engine is unavailable, so this used the rule-based fallback. Quality is reduced.
        </div>
      )}

      <div className="metrics">
        <div className="metric"><div className="k">Confidence</div><div className="v">{pct(res.confidence)}</div></div>
        <div className="metric"><div className="k">Engine</div><div className="v">{res.engine}</div></div>
        <div className="metric"><div className="k">Routed to</div><div className="v">{res.routed_team}</div></div>
      </div>

      {thinking ? (
        <div className="loading"><span className="spinner" /> AI reasoning about the request…</div>
      ) : (
        <>
          <label>🧠 AI reasoning / triage plan</label>
          <div className="note">{res.triage_note || res.reasoning}</div>

          <label>Remediation steps executed</label>
          {res.steps.slice(0, visible).map((s, i) => (
            <div className="step" key={i}>
              <span className="tick">✔</span>
              <div><b>{s.name}</b> — <span>{s.detail}</span></div>
            </div>
          ))}

          {visible >= res.steps.length && (
            <>
              <div className="muted" style={{ fontSize: 11.5, marginTop: 4 }}>
                In this POC the reply is really written to an outbox file; routing, reminders and
                notifications are simulated and map to Salesforce / Twilio / email in production.
              </div>
              <label style={{ marginTop: 14 }}>Generated reply to customer</label>
              <div className="reply">{res.reply}</div>
              {res.outbox_file && (
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  📄 Reply written to <code>{res.outbox_file}</code> (this action is really executed)
                </div>
              )}
              <div className="pillrow">
                <div><div className="k">Status</div><div className="v">{res.status}</div></div>
                <div><div className="k">Follow-up</div><div className="v">{res.follow_up}</div></div>
                <div><div className="k">Flags</div><div className="v">{(res.flags || []).join(', ') || '-'}</div></div>
              </div>
              {res.approval === 'Pending' && (
                <div className="warn">⏳ This case needs human approval — see the Approvals tab.</div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
