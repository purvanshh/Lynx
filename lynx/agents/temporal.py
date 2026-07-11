from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class TemporalAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "TemporalAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        score = 0.5
        if session.scheduled_start_time and participant.join_timestamp:
            delta = abs((participant.join_timestamp - session.scheduled_start_time).total_seconds())
            score = max(0.0, 1.0 - min(delta, 600) / 600)
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning="Placeholder temporal proximity heuristic.",
        )
