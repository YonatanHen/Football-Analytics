from pathlib import Path

import pytest

from fetch_cli.catalog_repository import CatalogRepository, SeasonInfo


@pytest.fixture
def repo(tmp_path: Path) -> CatalogRepository:
    return CatalogRepository(tmp_path / "catalog.sqlite3")


def _sample() -> tuple[list[str], list[SeasonInfo]]:
    competitions = ["England Premier League", "FIFA World Cup"]
    seasons = [
        SeasonInfo("England Premier League", "24/25", 61627),
        SeasonInfo("England Premier League", "25/26", 76986),
        SeasonInfo("FIFA World Cup", "2026", 12345),
    ]
    return competitions, seasons


def test_replace_all_and_list_competitions(repo: CatalogRepository) -> None:
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)

    assert repo.list_competitions() == ["England Premier League", "FIFA World Cup"]


def test_list_seasons_sorted_newest_first(repo: CatalogRepository) -> None:
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)

    result = repo.list_seasons("England Premier League")
    assert [s.season_label for s in result] == ["25/26", "24/25"]


def test_list_seasons_unknown_competition_returns_empty(repo: CatalogRepository) -> None:
    assert repo.list_seasons("Nonexistent League") == []


def test_replace_all_clears_previous_snapshot(repo: CatalogRepository) -> None:
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)

    repo.replace_all(["Spain La Liga"], [])

    assert repo.list_competitions() == ["Spain La Liga"]
    assert repo.list_seasons("England Premier League") == []


def test_last_refreshed_at_set_on_replace(repo: CatalogRepository) -> None:
    assert repo.last_refreshed_at() is None
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)
    assert repo.last_refreshed_at() is not None


def test_upsert_competition_leaves_others_untouched(repo: CatalogRepository) -> None:
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)

    repo.upsert_competition(
        "England Premier League", [SeasonInfo("England Premier League", "26/27", 99999)]
    )

    assert repo.list_competitions() == ["England Premier League", "FIFA World Cup"]
    assert [s.season_label for s in repo.list_seasons("England Premier League")] == ["26/27"]
    assert repo.list_seasons("FIFA World Cup") == [SeasonInfo("FIFA World Cup", "2026", 12345)]


def test_upsert_competition_new_name(repo: CatalogRepository) -> None:
    repo.upsert_competition("Spain La Liga", [SeasonInfo("Spain La Liga", "25/26", 1)])

    assert repo.list_competitions() == ["Spain La Liga"]


def test_is_empty(repo: CatalogRepository) -> None:
    assert repo.is_empty() is True
    competitions, seasons = _sample()
    repo.replace_all(competitions, seasons)
    assert repo.is_empty() is False
