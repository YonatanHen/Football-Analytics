import random

import pytest

from app.domain.models import Stats
from app.domain.scoring_engine import (
    ELITE_RAW,
    ScoringEngine,
    confidence_tier,
    effective_appearances,
    pillar_points,
    playing_time_bonus,
    score_confidence,
    to_fantasy_scale,
)


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


def test_forward_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = pillar_points(stats, "FW")
    # 5*4 + 3*3 + 4.0 + 2.5 = 20 + 9 + 6.5 = 35.5
    assert score.offensive == pytest.approx(35.5)


def test_midfielder_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=3, assists=5, xg=2.5, xa=4.0, minutes=900)
    score = pillar_points(stats, "MF")
    # 3*5 + 5*3 + 2.5 + 4.0 = 15 + 15 + 6.5 = 36.5
    assert score.offensive == pytest.approx(36.5)


def test_defender_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=2, assists=1, xg=1.5, xa=0.5, minutes=900)
    score = pillar_points(stats, "DF")
    # 2*6 + 1*4 + 1.5 + 0.5 = 12 + 4 + 2 = 18.0
    assert score.offensive == pytest.approx(18.0)


def test_goalkeeper_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=0, assists=1, xg=0.1, xa=0.2, minutes=900)
    score = pillar_points(stats, "GK")
    # 0*10 + 1*5 + 0.1 + 0.2 = 5.3
    assert score.offensive == pytest.approx(5.3)


def test_goalkeeper_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=2, minutes=900)
    score = pillar_points(stats, "GK")
    # 5*5 + 2*5 = 25 + 10 = 35
    assert score.defensive == pytest.approx(35.0)


def test_defender_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=3, minutes=900)
    score = pillar_points(stats, "DF")
    # 3*4 = 12
    assert score.defensive == pytest.approx(12.0)


def test_midfielder_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = pillar_points(stats, "MF")
    assert score.defensive == pytest.approx(0.0)


def test_forward_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = pillar_points(stats, "FW")
    assert score.defensive == pytest.approx(0.0)


def test_tactical_full(engine: ScoringEngine) -> None:
    stats = Stats(
        pk_won=2,
        pk_scored=3,
        pk_taken=4,
        yellow_cards=2,
        yellow_red_cards=1,
        direct_red_cards=1,
        fouls_committed=10,
        minutes=900,
        appearances=10,
        matches_started=10,
    )
    score = pillar_points(stats, "FW")
    # pk_ratio = 3/4 * 5 = 3.75
    # tactical = 2*2 + 3.75 - 2 - 1*2 - 1*4 - 10*0.2 = 4 + 3.75 - 2 - 2 - 4 - 2 = -2.25
    assert score.tactical == pytest.approx(-2.25)


def test_tactical_pk_ratio_zero_when_no_pk_taken(engine: ScoringEngine) -> None:
    stats = Stats(pk_scored=0, pk_taken=0, minutes=900)
    score = pillar_points(stats, "FW")
    assert score.tactical == pytest.approx(0.0)


def _bonus(avg_mins: float) -> float:
    return 0.5 * min(avg_mins, 59.0) / 59.0 + 0.5 * max(0.0, min(avg_mins, 90.0) - 59.0) / 31.0


def _scale(raw: float) -> float:
    return min(10.0, max(0.0, 10.0 * raw / ELITE_RAW))


def test_s_final_low_apps_confidence(engine: ScoringEngine) -> None:
    # 1 app → confidence=0.15; raw_per90=4.0, starter_bonus=1.2
    stats = Stats(goals=1, minutes=90, appearances=1, matches_started=1)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(_scale(4.0 * 1.2 * 0.15 + 0.15 * _bonus(90)), rel=1e-4)


