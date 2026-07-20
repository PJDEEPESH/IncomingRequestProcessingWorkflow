import { useEffect, useState } from 'react'
import { api } from './api'
import AccuracyView from './components/Accuracy'
import Approvals from './components/Approvals'
import Architecture from './components/Architecture'
import Compare from './components/Compare'
import Dashboard from './components/Dashboard'
import Inbox from './components/Inbox'
import IntakeForm from './components/IntakeForm'

type View = 'intake' | 'inbox' | 'approvals' | 'dashboard' | 'accuracy' | 'compare' | 'architecture'

const NAV: { id: View; label: string; ico: string; sub: string }[] = [
  { id: 'intake', label: 'Intake Form', ico: '📝', sub: 'Submit a request' },
  { id: 'inbox', label: 'Inbox', ico: '📥', sub: 'Multi-source requests' },
  { id: 'approvals', label: 'Approvals', ico: '✅', sub: 'Human-in-the-loop' },
  { id: 'dashboard', label: 'Dashboard', ico: '📊', sub: 'KPIs & charts' },
  { id: 'accuracy', label: 'Accuracy', ico: '🎯', sub: 'Classification score' },
  { id: 'compare', label: 'AI vs Rules', ico: '⚖️', sub: 'Prove the AI value' },
  { id: 'architecture', label: 'Architecture', ico: '🗺️', sub: 'LangGraph flow' },
]

export default function App() {
  const [view, setView] = useState<View>('intake')
  const [ai, setAi] = useState<boolean | null>(null)

  useEffect(() => { api.health().then(h => setAi(h.ai_configured)).catch(() => setAi(false)) }, [])

  const cur = NAV.find(n => n.id === view)!

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">B</div>
          <div>
            <div className="brand-name">BlueStream</div>
            <div className="brand-sub">Request Workflow · POC</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map(n => (
            <div key={n.id} className={`nav-item ${view === n.id ? 'active' : ''}`} onClick={() => setView(n.id)}>
              <span className="nav-ico">{n.ico}</span>{n.label}
            </div>
          ))}
        </nav>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <h1 className="page-title">{cur.label}</h1>
            <div className="page-sub">{cur.sub}</div>
          </div>
          <div className="ai-pill">
            <span className={`dot ${ai ? 'on' : 'off'}`} />
            {ai === null ? 'Checking…' : ai ? 'AI engine active' : 'Fallback engine'}
          </div>
        </div>

        {view === 'intake' && <IntakeForm />}
        {view === 'inbox' && <Inbox />}
        {view === 'approvals' && <Approvals />}
        {view === 'dashboard' && <Dashboard />}
        {view === 'accuracy' && <AccuracyView />}
        {view === 'compare' && <Compare />}
        {view === 'architecture' && <Architecture />}
      </main>
    </div>
  )
}
