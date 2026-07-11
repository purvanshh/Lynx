from datetime import datetime, timedelta, timezone

from lynx.agents.behavioral import BehavioralAgent
from lynx.models.participant import Participant
from lynx.models.session import SessionState
from lynx.models.transcript import TranscriptUtterance


def build_session(
    *,
    utterances: list[TranscriptUtterance],
    speaking_duration_total: float = 0.0,
) -> SessionState:
    return SessionState(
        session_id="behavioral-session",
        participants=[
            Participant(
                participant_id="p1",
                display_name="Candidate",
                speaking_duration_total=speaking_duration_total,
            )
        ],
        transcript=utterances,
    )


def test_behavioral_agent_scores_long_burst_pattern_highly() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = build_session(
        utterances=[
            TranscriptUtterance(
                speaker_id="p1",
                utterance="Detailed answer one",
                timestamp=start,
                duration_seconds=45,
            ),
            TranscriptUtterance(
                speaker_id="p1",
                utterance="Detailed answer two",
                timestamp=start + timedelta(minutes=1),
                duration_seconds=45,
            ),
            TranscriptUtterance(
                speaker_id="p1",
                utterance="Detailed answer three",
                timestamp=start + timedelta(minutes=2),
                duration_seconds=45,
            ),
        ],
    )

    result = BehavioralAgent().evaluate(session, "p1")

    assert result.score > 0.7


def test_behavioral_agent_scores_short_uniform_turns_low() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    utterances = [
        TranscriptUtterance(
            speaker_id="p1",
            utterance=f"Short answer {index}",
            timestamp=start + timedelta(seconds=index * 7),
            duration_seconds=10,
        )
        for index in range(8)
    ]
    session = build_session(utterances=utterances)

    result = BehavioralAgent().evaluate(session, "p1")

    assert result.score < 0.4


def test_behavioral_agent_returns_neutral_without_transcript() -> None:
    result = BehavioralAgent().evaluate(build_session(utterances=[]), "p1")

    assert result.score == 0.5
    assert "neutral" in result.reasoning.lower()


def test_behavioral_agent_handles_single_utterance() -> None:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    session = build_session(
        utterances=[
            TranscriptUtterance(
                speaker_id="p1",
                utterance="Only answer",
                timestamp=start,
                duration_seconds=30,
            )
        ]
    )

    result = BehavioralAgent().evaluate(session, "p1")

    assert 0.0 <= result.score <= 1.0
