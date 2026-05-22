import pytest
from app.domain.sleeper_detector import SleeperDetector


@pytest.fixture
def detector() -> SleeperDetector:
    return SleeperDetector()


def test_high_value_sleeper(detector: SleeperDetector) -> None:
    result = detector.classify(xg=2.0, xa=1.5, goals=1, assists=0, minutes=500)
    assert result == "HIGH_VALUE"


def test_high_value_requires_more_than_450_minutes(detector: SleeperDetector) -> None:
    result = detector.classify(xg=2.0, xa=1.5, goals=1, assists=0, minutes=450)
    assert result is None


def test_overperforming(detector: SleeperDetector) -> None:
    # ratio = (0.5+0.2)/(3+1) = 0.175 < 0.8
    result = detector.classify(xg=0.5, xa=0.2, goals=3, assists=1, minutes=800)
    assert result == "OVERPERFORMING"


def test_no_flag_when_ratio_in_range(detector: SleeperDetector) -> None:
    # ratio = 1.0/1 = 1.0, between 0.8 and 1.2
    result = detector.classify(xg=1.0, xa=0.0, goals=1, assists=0, minutes=900)
    assert result is None


def test_zero_output_with_xg_and_enough_minutes(detector: SleeperDetector) -> None:
    result = detector.classify(xg=1.0, xa=0.5, goals=0, assists=0, minutes=500)
    assert result == "HIGH_VALUE"


def test_zero_output_with_xg_but_not_enough_minutes(detector: SleeperDetector) -> None:
    result = detector.classify(xg=1.0, xa=0.5, goals=0, assists=0, minutes=300)
    assert result is None


def test_zero_everything_returns_none(detector: SleeperDetector) -> None:
    result = detector.classify(xg=0.0, xa=0.0, goals=0, assists=0, minutes=500)
    assert result is None


def test_get_ratio_returns_none_when_no_output(detector: SleeperDetector) -> None:
    assert detector.get_ratio(xg=1.0, xa=0.5, goals=0, assists=0) is None


def test_get_ratio_calculates_correctly(detector: SleeperDetector) -> None:
    # (2.0 + 1.0) / (1 + 2) = 1.0
    assert detector.get_ratio(xg=2.0, xa=1.0, goals=1, assists=2) == pytest.approx(1.0)
