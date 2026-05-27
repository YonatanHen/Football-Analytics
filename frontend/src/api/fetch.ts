import { apiFetch } from './client'

export interface FetchRequest { season?: string; mode?: string }
export interface FetchResponse { status: string; season: string; mode: string }

export async function triggerFetch(req: FetchRequest = {}): Promise<FetchResponse> {
  return apiFetch<FetchResponse>('/v1/fetch/', {
    method: 'POST',
    body: JSON.stringify({ mode: 'fantasy', ...req }),
  })
}
