from lynx.agents.face_consistency import FaceConsistencyAgent
from lynx.models.participant import Participant, WebcamFrame
from lynx.models.session import SessionState


def make_session(participant: Participant) -> SessionState:
    return SessionState(session_id="face-session", participants=[participant])


def test_face_consistency_agent_returns_none_when_webcam_off() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(Participant(participant_id="p1", display_name="Candidate", webcam_on=False)),
        "p1",
    )

    assert result is None


def test_face_consistency_agent_returns_neutral_without_frames() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(Participant(participant_id="p1", display_name="Candidate", webcam_on=True)),
        "p1",
    )

    assert result is not None
    assert result.score == 0.5


def test_face_consistency_agent_scores_perfect_single_face_sequence() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(
            Participant(
                participant_id="p1",
                display_name="Candidate",
                webcam_on=True,
                webcam_frames=[WebcamFrame(face_count=1) for _ in range(10)],
            )
        ),
        "p1",
    )

    assert result is not None
    assert result.score == 1.0


def test_face_consistency_agent_scores_no_face_sequence_as_zero() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(
            Participant(
                participant_id="p1",
                display_name="Candidate",
                webcam_on=True,
                webcam_frames=[WebcamFrame(face_count=0) for _ in range(10)],
            )
        ),
        "p1",
    )

    assert result is not None
    assert result.score == 0.0


def test_face_consistency_agent_penalizes_multiple_faces() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(
            Participant(
                participant_id="p1",
                display_name="Candidate",
                webcam_on=True,
                webcam_frames=[WebcamFrame(face_count=count) for count in [1, 1, 2, 1, 2, 1, 1, 1, 1, 1]],
            )
        ),
        "p1",
    )

    assert result is not None
    assert result.score < 1.0


def test_face_consistency_agent_returns_neutral_when_counts_cannot_be_derived() -> None:
    result = FaceConsistencyAgent().evaluate(
        make_session(
            Participant(
                participant_id="p1",
                display_name="Candidate",
                webcam_on=True,
                webcam_frames=[WebcamFrame(image_path="/tmp/non-existent-frame.png")],
            )
        ),
        "p1",
    )

    assert result is not None
    assert result.score == 0.5
