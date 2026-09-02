import pytest

from app.domain.models import Stats
from app.domain.scoring_engine import ScoringEngine


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


def test_forward_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = engine.calculate(stats, "FW")
    # 5*4 + 3*3 + 4.0 + 2.5 = 20 + 9 + 6.5 = 35.5
    assert score.offensive == pytest.approx(35.5)


def test_midfielder_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=3, assists=5, xg=2.5, xa=4.0, minutes=900)
    score = engine.calculate(stats, "MF")
    # 3*5 + 5*3 + 2.5 + 4.0 = 15 + 15 + 6.5 = 36.5
    assert score.offensive == pytest.approx(36.5)


def test_defender_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=2, assists=1, xg=1.5, xa=0.5, minutes=900)
    score = engine.calculate(stats, "DF")
    # 2*6 + 1*4 + 1.5 + 0.5 = 12 + 4 + 2 = 18.0
    assert score.offensive == pytest.approx(18.0)


def test_goalkeeper_offensive_score(engine: ScoringEngine) -> None:
    stats = Stats(goals=0, assists=1, xg=0.1, xa=0.2, minutes=900)
    score = engine.calculate(stats, "GK")
    # 0*10 + 1*5 + 0.1 + 0.2 = 5.3
    assert score.offensive == pytest.approx(5.3)


def test_goalkeeper_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=2, minutes=900)
    score = engine.calculate(stats, "GK")
    # 5*5 + 2*5 = 25 + 10 = 35
    assert score.defensive == pytest.approx(35.0)


def test_defender_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=3, minutes=900)
    score = engine.calculate(stats, "DF")
    # 3*4 = 12
    assert score.defensive == pytest.approx(12.0)


def test_midfielder_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = engine.calculate(stats, "MF")
    assert score.defensive == pytest.approx(0.0)


def test_forward_zero_defensive_score(engine: ScoringEngine) -> None:
    stats = Stats(clean_sheets=5, pk_saved=3, minutes=900)
    score = engine.calculate(stats, "FW")
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
    score = engine.calculate(stats, "FW")
    # pk_ratio = 3/4 * 5 = 3.75
    # tactical = 2*2 + 3.75 - 2 - 1*2 - 1*4 - 10*0.2 = 4 + 3.75 - 2 - 2 - 4 - 2 = -2.25
    assert score.tactical == pytest.approx(-2.25)


def test_tactical_pk_ratio_zero_when_no_pk_taken(engine: ScoringEngine) -> None:
    stats = Stats(pk_scored=0, pk_taken=0, minutes=900)
    score = engine.calculate(stats, "FW")
    assert score.tactical == pytest.approx(0.0)


def _bonus(apps: int, avg_mins: float) -> float:
    early = min(avg_mins, 59.0) * apps
    late = max(0.0, min(avg_mins, 90.0) - 59.0) * apps
    return early * 0.001 + late * 0.0015


def test_s_final_low_apps_confidence(engine: ScoringEngine) -> None:
    # 1 app → confidence=0.15; raw_per90=4.0, starter_bonus=1.2
    stats = Stats(goals=1, minutes=90, appearances=1, matches_started=1)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(4.0 * 1.2 * 0.15 + _bonus(1, 90), rel=1e-4)


