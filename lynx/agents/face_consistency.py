from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class FaceConsistencyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "FaceConsistencyAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        if not participant.webcam_on:
            return None
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=0.5,
            weight=self.weight,
            reasoning="Face consistency is a webcam-aware placeholder for now.",
        )
