import argparse
from pathlib import Path
from unittest.mock import patch

import requests

from fetch_cli.catalog_repository import CatalogRepository, SeasonInfo
from fetch_cli.cli import _cmd_refresh, _current_task_label, _to_app_season, _top_n_seasons


def test_club_season_expands_to_app_format() -> None:
    assert _to_app_season("25/26") == "2025-2026"


def test_club_season_handles_century_rollover() -> None:
    assert _to_app_season("99/00") == "1999-2000"


def test_club_season_handles_nineties() -> None:
    assert _to_app_season("92/93") == "1992-1993"


def test_single_year_tournament_passes_through() -> None:
    assert _to_app_season("2026") == "2026"


def test_club_season_century_boundary_stays_consistent() -> None:
    # Both halves must land in the same century-adjacent range, not diverge
    # independently (a naive per-half heuristic would produce "2030-1931").
    assert _to_app_season("30/31") == "2030-2031"


def test_top_n_seasons_returns_most_recent_first() -> None:
    valid = {"23/24": 52186, "25/26": 76986, "24/25": 61627}
    assert _top_n_seasons(valid, 2) == [("25/26", 76986), ("24/25", 61627)]


def test_top_n_seasons_n_larger_than_available() -> None:
    valid = {"25/26": 76986}
    assert _top_n_seasons(valid, 5) == [("25/26", 76986)]


def test_current_task_label_lists_all_running_tasks() -> None:
    status = {
        "current": "UEFA Champions League — Forwards",
        "status": "running",
        "tasks": [
            {"label": "UEFA Champions League — Goalkeepers", "status": "done"},
            {"label": "UEFA Champions League — Defenders", "status": "running"},
            {"label": "UEFA Champions League — Midfielders", "status": "running"},
            {"label": "UEFA Champions League — Forwards", "status": "pending"},
        ],
    }
    assert _current_task_label(status) == (
        "UEFA Champions League — Defenders, UEFA Champions League — Midfielders"
    )


def test_current_task_label_falls_back_when_nothing_running() -> None:
    status = {"current": "", "status": "done", "tasks": []}
    assert _current_task_label(status) == "done"


def test_refresh_only_leaves_catalog_untouched_on_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "catalog.sqlite3"
    repo = CatalogRepository(db_path)
    repo.upsert_competition(
        "England Premier League", [SeasonInfo("England Premier League", "25/26", 76986)]
    )
    repo.close()

    args = argparse.Namespace(
        backend_url="http://localhost:8000", only="England Premier League", seasons=5
    )

    with (
        patch("fetch_cli.cli.CATALOG_DB_PATH", db_path),
        patch(
            "fetch_cli.cli.BackendClient.list_competitions",
            return_value=["England Premier League"],
        ),
        patch(
            "fetch_cli.cli.BackendClient.get_seasons",
            side_effect=requests.RequestException("boom"),
        ),
    ):
        _cmd_refresh(args)

    repo = CatalogRepository(db_path)
    try:
        result = repo.list_seasons("England Premier League")
    finally:
        repo.close()
    assert result == [SeasonInfo("England Premier League", "25/26", 76986)]
