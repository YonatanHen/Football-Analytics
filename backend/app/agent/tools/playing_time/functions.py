from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.playing_time import prompts

METRICS = [
    "minutes",
    "appearances",
    "matches_started",
    "rating",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(
            repo, name="playing_time", description=prompts.DESCRIPTION, metrics=METRICS
        )
    ]
