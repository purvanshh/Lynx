from datetime import datetime, timedelta, timezone

import pytest

from lynx.agents.temporal import TemporalAgent
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def make_session(delta_minutes: float) -> SessionState:
    scheduled = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    joined = scheduled + timedelta(minutes=delta_minutes)
    return SessionState(
        session_id="temporal-session",
        scheduled_start_time=scheduled,
        participants=[
            Participant(participant_id="p1", display_name="Candidate", join_timestamp=joined),
        ],
    )


@pytest.mark.parametrize(
    ("delta_minutes", "expected_score"),
    [
        (0.0, 1.0),
        (-2.0, 0.726),
        (-5.0, 0.135),
        (3.0, 0.487),
        (6.0, 0.0),
        (-10.0, 0.0),
    ],
)
def test_temporal_agent_gaussian_window_scoring(delta_minutes: float, expected_score: float) -> None:
    result = TemporalAgent().evaluate(make_session(delta_minutes), "p1")

    assert result.score == pytest.approx(expected_score, abs=0.001)


def test_temporal_agent_returns_neutral_when_timestamps_missing() -> None:
    session = SessionState(
        session_id="temporal-missing",
        participants=[Participant(participant_id="p1", display_name="Candidate")],
    )

    result = TemporalAgent().evaluate(session, "p1")

    assert result.score == 0.5
