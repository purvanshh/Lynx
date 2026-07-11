from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class LLMReasoningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "LLMReasoningAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        _ = session
        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=0.5,
            weight=self.weight,
            reasoning="LLM reasoning is stubbed pending prompt and API integration.",
        )