def test_s_final_sub_low_apps(engine: ScoringEngine) -> None:
    # 1 sub app (45 min) → confidence=0.15; raw_per90=8.0, starter_bonus=1.0
    stats = Stats(goals=1, minutes=45, appearances=1, matches_started=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(8.0 * 1.0 * 0.15 + _bonus(1, 45), rel=1e-4)


def test_s_final_zero_when_no_minutes(engine: ScoringEngine) -> None:
    # appearances > 0 so this exercises the minutes guard, not the appearances one
    stats = Stats(goals=5, minutes=0, appearances=3)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(0.0)


def test_missing_appearances_estimated_from_minutes(engine: ScoringEngine) -> None:
    # Legacy record: 900 min, no appearance count -> apps estimated as 10, confidence 0.50
    stats = Stats(goals=5, minutes=900, appearances=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(2.0 * 1.0 * 0.50 + _bonus(10, 90), rel=1e-4)


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
    assert score.s_final == pytest.approx(4.0 * 1.2 * 0.15 + _bonus(1, 90), rel=1e-4)


@pytest.mark.parametrize(("apps", "confidence"), [(2, 0.15), (5, 0.50), (15, 0.80), (20, 1.00)])
def test_confidence_tiers(engine: ScoringEngine, apps: int, confidence: float) -> None:
    # Minutes held constant so only the tier varies; the expected value pins the constant.
    # (Scaling minutes with apps lets playing_time_bonus carry the assertion instead.)
    stats = Stats(goals=1, minutes=1800, appearances=apps)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / 20  # FW: 1 goal x weight 4, over 1800 minutes
    expected = raw_per90 * 1.0 * confidence + _bonus(apps, 1800 / apps)
    assert score.s_final == pytest.approx(expected, rel=1e-4)


def test_confidence_capped_at_one_past_twenty_apps(engine: ScoringEngine) -> None:
    at_20 = engine.calculate(Stats(goals=1, minutes=1800, appearances=20), "FW")
    at_30 = engine.calculate(Stats(goals=1, minutes=1800, appearances=30), "FW")
    raw_per90 = 4.0 / 20
    assert at_20.s_final == pytest.approx(raw_per90 + _bonus(20, 90.0), rel=1e-4)
    assert at_30.s_final == pytest.approx(raw_per90 + _bonus(30, 60.0), rel=1e-4)


def test_s_final_late_minutes_bonus_higher(engine: ScoringEngine) -> None:
    # With 0 goals, raw_per90=0, so s_final == playing_time_bonus only.
    # Full games (90 min avg) earn late-minute bonus; short stints (59 min avg) do not.
    full = Stats(goals=0, minutes=1800, appearances=20, matches_started=20)  # avg=90
    short = Stats(goals=0, minutes=1180, appearances=20, matches_started=20)  # avg=59
    assert engine.calculate(full, "FW").s_final > engine.calculate(short, "FW").s_final


def test_starter_bonus_full_starter(engine: ScoringEngine) -> None:
    # 20 full-game starts → confidence=1.0, starter_bonus=1.2
    stats = Stats(goals=1, minutes=1800, appearances=20, matches_started=20)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / (1800 / 90)
    assert score.s_final == pytest.approx(raw_per90 * 1.2 * 1.0 + _bonus(20, 90), rel=1e-4)


def test_starter_bonus_zero_starters(engine: ScoringEngine) -> None:
    # 20 sub appearances → confidence=1.0, starter_bonus=1.0
    stats = Stats(goals=1, minutes=1800, appearances=20, matches_started=0)
    score = engine.calculate(stats, "FW")
    raw_per90 = 4.0 / (1800 / 90)
    assert score.s_final == pytest.approx(raw_per90 * 1.0 * 1.0 + _bonus(20, 90), rel=1e-4)


def test_yellow_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(yellow_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW")
    assert score.tactical == pytest.approx(-2.0)


def test_direct_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(direct_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW")
    assert score.tactical == pytest.approx(-4.0)


def test_gk_goals_prevented_bonus(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=3.0, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "GK")
    assert score.defensive == pytest.approx(3.0 * 2)


def test_gk_goals_prevented_negative(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=-2.0, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "GK")
    assert score.defensive == pytest.approx(-2.0 * 2)


def test_negative_appearances_treated_as_missing(engine: ScoringEngine) -> None:
    # A negative count must not reach the arithmetic: it would make avg_mins negative and
    # min(-300, 59) * -3 a positive bonus, i.e. a silently wrong score.
    corrupt = engine.calculate(Stats(goals=5, minutes=900, appearances=-3), "FW")
    missing = engine.calculate(Stats(goals=5, minutes=900, appearances=0), "FW")
    assert corrupt.s_final == pytest.approx(missing.s_final, rel=1e-9)
