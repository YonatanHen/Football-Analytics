import { apiFetch } from './client'

export interface Stats {
  goals: number; assists: number; xg: number; xa: number
  minutes: number; clean_sheets: number; pk_saved: number; pk_won: number
  pk_scored: number; pk_taken: number; yellow_cards: number; red_cards: number
  fouls_committed: number; rating: number; big_chances_created: number; key_passes: number
}

export interface Score {
  offensive: number; defensive: number; tactical: number; s_final: number
}

export interface CompetitionEntry {
  competition: string; stats: Stats; scores: Score
}

export interface AggregatedScores extends Score {
  sleeper_ratio: number | null; sleeper_flag: 'HIGH_VALUE' | 'OVERPERFORMING' | null
}

export interface Player {
  player_id: string; name: string; season: string
  position: string; position_exact: string; team: string; nationality: string
  photo_url: string; competitions: CompetitionEntry[]
  aggregated_stats: Stats; aggregated_scores: AggregatedScores
  low_sample_size: boolean; last_updated: string
}

export interface PlayerList {
  data: Player[]; total: number; page: number; page_size: number
}

export interface ScatterPoint {
  player_id: string; name: string; position: string; xg_xa: number; g_a: number
}

export interface ScatterData { data: ScatterPoint[] }

export async function getPlayers(params: Record<string, string | number | undefined> = {}): Promise<PlayerList> {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString()
  return apiFetch<PlayerList>(`/v1/players${qs ? `?${qs}` : ''}`)
}

export async function getPlayer(playerId: string, season?: string): Promise<Player> {
  const qs = season ? `?season=${season}` : ''
  return apiFetch<Player>(`/v1/players/${playerId}${qs}`)
}

export async function getScatterData(season?: string): Promise<ScatterData> {
  const qs = season ? `?season=${season}` : ''
  return apiFetch<ScatterData>(`/v1/analysis/scatter${qs}`)
}
