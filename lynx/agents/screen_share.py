from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class ScreenShareAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ScreenShareAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        screen_share_count = len(participant.screen_share_events)
        if screen_share_count == 0:
            return None

        score = min(1.0, 0.5 + 0.15 * screen_share_count)
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=(
                f"Screen shared {screen_share_count} time{'s' if screen_share_count > 1 else ''}. "
                "Sharing screen is consistent with candidate behavior."
            ),
        )
