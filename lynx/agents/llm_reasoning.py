from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class LLMReasoningAgent(BaseAgent):
    name = "LLMReasoningAgent"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        return [
            AgentResult(
                participant_id=participant.participant_id,
                score=0.5,
                reasoning="LLM reasoning is stubbed pending prompt and API integration.",
            )
            for participant in session.participants
        ]
