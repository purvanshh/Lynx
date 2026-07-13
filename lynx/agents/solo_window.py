from datetime import datetime

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class SoloWindowAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "SoloWindowAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        solo_durations = self._solo_durations(session)
        if not solo_durations:
            return None

        max_duration_seconds = solo_durations.get(participant_id)
        if max_duration_seconds is None:
            return None

        if max_duration_seconds < 30:
            score = 0.5
        elif max_duration_seconds < 180:
            score = 0.5 + (0.5 * (max_duration_seconds - 30) / 150)
        else:
            score = 1.0

        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=(
                f"Longest solo window lasted {max_duration_seconds:.0f}s before others joined or after they left."
            ),
        )

    def _solo_durations(self, session: SessionState) -> dict[str, float]:
        participant_windows: list[tuple[datetime, datetime | None, str]] = []
        for participant in session.participants:
            if participant.join_timestamp is None:
                continue
            participant_windows.append(
                (participant.join_timestamp, participant.leave_timestamp, participant.participant_id)
            )

        if not participant_windows:
            return {}

        boundaries = {
            timestamp
            for join_timestamp, leave_timestamp, _ in participant_windows
            for timestamp in (join_timestamp, leave_timestamp)
            if timestamp is not None
        }
        ordered_boundaries = sorted(boundaries)
        if len(ordered_boundaries) < 2:
            return {}

        durations: dict[str, float] = {}
        for start, end in zip(ordered_boundaries, ordered_boundaries[1:], strict=False):
            if end <= start:
                continue

            present = [
                participant_id
                for join_timestamp, leave_timestamp, participant_id in participant_windows
                if join_timestamp <= start and (leave_timestamp is None or start < leave_timestamp)
            ]
            if len(present) != 1:
                continue

            participant_id = present[0]
            duration = (end - start).total_seconds()
            durations[participant_id] = max(durations.get(participant_id, 0.0), duration)

        return durations
