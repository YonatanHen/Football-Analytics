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
  competition: string; competition_type: string; stats: Stats; scores: Score
  raw_stats: Record<string, unknown>; total_matches: number
}

export interface CompetitionList { club: string[]; national: string[] }

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

export type SortOrder = 'asc' | 'desc'
export type FilterOp = 'gte' | 'lte' | 'gt' | 'lt' | 'eq' | 'ne'

export interface FilterClause { field: string; op: FilterOp; value: number }

// Allowlisted sortable/filterable metrics — mirrors backend metric_fields.METRIC_FIELDS.
export const METRIC_OPTIONS: { value: string; label: string }[] = [
  { value: 's_final', label: 'S_final' },
  { value: 'goals', label: 'Goals' },
  { value: 'assists', label: 'Assists' },
  { value: 'xg', label: 'xG' },
  { value: 'xa', label: 'xA' },
  { value: 'minutes', label: 'Minutes' },
  { value: 'rating', label: 'Rating' },
  { value: 'clean_sheets', label: 'Clean sheets' },
  { value: 'key_passes', label: 'Key passes' },
  { value: 'big_chances_created', label: 'Big chances created' },
  { value: 'total_shots', label: 'Total shots' },
  { value: 'shots_on_target', label: 'Shots on target' },
  { value: 'shots_off_target', label: 'Shots off target' },
  { value: 'appearances', label: 'Appearances' },
  { value: 'matches_started', label: 'Matches started' },
  { value: 'yellow_cards', label: 'Yellow cards' },
  { value: 'red_cards', label: 'Red cards' },
  { value: 'fouls_committed', label: 'Fouls committed' },
  { value: 'saves', label: 'Saves' },
  { value: 'saves_outside_box', label: 'Saves outside box' },
  { value: 'goals_conceded', label: 'Goals conceded' },
  { value: 'goals_prevented', label: 'Goals prevented' },
  { value: 'high_claims', label: 'High claims' },
  { value: 'pk_scored', label: 'Penalties scored' },
  { value: 'pk_won', label: 'Penalties won' },
  { value: 'headed_goals', label: 'Headed goals' },
  { value: 'left_foot_goals', label: 'Left-foot goals' },
  { value: 'right_foot_goals', label: 'Right-foot goals' },
  { value: 'offensive', label: 'Offensive score' },
  { value: 'defensive', label: 'Defensive score' },
  { value: 'tactical', label: 'Tactical score' },
]

export const FILTER_OP_OPTIONS: { value: FilterOp; label: string }[] = [
  { value: 'gte', label: '≥' },
  { value: 'lte', label: '≤' },
  { value: 'gt', label: '>' },
  { value: 'lt', label: '<' },
  { value: 'eq', label: '=' },
  { value: 'ne', label: '≠' },
]

// Serialize valid clauses to the JSON the backend `filters` query param expects; '' if none.
export function serializeFilters(clauses: FilterClause[]): string {
  const valid = clauses.filter((c) => c.field && Number.isFinite(c.value))
  return valid.length ? JSON.stringify(valid) : ''
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

export interface BioData { nationality: string; position_exact: string }

export async function refreshBio(playerId: string): Promise<BioData> {
  return apiFetch<BioData>(`/v1/players/${playerId}/refresh-bio`, { method: 'POST' })
}

export async function getPlayerCompetitions(season?: string): Promise<CompetitionList> {
  const qs = season ? `?season=${season}` : ''
  return apiFetch<CompetitionList>(`/v1/players/competitions${qs}`)
}
