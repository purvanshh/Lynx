from lynx.agents.name_matcher import NameMatcherAgent
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def test_name_matcher_returns_scores() -> None:
    session = SessionState(
        session_id="s1",
        candidate_name="Rahul Sharma",
        participants=[Participant(participant_id="p1", display_name="Rahul Sharma")],
    )
    result = NameMatcherAgent().evaluate(session, "p1")
    assert result.score is not None
