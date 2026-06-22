from pydantic import BaseModel


class StatsOut(BaseModel):
    """Flat player statistics for one competition or aggregated across all competitions."""

    goals: int
    assists: int
    xg: float
    xa: float
    minutes: int
    clean_sheets: int
    pk_saved: int
    pk_won: int
    pk_scored: int
    pk_taken: int
    yellow_cards: int
    red_cards: int
    yellow_red_cards: int
    direct_red_cards: int
    fouls_committed: float
    rating: float
    big_chances_created: int
    key_passes: int
    appearances: int
    matches_started: int
    saves: int
    saves_outside_box: int
    goals_conceded: int
    goals_prevented: float
    high_claims: int
    penalty_conceded: int
    penalty_faced: int
    total_shots: int
    shots_on_target: int
    shots_off_target: int
    scoring_frequency: float
    penalty_miss: int
    headed_goals: int
    left_foot_goals: int
    right_foot_goals: int


class ScoreOut(BaseModel):
    """Fantasy scores broken down by dimension plus the composite s_final."""

    offensive: float
    defensive: float
    tactical: float
    s_final: float


class CompetitionOut(BaseModel):
    """A player's stats and scores for a single competition within a season."""

    competition: str
    competition_type: str = "club"
    stats: StatsOut
    scores: ScoreOut
    raw_stats: dict = {}
    total_matches: int = 0


class AggregatedScoresOut(BaseModel):
    """Season-level fantasy scores including underprediction analysis across all competitions."""

    offensive: float
    defensive: float
    tactical: float
    s_final: float
    underpredicted_ratio: float | None
    underpredicted_flag: str | None


class PlayerOut(BaseModel):
    """Full player profile returned by GET /v1/players/{id} and the players list."""

    sofascore_player_id: str
    name: str
    season: str
    position: str
    position_exact: str
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionOut]
    aggregated_stats: StatsOut
    aggregated_scores: AggregatedScoresOut
    low_sample_size: bool
    last_updated: str


class PlayerListOut(BaseModel):
    """Paginated response envelope for GET /v1/players."""

    data: list[PlayerOut]
    total: int
    page: int
    page_size: int


class BioOut(BaseModel):
    nationality: str
    position_exact: str
