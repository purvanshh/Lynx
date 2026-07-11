from datetime import datetime, timedelta, timezone

from lynx.agents.llm_reasoning import LLMReasoningAgent
from lynx.config import Settings
from lynx.models.participant import Participant
from lynx.models.session import SessionState
from lynx.models.transcript import TranscriptUtterance


def make_session() -> SessionState:
    start = datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc)
    return SessionState(
        session_id="llm-session",
        candidate_name="Rahul Sharma",
        candidate_email="rahul.sharma@example.com",
        interviewer_names=["Anita Rao"],
        scheduled_start_time=start,
        participants=[
            Participant(
                participant_id="p1",
                display_name="Rahul Sharma",
                join_timestamp=start,
                webcam_on=True,
                speaking_duration_total=180.0,
            ),
            Participant(
                participant_id="p2",
                display_name="Anita Rao",
                join_timestamp=start + timedelta(minutes=2),
                webcam_on=True,
                speaking_duration_total=60.0,
            ),
        ],
        transcript=[
            TranscriptUtterance(
                speaker_id="p1",
                utterance="Thanks for having me. I can walk through the project.",
                timestamp=start,
                duration_seconds=35.0,
            )
        ],
    )


def test_llm_reasoning_agent_returns_neutral_without_api_key() -> None:
    agent = LLMReasoningAgent(
        settings=Settings(llm_api_key=None),
        now_provider=lambda: datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
    )

    result = agent.evaluate(make_session(), "p1")

    assert result.score == 0.5
    assert "not configured" in result.reasoning.lower()


def test_llm_reasoning_agent_maps_llm_choice_to_participant_scores() -> None:
    agent = LLMReasoningAgent(
        settings=Settings(llm_api_key="test-key"),
        now_provider=lambda: datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
        transport=lambda prompt: {
            "participant_id": "p1",
            "confidence": 0.82,
            "explanation": f"Selected p1 based on prompt: {prompt[:20]}",
        },
    )
    session = make_session()

    winner = agent.evaluate(session, "p1")
    loser = agent.evaluate(session, "p2")

    assert winner.score == 0.82
    assert loser.score == 0.18
    assert "favored participant 'p1'" in loser.reasoning


def test_llm_reasoning_agent_rate_limits_follow_up_calls() -> None:
    call_times = iter(
        [
            datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 11, 9, 0, 30, tzinfo=timezone.utc),
        ]
    )
    agent = LLMReasoningAgent(
        settings=Settings(llm_api_key="test-key", llm_rate_limit_seconds=60),
        now_provider=lambda: next(call_times),
        transport=lambda prompt: {
            "participant_id": "p1",
            "confidence": 0.9,
            "explanation": f"Selected p1 from {prompt[:15]}",
        },
    )

    first_result = agent.evaluate(make_session(), "p1")
    second_result = agent.evaluate(make_session().model_copy(update={"session_id": "llm-session-2"}), "p1")

    assert first_result.score == 0.9
    assert second_result.score == 0.5
    assert "rate limit" in second_result.reasoning.lower()


def test_llm_reasoning_agent_handles_unknown_participant_response() -> None:
    agent = LLMReasoningAgent(
        settings=Settings(llm_api_key="test-key"),
        now_provider=lambda: datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
        transport=lambda prompt: {
            "participant_id": "missing",
            "confidence": 0.75,
            "explanation": prompt[:10],
        },
    )

    result = agent.evaluate(make_session(), "p1")

    assert result.score == 0.5
    assert "unknown participant" in result.reasoning.lower()
