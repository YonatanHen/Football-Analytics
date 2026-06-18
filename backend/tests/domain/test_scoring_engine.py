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
        red_cards=1,
        fouls_committed=10,
        minutes=900,
    )
    score = engine.calculate(stats, "FW")
    # pk_ratio = 3/4 * 5 = 3.75
    # tactical = 2*2 + 3.75 - 2 - 1*3 - 10*0.2 = 4 + 3.75 - 2 - 3 - 2 = 0.75
    assert score.tactical == pytest.approx(0.75)


def test_tactical_pk_ratio_zero_when_no_pk_taken(engine: ScoringEngine) -> None:
    stats = Stats(pk_scored=0, pk_taken=0, minutes=900)
    score = engine.calculate(stats, "FW")
    assert score.tactical == pytest.approx(0.0)


def test_s_final_normalized_by_90_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=90)
    score = engine.calculate(stats, "FW")
    # offensive = 1*4 = 4, s_final = 4 / 1 = 4.0
    assert score.s_final == pytest.approx(4.0)


def test_s_final_half_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=1, minutes=45)
    score = engine.calculate(stats, "FW")
    # s_final = 4 / 0.5 = 8.0
    assert score.s_final == pytest.approx(8.0)


def test_s_final_zero_when_no_minutes(engine: ScoringEngine) -> None:
    stats = Stats(goals=5, minutes=0)
    score = engine.calculate(stats, "FW")
    assert score.s_final == pytest.approx(0.0)
