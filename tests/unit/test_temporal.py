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
        (0.0, 0.9),
        (-2.0, 0.654),
        (-5.0, 0.122),
        (3.0, 0.438),
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


@pytest.mark.parametrize(
    ("delta_minutes", "expected_score"),
    [
        (-5.0, 0.122),
        (3.0, 0.438),
    ],
)
def test_temporal_agent_includes_window_boundaries(delta_minutes: float, expected_score: float) -> None:
    result = TemporalAgent().evaluate(make_session(delta_minutes), "p1")

    assert result.score == pytest.approx(expected_score, abs=0.001)
