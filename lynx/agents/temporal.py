import math

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState

WINDOW_START_MINUTES = -5.0
WINDOW_END_MINUTES = 3.0
SIGMA_MINUTES = 2.5


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
        if session.scheduled_start_time is None or participant.join_timestamp is None:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.5,
                weight=self.weight,
                reasoning="Scheduled start time or join timestamp is missing. Temporal signal is neutral.",
            )

        delta_minutes = (
            participant.join_timestamp - session.scheduled_start_time
        ).total_seconds() / 60.0
        if delta_minutes < WINDOW_START_MINUTES or delta_minutes > WINDOW_END_MINUTES:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.0,
                weight=self.weight,
                reasoning=(
                    f"Joined {delta_minutes:+.1f} min from scheduled start. Outside candidate arrival window."
                ),
            )

        raw_score = math.exp(-0.5 * (delta_minutes / SIGMA_MINUTES) ** 2)
        score = 0.9 * raw_score
        timing_summary = f"Joined {delta_minutes:+.1f} min from scheduled start."
        if delta_minutes < 0:
            timing_summary += " Early join consistent with candidate behavior."
        elif delta_minutes > 0:
            timing_summary += " Slightly late but still within expected candidate window."
        else:
            timing_summary += " Exact on-time join."
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=timing_summary,
        )
