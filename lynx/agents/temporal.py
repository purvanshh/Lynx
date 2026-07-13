import math

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState

PEAK_MINUTES = 0.0
WINDOW_START_MINUTES = -5.0
WINDOW_END_MINUTES = 3.0
SIGMA_MINUTES = 2.5
DECAY_EXTENSION = 10.0


class TemporalAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "TemporalAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def _gaussian(self, delta_minutes: float) -> float:
        return math.exp(-0.5 * ((delta_minutes - PEAK_MINUTES) / SIGMA_MINUTES) ** 2)

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

        if WINDOW_START_MINUTES <= delta_minutes <= WINDOW_END_MINUTES:
            raw_score = self._gaussian(delta_minutes)
            score = 0.9 * raw_score
        elif delta_minutes < WINDOW_START_MINUTES:
            distance = WINDOW_START_MINUTES - delta_minutes
            tail = max(0.0, 1.0 - distance / DECAY_EXTENSION)
            score = 0.2 * tail
        else:
            distance = delta_minutes - WINDOW_END_MINUTES
            tail = max(0.0, 1.0 - distance / DECAY_EXTENSION)
            score = 0.2 * tail

        timing_summary = f"Joined {delta_minutes:+.1f} min from scheduled start."
        if delta_minutes < PEAK_MINUTES:
            timing_summary += " Early join consistent with candidate behavior."
        elif delta_minutes > PEAK_MINUTES:
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
