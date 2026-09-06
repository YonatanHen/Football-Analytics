from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.goalkeeping import prompts

METRICS = [
    "saves",
    "saves_outside_box",
    "goals_prevented",
    "high_claims",
    "pk_saved",
    "penalty_faced",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(
            repo, name="goalkeeping", description=prompts.DESCRIPTION, metrics=METRICS
        )
    ]
