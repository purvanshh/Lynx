from statistics import mean

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class BehavioralAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "BehavioralAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        utterances = [utterance for utterance in session.transcript if utterance.speaker_id == participant_id]
        if not utterances:
            return AgentResult(
                agent=self.name,
                participant_id=participant_id,
                score=0.5,
                weight=self.weight,
                reasoning="No transcript data available. Behavioral signal is neutral.",
            )

        durations = [utterance.duration_seconds or 0.0 for utterance in utterances]
        avg_duration = mean(durations)
        turn_count = len(utterances)

        transcript_timestamps = [utterance.timestamp for utterance in session.transcript]
        if transcript_timestamps:
            session_duration_seconds = max(
                60.0,
                (max(transcript_timestamps) - min(transcript_timestamps)).total_seconds(),
            )
        else:
            session_duration_seconds = 60.0

        turn_frequency = turn_count / (session_duration_seconds / 60.0)
        speaking_seconds = sum(durations)
        if speaking_seconds == 0.0:
            participant = next(
                participant for participant in session.participants if participant.participant_id == participant_id
            )
            speaking_seconds = participant.speaking_duration_total
        silence_ratio = max(0.0, min(1.0, 1.0 - (speaking_seconds / session_duration_seconds)))

        duration_score = min(1.0, avg_duration / 45.0)
        frequency_score = max(0.0, 1.0 - (turn_frequency / 8.0))
        silence_score = silence_ratio
        score = (0.5 * duration_score) + (0.3 * frequency_score) + (0.2 * silence_score)

        verdict = (
            "Burst-response pattern is consistent with candidate behavior."
            if score > 0.6
            else "Short, frequent turns look more like interviewer behavior."
        )
        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=(
                f"Avg utterance {avg_duration:.1f}s, turn frequency {turn_frequency:.2f}/min, "
                f"silence ratio {silence_ratio:.2f}. {verdict}"
            ),
        )
