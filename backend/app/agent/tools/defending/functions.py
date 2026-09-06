from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.defending import prompts

METRICS = [
    "clean_sheets",
    "goals_conceded",
    "penalty_conceded",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(repo, name="defending", description=prompts.DESCRIPTION, metrics=METRICS)
    ]
