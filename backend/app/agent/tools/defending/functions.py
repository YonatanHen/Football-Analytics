from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.defending import prompts

METRICS = [
    "clean_sheets",
    "goals_conceded",
    "penalty_conceded",
    "tackles",
    "tackles_won",
    "tackles_won_pct",
    "interceptions",
    "clearances",
    "blocks",
    "aerial_duels_won",
    "aerial_lost",
    "aerial_duels_won_pct",
    "ball_recoveries",
    "dribbled_past",
    "errors_lead_to_goal",
    "errors_lead_to_shot",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(repo, name="defending", description=prompts.DESCRIPTION, metrics=METRICS)
    ]
