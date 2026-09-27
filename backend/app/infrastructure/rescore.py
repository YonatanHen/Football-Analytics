"""Rescore every stored player, in every season, with the current formula."""

from app.domain.player_assembler import rescore_player
from app.infrastructure.mongo_repository import MongoRepository


def rescore_all_players(repo: MongoRepository, page_size: int = 500) -> list[float]:
    """Rewrite each player's competition and combined scores; returns every new s_final."""
    scores: list[float] = []
    for season in repo.list_seasons():
        # Read the full season first: upserts during paging could shift page boundaries.
        players, total = repo.get_players(season=season, page=1, page_size=page_size)
        page = 1
        while len(players) < total:
            page += 1
            more, _ = repo.get_players(season=season, page=page, page_size=page_size)
            if not more:
                break
            players.extend(more)
        for p in players:
            rescored = rescore_player(p)
            repo.upsert_player(rescored)
            scores.append(rescored.aggregated_scores.s_final)
            scores.extend(e.scores.s_final for e in rescored.competitions)
    return scores
