from datetime import datetime, timedelta, timezone

from lynx.agents.solo_window import SoloWindowAgent
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def make_session(participants: list[Participant]) -> SessionState:
    return SessionState(session_id="solo-window-session", participants=participants)


def test_solo_window_agent_scores_three_minute_window_as_certain() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = make_session(
        [
            Participant(participant_id="p1", display_name="Candidate", join_timestamp=start),
            Participant(
                participant_id="p2",
                display_name="Interviewer",
                join_timestamp=start + timedelta(minutes=3),
            ),
        ]
    )

    result = SoloWindowAgent().evaluate(session, "p1")

    assert result is not None
    assert result.score == 1.0


def test_solo_window_agent_scores_one_minute_window_midrange() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = make_session(
        [
            Participant(participant_id="p1", display_name="Candidate", join_timestamp=start),
            Participant(
                participant_id="p2",
                display_name="Interviewer",
                join_timestamp=start + timedelta(minutes=1),
            ),
        ]
    )

    result = SoloWindowAgent().evaluate(session, "p1")

    assert result is not None
    assert result.score == 0.6


def test_solo_window_agent_scores_short_window_as_weak_positive() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = make_session(
        [
            Participant(participant_id="p1", display_name="Candidate", join_timestamp=start),
            Participant(
                participant_id="p2",
                display_name="Interviewer",
                join_timestamp=start + timedelta(seconds=10),
            ),
        ]
    )

    result = SoloWindowAgent().evaluate(session, "p1")

    assert result is not None
    assert result.score == 0.5


def test_solo_window_agent_returns_none_when_nobody_has_solo_window() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = make_session(
        [
            Participant(participant_id="p1", display_name="Candidate", join_timestamp=start),
            Participant(participant_id="p2", display_name="Interviewer", join_timestamp=start),
        ]
    )

    assert SoloWindowAgent().evaluate(session, "p1") is None
    assert SoloWindowAgent().evaluate(session, "p2") is None


def test_solo_window_agent_uses_longest_window_across_rejoins() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = make_session(
        [
            Participant(
                participant_id="p1",
                display_name="Candidate",
                join_timestamp=start,
                leave_timestamp=start + timedelta(minutes=8),
            ),
            Participant(
                participant_id="p2",
                display_name="Interviewer",
                join_timestamp=start + timedelta(seconds=20),
                leave_timestamp=start + timedelta(minutes=2),
            ),
            Participant(
                participant_id="p3",
                display_name="Observer",
                join_timestamp=start + timedelta(minutes=5),
            ),
        ]
    )

    result = SoloWindowAgent().evaluate(session, "p1")

    assert result is not None
    assert result.score == 1.0
