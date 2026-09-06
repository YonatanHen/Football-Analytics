from langchain_core.tools import BaseTool

from app.agent.tools.attacking import prompts
from app.agent.tools.base import build_metric_tool

METRICS = [
    "goals",
    "assists",
    "xg",
    "xa",
    "key_passes",
    "big_chances_created",
    "pk_won",
    "pk_scored",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(repo, name="attacking", description=prompts.DESCRIPTION, metrics=METRICS)
    ]
