import pytest

from lynx.agents.name_matcher import NameMatcherAgent
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def make_session(
    *,
    display_name: str,
    candidate_name: str = "Rahul Sharma",
    candidate_email: str | None = "rahul.sharma@example.com",
    interviewer_names: list[str] | None = None,
) -> SessionState:
    return SessionState(
        session_id="s1",
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        interviewer_names=interviewer_names or [],
        participants=[Participant(participant_id="p1", display_name=display_name)],
    )


def test_name_matcher_exact_name_match_scores_high() -> None:
    result = NameMatcherAgent().evaluate(make_session(display_name="Rahul Sharma"), "p1")

    assert result.score == 1.0


def test_name_matcher_typo_still_scores_strongly() -> None:
    result = NameMatcherAgent().evaluate(make_session(display_name="Rahul Shrama"), "p1")

    assert result.score > 0.8


def test_name_matcher_uses_email_prefix_when_name_is_shortened() -> None:
    result = NameMatcherAgent().evaluate(make_session(display_name="rahul sharma"), "p1")

    assert result.score >= 0.95


def test_name_matcher_uses_email_prefix_for_handle_style_name() -> None:
    result = NameMatcherAgent().evaluate(
        make_session(display_name="rahul.s", candidate_email="rahul.sharma@example.com"),
        "p1",
    )

    assert result.score > 0.7


def test_name_matcher_flags_interviewer_name_as_strong_negative() -> None:
    result = NameMatcherAgent().evaluate(
        make_session(display_name="Anita Rao", interviewer_names=["Anita Rao"]),
        "p1",
    )

    assert result.score == 0.0
    assert "interviewer" in result.reasoning.lower()


@pytest.mark.parametrize("display_name", ["MacBook Pro", "Guest"])
def test_name_matcher_treats_generic_device_names_as_weak_signal(display_name: str) -> None:
    result = NameMatcherAgent().evaluate(make_session(display_name=display_name), "p1")

    assert result.score == 0.1


def test_name_matcher_handles_empty_display_name_gracefully() -> None:
    session = SessionState(
        session_id="s1",
        candidate_name="Rahul Sharma",
        participants=[Participant(participant_id="p1", display_name="")],
    )
    result = NameMatcherAgent().evaluate(session, "p1")

    assert result.score == 0.0


def test_name_matcher_handles_missing_candidate_fields() -> None:
    result = NameMatcherAgent().evaluate(
        make_session(display_name="Unknown User", candidate_name="", candidate_email=None),
        "p1",
    )

    assert result.score == 0.0