def test_s_final_sub_low_apps(engine: ScoringEngine) -> None:
    # 45 minutes count as one full match (floor), so raw_per90 is 4.0, not 8.0
    stats = Stats(goals=1, minutes=45, appearances=1, matches_started=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(_scale(4.0 * 1.0 * 0.15 + 0.15 * _bonus(45)), rel=1e-4)


def test_s_final_zero_when_no_minutes(engine: ScoringEngine) -> None:
    # appearances > 0 so this exercises the minutes guard, not the appearances one
    stats = Stats(goals=5, minutes=0, appearances=3)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(0.0)


def test_missing_appearances_estimated_from_minutes(engine: ScoringEngine) -> None:
    # Legacy record: 900 min, no appearance count -> apps estimated as 10, confidence 0.50
    stats = Stats(goals=5, minutes=900, appearances=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(_scale(2.0 * 1.0 * 0.50 + 0.50 * _bonus(90)), rel=1e-4)


def test_missing_appearances_estimate_is_at_least_one(engine: ScoringEngine) -> None:
    # ceil(20/90) == 1, so a sub-90-minute record still gets a usable estimate.
    stats = Stats(goals=1, minutes=20, appearances=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final > 0.0


def test_starter_bonus_clamped_when_starts_exceed_estimated_appearances(
    engine: ScoringEngine,
) -> None:
    # matches_started can exceed an estimated apps count; the ratio must not exceed 1.
    stats = Stats(goals=1, minutes=90, appearances=0, matches_started=5)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(_scale(4.0 * 1.2 * 0.15 + 0.15 * _bonus(90)), rel=1e-4)


@pytest.mark.parametrize(("apps", "confidence"), [(2, 0.15), (5, 0.50), (15, 0.80), (20, 1.00)])
def test_confidence_tiers(engine: ScoringEngine, apps: int, confidence: float) -> None:
    # Minutes held constant so only the tier varies.
    stats = Stats(goals=1, minutes=1800, appearances=apps)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / 20  # FW: 1 goal x weight 4, over 1800 minutes
    expected = _scale(raw_per90 * 1.0 * confidence + confidence * _bonus(1800 / apps))
    assert score.s_final == pytest.approx(expected, rel=1e-4)


def test_confidence_capped_at_one_past_twenty_apps(engine: ScoringEngine) -> None:
    at_20 = engine.calculate(Stats(goals=1, minutes=1800, appearances=20), "FW")
    at_30 = engine.calculate(Stats(goals=1, minutes=1800, appearances=30), "FW")
    raw_per90 = 4.0 / 20
    assert at_20.s_final == pytest.approx(_scale(raw_per90 + _bonus(90.0)), rel=1e-4)
    assert at_30.s_final == pytest.approx(_scale(raw_per90 + _bonus(60.0)), rel=1e-4)


def test_s_final_late_minutes_bonus_higher(engine: ScoringEngine) -> None:
    # With 0 goals, raw_per90=0, so s_final comes from the bonus only.
    full = Stats(goals=0, minutes=1800, appearances=20, matches_started=20)  # avg=90
    short = Stats(goals=0, minutes=1180, appearances=20, matches_started=20)  # avg=59
    assert engine.calculate(full, "FW").s_final > engine.calculate(short, "FW").s_final


def test_starter_bonus_full_starter(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=1800, appearances=20, matches_started=20)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / (1800 / 90)
    assert score.s_final == pytest.approx(_scale(raw_per90 * 1.2 + _bonus(90)), rel=1e-4)


def test_starter_bonus_zero_starters(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=1800, appearances=20, matches_started=0)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / (1800 / 90)
    assert score.s_final == pytest.approx(_scale(raw_per90 + _bonus(90)), rel=1e-4)


def test_yellow_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(yellow_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = pillar_points(stats, "FW")
    assert score.tactical == pytest.approx(-2.0)


def test_direct_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(direct_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = pillar_points(stats, "FW")
    assert score.tactical == pytest.approx(-4.0)


def test_gk_goals_prevented_bonus(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=3.0, minutes=900, appearances=10, matches_started=10)
    score = pillar_points(stats, "GK")
    assert score.defensive == pytest.approx(3.0 * 2)


def test_gk_goals_prevented_negative(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=-2.0, minutes=900, appearances=10, matches_started=10)
    score = pillar_points(stats, "GK")
    assert score.defensive == pytest.approx(-2.0 * 2)


def test_negative_appearances_treated_as_missing(engine: ScoringEngine) -> None:
    # A negative count must not reach the arithmetic; it is treated like a missing one.
    corrupt = engine.calculate(Stats(goals=5, minutes=900, appearances=-3), "FW")
    missing = engine.calculate(Stats(goals=5, minutes=900, appearances=0), "FW")
    assert corrupt.s_final == pytest.approx(missing.s_final, rel=1e-9)


# --- 0-10 range ---


def test_one_card_in_one_minute_scores_zero(engine: ScoringEngine) -> None:
    # Before the floor this was -13.5: -1 point divided by 1/90 of a match.
    stats = Stats(yellow_cards=1, minutes=1, appearances=1)
    assert engine.calculate(stats, "MF").s_final == 0.0


def test_minutes_floor_is_one_full_match(engine: ScoringEngine) -> None:
    short = engine.calculate(Stats(goals=1, minutes=30, appearances=1), "FW")
    assert short.s_final == pytest.approx(_scale(4.0 * 1.0 * 0.15 + 0.15 * _bonus(30)), rel=1e-4)


def test_bonus_is_half_at_59_and_full_at_90() -> None:
    assert playing_time_bonus(Stats(minutes=1180), 20) == pytest.approx(0.5)
    assert playing_time_bonus(Stats(minutes=1800), 20) == pytest.approx(1.0)


def test_bonus_is_capped_when_average_exceeds_90() -> None:
    # A bad appearance count can give 300 minutes per game; the bonus must not pass 1.0.
    assert playing_time_bonus(Stats(minutes=300), 1) == pytest.approx(1.0)


def test_bonus_does_not_grow_with_total_minutes() -> None:
    # A second competition adds minutes but not a larger bonus.
    one_league = playing_time_bonus(Stats(minutes=900), 10)
    two_leagues = playing_time_bonus(Stats(minutes=3600), 40)
    assert one_league == pytest.approx(two_leagues)


@pytest.mark.parametrize(
    ("raw", "expected"), [(-3.0, 0.0), (0.0, 0.0), (4.0, 5.0), (8.0, 10.0), (20.0, 10.0)]
)
def test_to_fantasy_scale_is_linear_and_clamped(raw: float, expected: float) -> None:
    assert to_fantasy_scale(raw) == pytest.approx(expected)


def test_exceptional_season_is_capped_at_ten(engine: ScoringEngine) -> None:
    # Harry Kane 2025-26 combined: 12.09 under the old formula.
    stats = Stats(
        goals=50, assists=7, xg=36.19, xa=6.75, minutes=3421, appearances=44, matches_started=37
    )
    assert engine.calculate(stats, "FW").s_final == 10.0


def test_very_negative_goalkeeper_scores_zero(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=-40.0, minutes=2700, appearances=30, matches_started=30)
    assert engine.calculate(stats, "GK").s_final == 0.0


def test_score_is_always_between_zero_and_ten(engine: ScoringEngine) -> None:
    rng = random.Random(42)
    for _ in range(3000):
        stats = Stats(
            goals=rng.randint(0, 60),
            assists=rng.randint(0, 30),
            xg=rng.uniform(0, 50),
            xa=rng.uniform(0, 30),
            clean_sheets=rng.randint(0, 30),
            pk_saved=rng.randint(0, 5),
            goals_prevented=rng.uniform(-40, 20),
            pk_won=rng.randint(0, 6),
            pk_scored=rng.randint(0, 10),
            pk_taken=rng.randint(0, 12),
            yellow_cards=rng.randint(0, 15),
            yellow_red_cards=rng.randint(0, 3),
            direct_red_cards=rng.randint(0, 3),
            fouls_committed=rng.uniform(0, 90),
            minutes=rng.choice([0, 1, 5, 45, 90, rng.randint(0, 5000)]),
            appearances=rng.randint(-3, 50),
            matches_started=rng.randint(0, 60),
        )
        for position in ("GK", "DF", "MF", "FW"):
            s = engine.calculate(stats, position).s_final
            assert 0.0 <= s <= 10.0, (position, stats, s)


@pytest.mark.parametrize(
    ("apps", "expected"), [(0, 0.15), (4, 0.15), (5, 0.5), (14, 0.5), (15, 0.8), (20, 1.0)]
)
def test_confidence_tier_is_a_pure_lookup(apps: int, expected: float) -> None:
    assert confidence_tier(apps) == expected


def test_effective_appearances_estimates_from_minutes() -> None:
    assert effective_appearances(Stats(minutes=900)) == 10
    assert effective_appearances(Stats(minutes=900, appearances=12)) == 12
    assert effective_appearances(Stats()) == 0


# --- confidence counts minutes too (A) and scales the bonus (B) ---


def test_short_sub_appearances_do_not_earn_full_confidence() -> None:
    # 684 minutes over 24 appearances = 11 sixty-minute games -> the 0.50 tier, not 1.00.
    assert score_confidence(Stats(minutes=684, appearances=24)) == 0.50


def test_regular_sixty_minute_starters_keep_full_confidence() -> None:
    assert score_confidence(Stats(minutes=1200, appearances=20)) == 1.00


def test_confidence_is_the_lower_of_appearances_and_minutes() -> None:
    assert score_confidence(Stats(minutes=69, appearances=8)) == 0.15  # minutes decide
    assert score_confidence(Stats(minutes=3000, appearances=4)) == 0.15  # appearances decide


def test_legacy_record_confidence_uses_estimated_appearances() -> None:
    # apps estimated as ceil(900/90) = 10 -> 0.50; minutes give 15 games -> 0.80.
    assert score_confidence(Stats(minutes=900, appearances=0)) == 0.50


def test_bonus_is_scaled_by_confidence(engine: ScoringEngine) -> None:
    # One quiet full match: 1.25 before, now 0.15 x 1.0 bonus.
    stats = Stats(minutes=90, appearances=1, matches_started=1)
    assert engine.calculate(stats, "MF").s_final == pytest.approx(_scale(0.15 * 1.0))


def test_few_minutes_over_many_sub_appearances_are_damped(engine: ScoringEngine) -> None:
    # Same production as a regular starter, but in 684 minutes of 24 short appearances.
    stats = Stats(goals=8, assists=4, minutes=684, appearances=24, matches_started=2)
    per90 = (8 * 4 + 4 * 3) / (684 / 90)
    starter = 1 + 0.2 * (2 / 24)
    expected = _scale(per90 * starter * 0.50 + 0.50 * _bonus(684 / 24))
    assert engine.calculate(stats, "FW").s_final == pytest.approx(expected, rel=1e-4)


# --- pillar scores on 0-10 (same mechanism as s_final) ---


def test_offensive_pillar_is_scaled_on_zero_to_ten(engine: ScoringEngine) -> None:
    # 1 goal as FW over 1800 min, 20 sub apps: 4/20 per 90 x 1.0 x 1.0 -> 10 x 0.2 / 8.0
    stats = Stats(goals=1, minutes=1800, appearances=20)
    assert engine.calculate(stats, "FW").offensive == pytest.approx(0.25)


def test_defensive_pillar_is_scaled_on_zero_to_ten(engine: ScoringEngine) -> None:
    # 5 clean sheets as DF = 20 points over 20 full matches -> 1.0 per 90 -> 10 x 1.0 / 3.0
    stats = Stats(clean_sheets=5, minutes=1800, appearances=20)
    assert engine.calculate(stats, "DF").defensive == pytest.approx(10 / 3)


def test_outfield_midfielder_has_no_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, minutes=1800, appearances=20)
    assert engine.calculate(stats, "MF").defensive == 0.0


def test_clean_discipline_is_a_neutral_tactical_five(engine: ScoringEngine) -> None:
    stats = Stats(goals=3, minutes=1800, appearances=20)
    assert engine.calculate(stats, "FW").tactical == 5.0


def test_penalties_won_raise_tactical_above_five(engine: ScoringEngine) -> None:
    # 5 pk_won = 10 points over 20 matches -> 0.5 per 90 -> 5 + 5 x 0.5
    stats = Stats(pk_won=5, minutes=1800, appearances=20)
    assert engine.calculate(stats, "FW").tactical == pytest.approx(7.5)


def test_cards_lower_tactical_below_five_and_stop_at_zero(engine: ScoringEngine) -> None:
    some = Stats(yellow_cards=4, minutes=1800, appearances=20)  # -0.2 per 90 -> 4.0
    many = Stats(yellow_cards=40, minutes=1800, appearances=20)  # -2.0 per 90 -> clamp 0
    assert engine.calculate(some, "MF").tactical == pytest.approx(4.0)
    assert engine.calculate(many, "MF").tactical == 0.0


def test_low_confidence_pulls_tactical_toward_neutral(engine: ScoringEngine) -> None:
    # 1 yellow in 90 min: -1.0 per 90 x confidence 0.15 -> 5 - 0.75
    stats = Stats(yellow_cards=1, minutes=90, appearances=1)
    assert engine.calculate(stats, "MF").tactical == pytest.approx(4.25)


def test_exceptional_attacker_offensive_pillar_is_capped_at_ten(engine: ScoringEngine) -> None:
    stats = Stats(
        goals=50, assists=7, xg=36.19, xa=6.75, minutes=3421, appearances=44, matches_started=37
    )
    assert engine.calculate(stats, "FW").offensive == 10.0


def test_no_minutes_gives_zero_pillars_and_neutral_tactical(engine: ScoringEngine) -> None:
    score = engine.calculate(Stats(goals=5, yellow_cards=3, minutes=0, appearances=3), "FW")
    assert (score.offensive, score.defensive, score.tactical, score.s_final) == (0.0, 0.0, 5.0, 0.0)


def test_overall_score_still_uses_raw_pillar_points(engine: ScoringEngine) -> None:
    # Pillar display scaling must not change s_final: raw 4/20 per 90 + full bonus, conf 1.0.
    stats = Stats(goals=1, minutes=1800, appearances=20)
    assert engine.calculate(stats, "FW").s_final == pytest.approx(_scale(0.2 + _bonus(90)))


def test_every_pillar_is_always_between_zero_and_ten(engine: ScoringEngine) -> None:
    rng = random.Random(7)
    for _ in range(3000):
        stats = Stats(
            goals=rng.randint(0, 60),
            assists=rng.randint(0, 30),
            xg=rng.uniform(0, 50),
            xa=rng.uniform(0, 30),
            clean_sheets=rng.randint(0, 30),
            pk_saved=rng.randint(0, 5),
            goals_prevented=rng.uniform(-40, 20),
            pk_won=rng.randint(0, 6),
            pk_scored=rng.randint(0, 10),
            pk_taken=rng.randint(0, 12),
            yellow_cards=rng.randint(0, 15),
            yellow_red_cards=rng.randint(0, 3),
            direct_red_cards=rng.randint(0, 3),
            fouls_committed=rng.uniform(0, 90),
            minutes=rng.choice([0, 1, 5, 45, 90, rng.randint(0, 5000)]),
            appearances=rng.randint(-3, 50),
            matches_started=rng.randint(0, 60),
        )
        for position in ("GK", "DF", "MF", "FW"):
            score = engine.calculate(stats, position)
            for value in (score.offensive, score.defensive, score.tactical):
                assert 0.0 <= value <= 10.0, (position, stats, score)
