from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class SoloWindowAgent(BaseAgent):
    name = "SoloWindowAgent"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        return [
            AgentResult(
                participant_id=participant.participant_id,
                score=None,
                reasoning="Solo-window logic not implemented yet.",
            )
            for participant in session.participants
        ]
