from datetime import UTC, datetime

from app.domain.competitions import canonical_competition
from app.domain.models import AggregatedScores, CompetitionEntry, PlayerDTO, Stats
from app.domain.scoring_engine import ScoringEngine
from app.domain.sleeper_detector import SleeperDetector

_scoring = ScoringEngine()
_sleeper = SleeperDetector()


def aggregate_stats(entries: list[CompetitionEntry]) -> Stats:
    """Sum per-competition Stats across all entries; use max rating instead of sum."""
    total = Stats()
    for e in entries:
        s = e.stats
        total.goals += s.goals
        total.assists += s.assists
        total.xg += s.xg
        total.xa += s.xa
        total.minutes += s.minutes
        total.clean_sheets += s.clean_sheets
        total.pk_saved += s.pk_saved
        total.pk_won += s.pk_won
        total.pk_scored += s.pk_scored
        total.pk_taken += s.pk_taken
        total.yellow_cards += s.yellow_cards
        total.red_cards += s.red_cards
        total.fouls_committed += s.fouls_committed
        total.rating = max(total.rating, s.rating)
        total.big_chances_created += s.big_chances_created
        total.key_passes += s.key_passes
        total.appearances += s.appearances
        total.matches_started += s.matches_started
        total.yellow_red_cards += s.yellow_red_cards
        total.direct_red_cards += s.direct_red_cards
        total.saves += s.saves
        total.saves_outside_box += s.saves_outside_box
        total.goals_conceded += s.goals_conceded
        total.goals_prevented += s.goals_prevented
        total.high_claims += s.high_claims
        total.penalty_conceded += s.penalty_conceded
        total.penalty_faced += s.penalty_faced
        total.total_shots += s.total_shots
        total.shots_on_target += s.shots_on_target
        total.shots_off_target += s.shots_off_target
        total.penalty_miss += s.penalty_miss
        total.headed_goals += s.headed_goals
        total.left_foot_goals += s.left_foot_goals
        total.right_foot_goals += s.right_foot_goals
    total.scoring_frequency = (total.minutes / total.goals) if total.goals > 0 else 0.0
    return total


def build_player(
    meta: dict,
    entries: list[CompetitionEntry],
    season: str,
) -> PlayerDTO:
    """Construct a fully scored PlayerDTO from raw meta + competition entries."""
    agg_stats = aggregate_stats(entries)
    agg_score = _scoring.calculate(agg_stats, meta["position"])
    return PlayerDTO(
        sofascore_player_id=meta.get("sofascore_player_id"),
        name=meta["name"],
        season=season,
        position=meta["position"],
        position_exact=meta.get("position_exact", ""),
        team=meta["team"],
        nationality=meta.get("nationality", ""),
        photo_url=meta.get("photo_url", ""),
        competitions=entries,
        aggregated_stats=agg_stats,
        aggregated_scores=AggregatedScores(
            offensive=agg_score.offensive,
            defensive=agg_score.defensive,
            tactical=agg_score.tactical,
            s_final=agg_score.s_final,
            underpredicted_ratio=_sleeper.get_ratio(
                agg_stats.xg, agg_stats.xa, agg_stats.goals, agg_stats.assists
            ),
            underpredicted_flag=_sleeper.classify(
                agg_stats.xg,
                agg_stats.xa,
                agg_stats.goals,
                agg_stats.assists,
                agg_stats.minutes,
            ),
        ),
        low_sample_size=agg_stats.minutes < 90,
        last_updated=datetime.now(UTC).isoformat(),
    )


def merge(existing: PlayerDTO | None, incoming: PlayerDTO) -> PlayerDTO:
    """Merge incoming player data into an existing doc.

    Rules:
    - competitions[] is keyed by canonical competition name; incoming entry replaces
      an existing same-canonical entry (within the same season), otherwise appended.
    - Fantasy identity fields (sofascore_player_id, photo_url, position_exact) supersede
      whatever was in the existing doc when present in incoming.
    - Re-aggregates and re-scores over the merged competition set.
    """
    if existing is None:
        return incoming

    # Canonicalize and de-duplicate: incoming entries win for same competition
    merged_entries: dict[str, CompetitionEntry] = {
        canonical_competition(e.competition): e for e in existing.competitions
    }
    for e in incoming.competitions:
        merged_entries[canonical_competition(e.competition)] = e

    entries = list(merged_entries.values())

    # Build merged meta; prefer non-empty incoming fields for identity/media
    meta = {
        "sofascore_player_id": incoming.sofascore_player_id or existing.sofascore_player_id,
        "name": incoming.name or existing.name,
        "position": incoming.position or existing.position,
        "position_exact": incoming.position_exact or existing.position_exact,
        "team": incoming.team or existing.team,
        "nationality": incoming.nationality or existing.nationality,
        "photo_url": incoming.photo_url or existing.photo_url,
    }

    return build_player(meta, entries, incoming.season)
