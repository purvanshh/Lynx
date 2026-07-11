from abc import ABC, abstractmethod
from dataclasses import dataclass

from lynx.models.session import SessionState


@dataclass(slots=True)
class AgentResult:
    agent: str
    participant_id: str
    score: float | None
    weight: float
    reasoning: str


class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def weight(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        raise NotImplementedError
