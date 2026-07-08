from app.infrastructure.sofascore_client import _season_to_sofascore_year


def test_converts_app_season_format() -> None:
    assert _season_to_sofascore_year("2025-2026") == "25/26"


def test_passes_through_native_club_format() -> None:
    assert _season_to_sofascore_year("25/26") == "25/26"


def test_passes_through_native_single_year_format() -> None:
    assert _season_to_sofascore_year("2026") == "2026"
