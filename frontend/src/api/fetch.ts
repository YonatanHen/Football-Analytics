import { apiFetch } from './client'

export interface FetchRequest { season?: string; mode?: string; competitions?: string[] }
export interface FetchResponse { job_id: string }
export interface FetchJobStatus {
  job_id: string
  status: 'running' | 'done' | 'partial' | 'error'
  total: number
  completed: number
  current: string
  players_upserted: number
  competitions_failed: number
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
