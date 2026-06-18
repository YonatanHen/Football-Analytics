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
        pk_won=2, pk_scored=3, pk_taken=4,
        yellow_cards=2, yellow_red_cards=1, direct_red_cards=1,
        fouls_committed=10,
        minutes=900, appearances=10, matches_started=10,
    )
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    # pk_ratio = 3/4 * 5 = 3.75
    # tactical = 2*2 + 3.75 - 2 - 1*2 - 1*4 - 10*0.2 = 4 + 3.75 - 2 - 2 - 4 - 2 = -2.25
    assert score.tactical == pytest.approx(-2.25)


def test_tactical_pk_ratio_zero_when_no_pk_taken(engine: ScoringEngine) -> None:
    stats = Stats(pk_scored=0, pk_taken=0, minutes=900)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    assert score.tactical == pytest.approx(0.0)


def test_s_final_normalized_by_90_minutes(engine: ScoringEngine) -> None:
    # 1 goal in 90 min, 1 start out of 1 match played → factor=1.0, starter_bonus=1.2
    stats = Stats(goals=1, minutes=90, appearances=1, matches_started=1)
    score = engine.calculate(stats, "FW", total_possible_minutes=90)
    assert score.s_final == pytest.approx(4.0 * 1.0 * 1.2)


def test_s_final_half_minutes(engine: ScoringEngine) -> None:
    # sub: 45 min in 1 match, total 1 match played → factor=45/90=0.5, no starter bonus
    stats = Stats(goals=1, minutes=45, appearances=1, matches_started=0)
    score = engine.calculate(stats, "FW", total_possible_minutes=90)
    raw_per90 = 4.0 / (45 / 90)  # = 8.0
    assert score.s_final == pytest.approx(raw_per90 * 0.5 * 1.0)


def test_s_final_zero_when_no_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, minutes=0)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    assert score.s_final == pytest.approx(0.0)


def test_s_final_legacy_no_total_matches_factor_one(engine: ScoringEngine) -> None:
    # When total_possible_minutes=0 (legacy/unknown), factor defaults to 1.0
    stats = Stats(goals=1, minutes=90, appearances=1, matches_started=1)
    score = engine.calculate(stats, "FW", total_possible_minutes=0)
    assert score.s_final == pytest.approx(4.0 * 1.0 * 1.2)


def test_playing_time_factor_dampens_low_minutes(engine: ScoringEngine) -> None:
    # 1 match out of 10 played → factor = 90/900
    stats = Stats(goals=1, minutes=90, appearances=1, matches_started=1)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    assert score.s_final == pytest.approx(4.0 * (90 / 900) * 1.2, rel=1e-4)


def test_playing_time_factor_caps_at_one(engine: ScoringEngine) -> None:
    # Played all available minutes → factor = 1.0
    stats = Stats(goals=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    raw_per90 = 4.0 / 10
    assert score.s_final == pytest.approx(raw_per90 * 1.0 * 1.2, rel=1e-4)


def test_starter_bonus_full_starter(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    raw_per90 = 4.0 / (900 / 90)
    assert score.s_final == pytest.approx(raw_per90 * 1.0 * 1.2, rel=1e-4)


def test_starter_bonus_zero_starter(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=900, appearances=10, matches_started=0)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    raw_per90 = 4.0 / (900 / 90)
    assert score.s_final == pytest.approx(raw_per90 * 1.0 * 1.0, rel=1e-4)


def test_yellow_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(yellow_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    assert score.tactical == pytest.approx(-2.0)


def test_direct_red_card_penalty(engine: ScoringEngine) -> None:
    stats = Stats(direct_red_cards=1, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "FW", total_possible_minutes=900)
    assert score.tactical == pytest.approx(-4.0)


def test_gk_goals_prevented_bonus(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=3.0, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "GK", total_possible_minutes=900)
    assert score.defensive == pytest.approx(3.0 * 2)


def test_gk_goals_prevented_negative(engine: ScoringEngine) -> None:
    stats = Stats(goals_prevented=-2.0, minutes=900, appearances=10, matches_started=10)
    score = engine.calculate(stats, "GK", total_possible_minutes=900)
    assert score.defensive == pytest.approx(-2.0 * 2)
