import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import type { CaseRow, Kpis, Stats } from '../types'

const toData = (o: Record<string, number> = {}) => Object.entries(o).map(([name, value]) => ({ name, value }))
const COLORS = ['#7c6bff', '#4f9dff', '#33c481', '#ff9f45', '#ff5470']

function Chart({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  return (
    <div className="card">
      <h3 style={{ fontSize: 14 }}>{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <XAxis dataKey="name" stroke="#8b93a7" fontSize={11} interval={0} />
          <YAxis stroke="#8b93a7" fontSize={11} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: '#141b2e', border: '1px solid rgba(255,255,255,0.16)', borderRadius: 10, color: '#e7ebf5' }}
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Dashboard() {
  const [kpis, setKpis] = useState<Kpis | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [pq, setPq] = useState<CaseRow[]>([])

  useEffect(() => {
    api.kpis().then(setKpis).catch(() => {})
    api.stats().then(setStats).catch(() => {})
    api.priorityQueue().then(setPq).catch(() => {})
  }, [])

  async function exportCsv() {
    const rows = await api.cases()
    if (!rows.length) return
    const headers = Object.keys(rows[0])
    const csv = [
      headers.join(','),
      ...rows.map(r => headers.map(h => JSON.stringify(r[h] ?? '')).join(',')),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'case_log.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!kpis || kpis.total === 0) {
    return <div className="card"><div className="muted center" style={{ padding: 24 }}>No data yet — process some requests (try the Inbox).</div></div>
  }

  const tiles: [string, string | number][] = [
    ['Total requests', kpis.total],
    ['Automation rate', `${kpis.automation_rate}%`],
    ['Avg confidence', `${kpis.avg_confidence}%`],
    ['Awaiting approval', kpis.pending ?? 0],
    ['Critical', kpis.critical ?? 0],
  ]

  return (
    <>
      <div className="grid cols-5">
        {tiles.map(([label, value]) => (
          <div className="kpi" key={label}><div className="label">{label}</div><div className="value">{value}</div></div>
        ))}
      </div>

      <div className="grid cols-3" style={{ marginTop: 18 }}>
        <Chart title="By type" data={toData(stats?.by_type)} />
        <Chart title="By urgency" data={toData(stats?.by_urgency)} />
        <Chart title="By sentiment" data={toData(stats?.by_sentiment)} />
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>🚦 Priority queue — open cases, most urgent first</h3>
          <button className="btn ghost sm" onClick={exportCsv}>⬇ Export case log (CSV)</button>
        </div>
        <div style={{ height: 12 }} />
        <div className="tablewrap">
          <table className="table">
            <thead>
              <tr><th>#</th><th>Urgency</th><th>Type</th><th>Sentiment</th><th>Source</th><th>Routed to</th><th>Status</th></tr>
            </thead>
            <tbody>
              {pq.map(r => (
                <tr key={r.id as number}>
                  <td>{r.id}</td><td>{r.urgency}</td><td>{r.type}</td><td>{r.sentiment}</td>
                  <td>{r.source}</td><td>{r.routed_team}</td><td>{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
