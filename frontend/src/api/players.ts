import { apiFetch } from './client'

export interface Stats {
  goals: number; assists: number; xg: number; xa: number
  minutes: number; clean_sheets: number; pk_saved: number; pk_won: number
  pk_scored: number; pk_taken: number; yellow_cards: number; red_cards: number
  yellow_red_cards: number; direct_red_cards: number
  fouls_committed: number; rating: number; big_chances_created: number; key_passes: number
  appearances: number; matches_started: number
  saves: number; saves_outside_box: number
  goals_conceded: number; goals_prevented: number
  high_claims: number; penalty_conceded: number; penalty_faced: number
  total_shots: number; shots_on_target: number; shots_off_target: number
  scoring_frequency: number; penalty_miss: number
  headed_goals: number; left_foot_goals: number; right_foot_goals: number
}

export interface Score {
  offensive: number; defensive: number; tactical: number; s_final: number
}

export interface CompetitionEntry {
  competition: string; stats: Stats; scores: Score
  raw_stats: Record<string, unknown>; total_matches: number
}

export interface AggregatedScores extends Score {
  underpredicted_ratio: number | null; underpredicted_flag: 'HIGH_VALUE' | 'OVERPERFORMING' | null
}

export interface Player {
  sofascore_player_id: string; name: string; season: string
  position: string; position_exact: string; team: string; nationality: string
  photo_url: string; competitions: CompetitionEntry[]
  aggregated_stats: Stats; aggregated_scores: AggregatedScores
  low_sample_size: boolean; last_updated: string
}

export interface PlayerList {
  data: Player[]; total: number; page: number; page_size: number
}

export interface ScatterPoint {
  sofascore_player_id: string | null; name: string; position: string; xg_xa: number; g_a: number
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
