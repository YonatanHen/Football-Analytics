from langchain_core.tools import BaseTool

from app.agent.tools import (
    attacking,
    composite_scores,
    defending,
    discipline,
    goalkeeping,
    playing_time,
    shots,
)

FAMILIES = [
    attacking,
    shots,
    defending,
    goalkeeping,
    discipline,
    playing_time,
    composite_scores,
]


def build_tools(repo) -> list[BaseTool]:
    return [tool for family in FAMILIES for tool in family.functions.build(repo)]
