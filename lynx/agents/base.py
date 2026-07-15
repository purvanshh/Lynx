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
    def __init__(self) -> None:
        self._weight_override: float | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def weight(self) -> float:
        raise NotImplementedError

    def get_effective_weight(self) -> float:
        override = getattr(self, "_weight_override", None)
        return override if override is not None else self.weight

    @abstractmethod
    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        raise NotImplementedError
