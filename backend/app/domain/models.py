from dataclasses import dataclass
from typing import Optional


@dataclass
class Stats:
    """Raw performance statistics for one competition or aggregated across competitions."""
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
    red_cards: int = 0
    fouls_committed: float = 0.0
    rating: float = 0.0
    big_chances_created: int = 0
    key_passes: int = 0


@dataclass
class Score:
    """Fantasy score for one competition, broken into offensive/defensive/tactical dimensions."""
    offensive: float
    defensive: float
    tactical: float
    s_final: float


@dataclass
class CompetitionEntry:
    """Stats and scores for a player in a single competition."""
    competition: str
    stats: Stats
    scores: Score


@dataclass
class AggregatedScores:
    """Season-level fantasy scores summed across all competitions, plus prediction classification."""
    offensive: float
    defensive: float
    tactical: float
    s_final: float
    underpredicted_ratio: Optional[float]
    underpredicted_flag: Optional[str]  # "HIGH_VALUE" | "OVERPERFORMING" | None


@dataclass
class PlayerDTO:
    """Complete player record stored in MongoDB and passed between all application layers."""
    sofascore_player_id: Optional[str]  # Sofascore numeric ID; None for FBref/Kaggle players
    name: str
    season: str             # "2025-2026"
    position: str           # GK | DF | MF | FW
    position_exact: str     # raw position e.g. "RW", "CB"
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionEntry]
    aggregated_stats: Stats
    aggregated_scores: AggregatedScores
    low_sample_size: bool   # True when aggregated minutes < 90
    last_updated: str       # ISO 8601 UTC
