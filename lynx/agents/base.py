from abc import ABC, abstractmethod
from dataclasses import dataclass

from lynx.models.session import SessionState


@dataclass(slots=True)
class AgentResult:
    participant_id: str
    score: float | None
    reasoning: str


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def evaluate(self, session: SessionState) -> list[AgentResult]:
        raise NotImplementedError
