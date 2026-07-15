"""Example plugin: EngagementAgent.

Measures participant engagement based on speaking duration ratio.
Higher engagement is consistent with candidate behavior.

Drop this file into the plugins/ directory and restart the API.
The agent automatically registers in the evidence array."""

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class EngagementAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "EngagementAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS.get(self.name, 0.08)

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        participant = next(
            p for p in session.participants if p.participant_id == participant_id
        )
        if participant.speaking_duration_total <= 0:
            return None

        total_session_duration = 0.0
        if session.current_time and session.created_at:
            total_session_duration = (session.current_time - session.created_at).total_seconds()

        if total_session_duration <= 0:
            return None

        engagement_ratio = participant.speaking_duration_total / total_session_duration
        score = min(1.0, engagement_ratio * 3.0)

        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=(
                f"Speaking engagement ratio {engagement_ratio:.2%} "
                f"({participant.speaking_duration_total:.1f}s of {total_session_duration:.1f}s). "
                "Higher engagement is consistent with candidate behavior."
            ),
        )
