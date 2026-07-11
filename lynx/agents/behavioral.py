from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class BehavioralAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "BehavioralAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=0.5,
            weight=self.weight,
            reasoning="Placeholder behavioral scoring until speaking-feature extraction is implemented.",
        )
