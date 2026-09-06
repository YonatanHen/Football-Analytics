from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.domain.models import AggregatedScores, PlayerDTO, Stats


class FakeToolCallingModel(BaseChatModel):
    """Replays scripted AIMessages and supports bind_tools, which the built-in fakes do not."""

    responses: list[AIMessage] = []
    index: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "FakeToolCallingModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def fake_player(name: str = "Player A", goals: int = 10) -> PlayerDTO:
    return PlayerDTO(
        sofascore_player_id="1",
        name=name,
        season="2025-2026",
        position="FW",
        position_exact="ST",
        team="Team A",
        nationality="Portugal",
        photo_url="",
        competitions=[],
        aggregated_stats=Stats(goals=goals, assists=3, minutes=900),
        aggregated_scores=AggregatedScores(
            offensive=1,
            defensive=0,
            tactical=0,
            s_final=5.5,
            underpredicted_ratio=None,
            underpredicted_flag=None,
        ),
        low_sample_size=False,
        last_updated="2026-09-02T00:00:00+00:00",
    )


def fake_repo(rows: list[PlayerDTO] | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get_players.return_value = (rows or [], len(rows or []))
    return repo
