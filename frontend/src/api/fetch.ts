import { apiFetch } from './client'

export interface FetchRequest { season?: string; mode?: string; competitions?: string[] }
export interface FetchResponse { status: string; season: string; players_upserted?: number }

export async function triggerFetch(req: FetchRequest = {}): Promise<FetchResponse> {
  return apiFetch<FetchResponse>('/v1/fetch/', {
    method: 'POST',
    body: JSON.stringify({ mode: 'fantasy', ...req }),
  })
}
