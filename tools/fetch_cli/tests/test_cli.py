from fetch_cli.cli import _to_app_season


def test_club_season_expands_to_app_format() -> None:
    assert _to_app_season("25/26") == "2025-2026"


def test_club_season_handles_century_rollover() -> None:
    assert _to_app_season("99/00") == "1999-2000"


def test_club_season_handles_nineties() -> None:
    assert _to_app_season("92/93") == "1992-1993"


def test_single_year_tournament_passes_through() -> None:
    assert _to_app_season("2026") == "2026"
