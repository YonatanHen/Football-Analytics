import { apiFetch, API_URL } from './client'

export interface Meta {
  players_total: number
  last_updated: string | null
  seasons: string[]
  agent: { model: string; max_tool_calls: number }
}

export function getMeta(season?: string): Promise<Meta> {
  return apiFetch<Meta>(`/v1/meta${season ? `?season=${encodeURIComponent(season)}` : ''}`)
}

export const API_DOCS_URL = `${API_URL}/docs`
