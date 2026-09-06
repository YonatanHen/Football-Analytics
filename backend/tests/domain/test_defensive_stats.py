import pytest

from app.domain.defensive_stats import DEFENSIVE_RAW_MAP, apply_defensive_raw, recompute_rates
from app.domain.metric_fields import METRIC_FIELDS
from app.domain.models import CompetitionEntry, Score, Stats
from app.domain.player_assembler import aggregate_stats

DEFENSIVE_COUNTS = [
    "tackles",
    "tackles_won",
    "interceptions",
    "clearances",
    "blocks",
    "aerial_duels_won",
    "aerial_lost",
    "ball_recoveries",
    "dribbled_past",
    "errors_lead_to_goal",
    "errors_lead_to_shot",
]
DEFENSIVE_RATES = ["tackles_won_pct", "aerial_duels_won_pct"]


def _entry(competition: str, **stats) -> CompetitionEntry:
    return CompetitionEntry(
        competition=competition,
        stats=Stats(**stats),
        scores=Score(offensive=0.0, defensive=0.0, tactical=0.0, s_final=0.0),
        raw_stats={},
        total_matches=38,
        competition_type="club",
    )


def test_stats_declares_every_defensive_field_defaulting_to_zero():
    s = Stats()
    for field in DEFENSIVE_COUNTS + DEFENSIVE_RATES:
        assert getattr(s, field) == 0, f"{field} should default to 0"


def test_defensive_fields_are_queryable_metrics():
    for field in DEFENSIVE_COUNTS + DEFENSIVE_RATES:
        assert field in METRIC_FIELDS, f"{field} must be sortable/filterable"


def test_apply_defensive_raw_maps_sofascore_columns():
    stats = Stats()
    apply_defensive_raw(
        stats,
        {
            "tackles": 46.0,
            "tacklesWon": 30.0,
            "interceptions": 50.0,
            "clearances": 164.0,
            "outfielderBlocks": 12.0,
            "aerialDuelsWon": 60.0,
            "aerialLost": 40.0,
            "ballRecovery": 88.0,
            "dribbledPast": 21.0,
            "errorLeadToGoal": 1.0,
            "errorLeadToShot": 3.0,
        },
    )
    assert stats.tackles == 46
    assert stats.tackles_won == 30
    assert stats.interceptions == 50
    assert stats.clearances == 164
    assert stats.blocks == 12
    assert stats.aerial_duels_won == 60
    assert stats.aerial_lost == 40
    assert stats.ball_recoveries == 88
    assert stats.dribbled_past == 21
    assert stats.errors_lead_to_goal == 1
    assert stats.errors_lead_to_shot == 3


def test_apply_defensive_raw_tolerates_missing_and_null_columns():
    # GK rows and older documents do not carry every column.
    stats = Stats()
    apply_defensive_raw(stats, {"tackles": None, "interceptions": 7.0})
    assert stats.tackles == 0
    assert stats.interceptions == 7
    assert stats.clearances == 0


def test_recompute_rates_derives_percentages_from_counts():
    stats = Stats(tackles=100, tackles_won=54, aerial_duels_won=60, aerial_lost=40)
    recompute_rates(stats)
    assert stats.tackles_won_pct == pytest.approx(54.0)
    assert stats.aerial_duels_won_pct == pytest.approx(60.0)


def test_recompute_rates_is_zero_when_the_denominator_is_zero():
    stats = Stats(tackles=0, tackles_won=0, aerial_duels_won=0, aerial_lost=0)
    recompute_rates(stats)
    assert stats.tackles_won_pct == 0.0
    assert stats.aerial_duels_won_pct == 0.0


def test_aggregate_sums_defensive_counts_across_competitions():
    agg = aggregate_stats(
        [
            _entry("England Premier League", minutes=900, tackles=46, interceptions=50, blocks=4),
            _entry("UEFA Champions League", minutes=450, tackles=14, interceptions=10, blocks=2),
        ]
    )
    assert agg.tackles == 60
    assert agg.interceptions == 60
    assert agg.blocks == 6


def test_aggregate_recomputes_tackle_success_from_summed_counts_not_averaged():
    # 90% over 10 tackles and 50% over 90 tackles average to 70%, but the true
    # combined rate is 54/100 = 54%. Averaging percentages is the bug this pins.
    agg = aggregate_stats(
        [
            _entry("England Premier League", minutes=900, tackles=10, tackles_won=9),
            _entry("UEFA Champions League", minutes=900, tackles=90, tackles_won=45),
        ]
    )
    assert agg.tackles == 100
    assert agg.tackles_won == 54
    assert agg.tackles_won_pct == pytest.approx(54.0)


def test_aggregate_recomputes_aerial_success_from_summed_counts():
    agg = aggregate_stats(
        [
            _entry("England Premier League", minutes=900, aerial_duels_won=9, aerial_lost=1),
            _entry("UEFA Champions League", minutes=900, aerial_duels_won=45, aerial_lost=45),
        ]
    )
    assert agg.aerial_duels_won == 54
    assert agg.aerial_lost == 46
    assert agg.aerial_duels_won_pct == pytest.approx(54.0)


def test_defensive_raw_map_targets_only_real_stats_fields():
    valid = {f for f in Stats().__dict__}
    for raw_key, field in DEFENSIVE_RAW_MAP.items():
        assert field in valid, f"{raw_key} maps to unknown Stats field {field}"


def test_defensive_fields_survive_the_mongo_round_trip():
    from app.infrastructure.mongo_repository import _stats_from_dict, _stats_to_dict

    original = Stats(minutes=900, tackles=46, tackles_won=30, interceptions=50, clearances=164)
    restored = _stats_from_dict(_stats_to_dict(original))
    assert restored == original


def test_stats_from_dict_ignores_unknown_keys_from_older_documents():
    from app.infrastructure.mongo_repository import _stats_from_dict

    restored = _stats_from_dict({"goals": 3, "a_field_we_removed": 99})
    assert restored.goals == 3
    assert restored.tackles == 0


def test_stats_out_exposes_every_stats_field():
    from app.api.modals.player_modals import StatsOut

    missing = set(Stats().__dict__) - set(StatsOut.model_fields)
    assert not missing, f"StatsOut silently drops: {sorted(missing)}"
