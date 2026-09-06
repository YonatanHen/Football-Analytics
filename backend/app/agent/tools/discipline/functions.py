from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.discipline import prompts

METRICS = [
    "yellow_cards",
    "red_cards",
    "yellow_red_cards",
    "direct_red_cards",
    "fouls_committed",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(repo, name="discipline", description=prompts.DESCRIPTION, metrics=METRICS)
    ]
