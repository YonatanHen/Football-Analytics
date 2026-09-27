from datetime import date

from app.agent.season import calendar_season, previous_season


def test_autumn_belongs_to_the_season_that_started_this_year():
    assert calendar_season(date(2026, 9, 27)) == "2026-2027"


def test_spring_belongs_to_the_season_that_started_last_year():
    assert calendar_season(date(2027, 3, 1)) == "2026-2027"


def test_a_new_season_starts_in_july():
    assert calendar_season(date(2026, 6, 30)) == "2025-2026"
    assert calendar_season(date(2026, 7, 1)) == "2026-2027"


def test_previous_season():
    assert previous_season("2026-2027") == "2025-2026"
