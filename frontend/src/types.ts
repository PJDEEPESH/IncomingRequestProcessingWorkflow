export interface Step {
  name: string
  detail: string
  done: boolean
}

export interface Result {
  id?: number
  message: string
  source: string
  sender?: string
  subject?: string
  type: string
  urgency: string
  sentiment: string
  sentiment_score: number
  confidence: number
  engine: string
  reasoning: string
  triage_note: string
  department?: string
  steps: Step[]
  reply: string
  routed_team: string
  follow_up: string
  flags: string[]
  status: string
  approval: string
  outbox_file?: string
}

export interface Accuracy {
  n: number
  engine: string
  type_accuracy: number
  urgency_accuracy: number
  type_correct: number
  urgency_correct: number
  confusion: Record<string, Record<string, number>>
  rows: { message: string; true: string; pred: string; ok: string }[]
}

export interface InboxItem {
  source: string
  sender: string
  subject: string
  message: string
}

export interface Kpis {
  total: number
  automation_rate?: number
  avg_confidence?: number
  pending?: number
  critical?: number
}

export interface Stats {
  total: number
  by_type: Record<string, number>
  by_urgency: Record<string, number>
  by_status: Record<string, number>
  by_sentiment: Record<string, number>
}

export interface Classification {
  type: string
  urgency: string
  sentiment: string
  sentiment_score: number
  confidence: number
  reasoning: string
  engine: string
}

export interface CompareOut {
  ai: Classification | null
  rules: Classification
}

export type CaseRow = Record<string, string | number>
