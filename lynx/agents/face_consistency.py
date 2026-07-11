from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class FaceConsistencyAgent(BaseAgent):
    name = "FaceConsistencyAgent"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        return [
            AgentResult(
                participant_id=participant.participant_id,
                score=None if not participant.webcam_on else 0.5,
                reasoning="Face consistency is a webcam-aware placeholder for now.",
            )
            for participant in session.participants
        ]
