import type { Accuracy, CaseRow, CompareOut, InboxItem, Kpis, Result, Stats } from './types'

const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export const api = {
  health: () => get<{ ok: boolean; ai_configured: boolean; threshold: number }>('/api/health'),
  inbox: () => get<InboxItem[]>('/api/inbox'),
  process: (body: { message: string; source?: string; sender?: string; subject?: string }) =>
    post<Result>('/api/process', body),
  processInbox: () => post<Record<string, string>[]>('/api/process-inbox'),
  accuracy: () => get<Accuracy>('/api/accuracy'),
  cases: () => get<CaseRow[]>('/api/cases'),
  pending: () => get<CaseRow[]>('/api/pending'),
  approve: (id: number, decision: string) => post<{ ok: boolean }>('/api/approve', { id, decision }),
  kpis: () => get<Kpis>('/api/kpis'),
  stats: () => get<Stats>('/api/stats'),
  priorityQueue: () => get<CaseRow[]>('/api/priority-queue'),
  compare: (message: string) => post<CompareOut>('/api/compare', { message }),
  clear: () => post<{ ok: boolean }>('/api/clear'),
}
