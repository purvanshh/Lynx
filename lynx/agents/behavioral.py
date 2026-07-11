from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class BehavioralAgent(BaseAgent):
    name = "BehavioralAgent"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        return [
            AgentResult(
                participant_id=participant.participant_id,
                score=0.5,
                reasoning="Placeholder behavioral scoring until speaking-feature extraction is implemented.",
            )
            for participant in session.participants
        ]
