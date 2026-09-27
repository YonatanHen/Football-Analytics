"""Non-metric tools: resolve a player by name, compare two, or report data coverage."""

import logging

from langchain_core.tools import BaseTool, StructuredTool

from app.agent.constants import MAX_ROWS, TOOL_ERROR
from app.agent.tools.base import competition_value, entries_in_scope
from app.agent.tools.identity import prompts
from app.config import settings

logger = logging.getLogger(__name__)

_NAME_MATCH_LIMIT = 5


def _competition_line(entry, position: str) -> dict:
    return {
        "competition": entry.competition,
        "appearances": entry.stats.appearances,
        "minutes": entry.stats.minutes,
        "goals": entry.stats.goals,
        "assists": entry.stats.assists,
        "fantasy_score": competition_value(entry, position, "s_final"),
    }


def _profile(player, competition: str | None = None) -> dict:
    stats, scores = player.aggregated_stats, player.aggregated_scores
    entries = entries_in_scope(player, competition)
    return {
        "name": player.name,
        "team": player.team,
        "position": player.position,
        "position_exact": player.position_exact,
        "nationality": player.nationality,
        "season": player.season,
        "competitions": [e.competition for e in entries],
        "minutes": stats.minutes,
        "appearances": stats.appearances,
        "goals": stats.goals,
        "assists": stats.assists,
        "fantasy_score": round(scores.s_final, 2),
        "sleeper_flag": scores.underpredicted_flag,
        "low_sample_size": player.low_sample_size,
        "by_competition": [_competition_line(e, player.position) for e in entries],
    }


def _lookup(
    repo, name: str, limit: int = _NAME_MATCH_LIMIT, competition: str | None = None
) -> list[dict]:
    players, _ = repo.get_players(
        season=settings.season,
        name=name,
        stats_view=competition,
        page=1,
        page_size=min(limit, MAX_ROWS),
    )
    return [_profile(p, competition) for p in players]


def build(repo) -> list[BaseTool]:
    def find_player(name: str, competition: str | None = None) -> list[dict]:
        try:
            return _lookup(repo, name, competition=competition)
        except Exception:
            logger.exception("find_player failed for %s", name)
            return [{"error": TOOL_ERROR}]

    def compare_players(first_name: str, second_name: str) -> list[dict]:
        rows: list[dict] = []
        for who in (first_name, second_name):
            try:
                rows.extend(_lookup(repo, who, limit=1))
            except Exception:
                logger.exception("compare_players failed for %s", who)
                return [{"error": TOOL_ERROR}]
        return rows

    def data_coverage() -> dict:
        try:
            competitions = repo.get_competition_list(settings.season)
            fetched = repo.list_fetched_leagues()
        except Exception:
            logger.exception("data_coverage failed")
            return {"error": TOOL_ERROR}
        return {
            "club_competitions": competitions.get("club", []),
            "national_competitions": competitions.get("national", []),
            "seasons": sorted({row["season"] for row in fetched if row.get("season")}),
        }

    return [
        StructuredTool.from_function(
            func=find_player, name="find_player", description=prompts.DESCRIPTION_FIND
        ),
        StructuredTool.from_function(
            func=compare_players,
            name="compare_players",
            description=prompts.DESCRIPTION_COMPARE,
        ),
        StructuredTool.from_function(
            func=data_coverage, name="data_coverage", description=prompts.DESCRIPTION_COVERAGE
        ),
    ]
