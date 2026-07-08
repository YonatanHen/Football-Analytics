from fetch_cli.cli import _current_task_label, _to_app_season, _top_n_seasons


def test_club_season_expands_to_app_format() -> None:
    assert _to_app_season("25/26") == "2025-2026"


def test_club_season_handles_century_rollover() -> None:
    assert _to_app_season("99/00") == "1999-2000"


def test_club_season_handles_nineties() -> None:
    assert _to_app_season("92/93") == "1992-1993"


def test_single_year_tournament_passes_through() -> None:
    assert _to_app_season("2026") == "2026"


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
