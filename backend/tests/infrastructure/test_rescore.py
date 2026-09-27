from datetime import UTC, datetime

from app.domain.models import AggregatedScores, CompetitionEntry, PlayerDTO, Score, Stats
from app.infrastructure.mongo_repository import MongoRepository
from app.infrastructure.rescore import rescore_all_players

_STALE = Score(offensive=0.0, defensive=0.0, tactical=0.0, s_final=12.09)


def _stored(player_id: str, season: str) -> PlayerDTO:
    stats = Stats(
        goals=50, assists=7, xg=36.19, xa=6.75, minutes=3421, appearances=44, matches_started=37
    )
    return PlayerDTO(
        sofascore_player_id=player_id,
        name=f"Player {player_id}",
        season=season,
        position="FW",
        position_exact="ST",
        team="Team A",
        nationality="England",
        photo_url="",
        competitions=[CompetitionEntry("Germany Bundesliga", stats, _STALE)],
        aggregated_stats=stats,
        aggregated_scores=AggregatedScores(0.0, 0.0, 0.0, 12.09, None, None),
        low_sample_size=False,
        last_updated=datetime.now(UTC).isoformat(),
    )


def _all_scores(repo: MongoRepository, season: str) -> list[float]:
    players, _ = repo.get_players(season=season, page=1, page_size=100)
    return [p.aggregated_scores.s_final for p in players] + [
        c.scores.s_final for p in players for c in p.competitions
    ]


def test_every_stored_season_is_rescored(repo: MongoRepository) -> None:
    repo.upsert_player(_stored("1", "2025-2026"))
    repo.upsert_player(_stored("2", "2024-2025"))
    rescore_all_players(repo)
    for season in ("2025-2026", "2024-2025"):
        assert _all_scores(repo, season) == [10.0, 10.0]


def test_players_beyond_the_first_page_are_rescored(repo: MongoRepository) -> None:
    for i in range(7):
        repo.upsert_player(_stored(str(i), "2025-2026"))
    scores = rescore_all_players(repo, page_size=3)
    assert len(scores) == 14  # 7 combined + 7 competition scores
    assert all(s == 10.0 for s in _all_scores(repo, "2025-2026"))


def test_an_empty_database_returns_no_scores(repo: MongoRepository) -> None:
    assert rescore_all_players(repo) == []
