from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.shots import prompts

METRICS = [
    "total_shots",
    "shots_on_target",
    "shots_off_target",
    "scoring_frequency",
    "headed_goals",
    "left_foot_goals",
    "right_foot_goals",
    "pk_taken",
    "penalty_miss",
]


def build(repo) -> list[BaseTool]:
    return [build_metric_tool(repo, name="shots", description=prompts.DESCRIPTION, metrics=METRICS)]
