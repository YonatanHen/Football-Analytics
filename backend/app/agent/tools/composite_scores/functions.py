from langchain_core.tools import BaseTool

from app.agent.tools.base import build_metric_tool
from app.agent.tools.composite_scores import prompts

METRICS = [
    "s_final",
    "offensive",
    "defensive",
    "tactical",
]


def build(repo) -> list[BaseTool]:
    return [
        build_metric_tool(
            repo, name="composite_scores", description=prompts.DESCRIPTION, metrics=METRICS
        )
    ]
