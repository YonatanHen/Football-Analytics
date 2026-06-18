from dataclasses import dataclass, field


@dataclass
class Stats:
    goals: int = 0
    assists: int = 0
    xg: float = 0.0
    xa: float = 0.0
    minutes: int = 0
    clean_sheets: int = 0
    pk_saved: int = 0
    pk_won: int = 0
    pk_scored: int = 0
    pk_taken: int = 0
    yellow_cards: int = 0
    red_cards: int = 0  # total reds (display only; not used in scoring)
    yellow_red_cards: int = 0  # 2nd yellow → red
    direct_red_cards: int = 0  # straight red
    fouls_committed: float = 0.0
    rating: float = 0.0
    big_chances_created: int = 0
    key_passes: int = 0
    # Appearance metrics
    appearances: int = 0
    matches_started: int = 0
    # GK metrics
    saves: int = 0
    saves_outside_box: int = 0
    goals_conceded: int = 0
    goals_prevented: float = 0.0
    high_claims: int = 0
    penalty_conceded: int = 0
    penalty_faced: int = 0
    # Shots
    total_shots: int = 0
    shots_on_target: int = 0
    shots_off_target: int = 0
    scoring_frequency: float = 0.0
    penalty_miss: int = 0
    # Goal breakdown
    headed_goals: int = 0
    left_foot_goals: int = 0
    right_foot_goals: int = 0


@dataclass
class Score:
    offensive: float
    defensive: float
    tactical: float
    s_final: float


@dataclass
class CompetitionEntry:
    competition: str
    stats: Stats
    scores: Score
    raw_stats: dict = field(default_factory=dict)
    total_matches: int = 0  # matches played in this competition at fetch time


@dataclass
class AggregatedScores:
    offensive: float
    defensive: float
    tactical: float
    s_final: float
    underpredicted_ratio: float | None
    underpredicted_flag: str | None


@dataclass
class PlayerDTO:
    sofascore_player_id: str
    name: str
    season: str
    position: str
    position_exact: str
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionEntry]
    aggregated_stats: Stats
    aggregated_scores: AggregatedScores
    low_sample_size: bool
    last_updated: str
