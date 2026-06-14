import { apiFetch } from './client'

export interface FetchRequest { season?: string; mode?: string; competitions?: string[] }
export interface FetchResponse { job_id: string }
export interface FetchTask {
  label: string
  status: 'pending' | 'running' | 'done' | 'failed'
}

export interface FetchJobStatus {
  job_id: string
  status: 'running' | 'done' | 'partial' | 'error'
  total: number
  completed: number
  current: string
  players_upserted: number
  competitions_failed: number
  tasks: FetchTask[]
}

export async function triggerFetch(req: FetchRequest = {}): Promise<FetchResponse> {
  return apiFetch<FetchResponse>('/v1/fetch/', {
    method: 'POST',
    body: JSON.stringify({ mode: 'fantasy', ...req }),
  })
}

export async function getFetchStatus(jobId: string): Promise<FetchJobStatus> {
  return apiFetch<FetchJobStatus>(`/v1/fetch/status/${jobId}`)
}

export async function getCompetitions(): Promise<string[]> {
  return apiFetch<string[]>('/v1/competitions')
}

export interface CooldownStatus {
  allowed: boolean
  cooldown_hours: number
  last_fetched_at: string | null
  next_allowed_at: string | null
  seconds_remaining: number
  last_competition: string | null
}

export async function getCooldown(): Promise<CooldownStatus> {
  return apiFetch<CooldownStatus>('/v1/fetch/cooldown')
}
