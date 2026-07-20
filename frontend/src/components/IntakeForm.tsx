import { useState } from 'react'
import { api } from '../api'
import type { Result } from '../types'
import ResultCard from './ResultCard'

const EXAMPLES: Record<string, string> = {
  '— pick an example —': '',
  'Complaint (billing)': "I've been charged twice for my broadband this month and no one is helping me.",
  'Enquiry (hours)': 'What are your customer support opening hours on weekends?',
  'Service request (upgrade)': "I'd like to upgrade my current plan to the 1 Gbps fibre package please.",
  'Escalation (angry)': "This is the THIRD time my internet has gone down this week. I want a manager NOW or I'm cancelling.",
  'Sarcasm test': 'Oh great, no internet AGAIN. Wonderful service as always. Fix it.',
  'Low-confidence (vague)': 'hmm not sure honestly, just wanted to check something about my account i think',
  'Multi-intent (hard)': "I want to upgrade to 1 Gbps, but also my last bill is wrong AND this is the third outage this week.",
  'Typos / non-native': 'helo my internet is not workng since 2 day pls i need fix it fast thx',
}

export default function IntakeForm() {
  const [message, setMessage] = useState('')
  const [source, setSource] = useState('Web Form')
  const [sender, setSender] = useState('')
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState<Result | null>(null)

  async function submit() {
    if (!message.trim()) return
    setBusy(true); setRes(null)
    try {
      const r = await api.process({ message, source, sender, subject: 'Intake form submission' })
      setRes(r)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="card">
        <h3>Submit a request</h3>
        <div className="hint">The customer-facing intake form. Fill it in and watch the AI classify and remediate live.</div>

        <div className="row" style={{ marginBottom: 12 }}>
          <div>
            <label>Source channel</label>
            <select value={source} onChange={e => setSource(e.target.value)}>
              <option>Web Form</option><option>Email</option><option>Shared Inbox</option><option>Chat</option>
            </select>
          </div>
          <div>
            <label>Your email / name (optional)</label>
            <input value={sender} onChange={e => setSender(e.target.value)} placeholder="you@example.com" />
          </div>
        </div>

        <label>Load an example</label>
        <select onChange={e => setMessage(EXAMPLES[e.target.value] ?? '')} style={{ marginBottom: 12 }}>
          {Object.keys(EXAMPLES).map(k => <option key={k}>{k}</option>)}
        </select>

        <label>Your message</label>
        <textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="Describe your issue or request…" />

        <div style={{ marginTop: 14 }}>
          <button className="btn" onClick={submit} disabled={busy}>
            {busy ? <><span className="spinner" /> Processing…</> : '▶ Submit request'}
          </button>
        </div>
      </div>

      {res && <div className="card"><h3>Result</h3><ResultCard res={res} /></div>}
    </>
  )
}
