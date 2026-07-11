from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class TemporalAgent(BaseAgent):
    name = "TemporalAgent"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        results: list[AgentResult] = []
        for participant in session.participants:
            score = 0.5
            if session.scheduled_start_time and participant.join_timestamp:
                delta = abs((participant.join_timestamp - session.scheduled_start_time).total_seconds())
                score = max(0.0, 1.0 - min(delta, 600) / 600)
            results.append(
                AgentResult(
                    participant_id=participant.participant_id,
                    score=round(score, 3),
                    reasoning="Placeholder temporal proximity heuristic.",
                )
            )
        return results
