import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from lynx.api.main import app
from lynx.api.dependencies import get_store
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_candidate_route_uses_orchestrator_output() -> None:
    store = get_store()
    store.clear()
    store.save(
        SessionState(
            session_id="api-session",
            candidate_name="Rahul Sharma",
            candidate_email="rahul@example.com",
            scheduled_start_time=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
            participants=[
                Participant(
                    participant_id="p1",
                    display_name="Rahul Sharma",
                    join_timestamp=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
                ),
                Participant(
                    participant_id="p2",
                    display_name="Interviewer",
                    join_timestamp=datetime(2026, 7, 11, 9, 4, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    client = TestClient(app)
    response = client.get("/sessions/api-session/candidate")

    assert response.status_code == 200
    assert response.json()["participant_id"] == "p1"
    assert response.json()["display_name"] == "Rahul Sharma"
    assert response.json()["arbitrator_explanation"]
    assert isinstance(response.json()["evidence"], list)


def test_create_session_inject_events_and_retrieve_confidence_history() -> None:
    store = get_store()
    store.clear()
    client = TestClient(app)

    create_response = client.post(
        "/sessions",
        json={
            "candidate_name": "Rahul Sharma",
            "candidate_email": "rahul.sharma@example.com",
            "interviewer_names": ["Anita Rao"],
            "scheduled_start_time": "2026-07-11T09:00:00Z",
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    join_candidate = client.post(
        f"/sessions/{session_id}/events",
        json={
            "type": "participant_join",
            "timestamp": "2026-07-11T09:00:00Z",
            "participant_id": "p1",
            "display_name": "Rahul Sharma",
            "webcam_on": True,
        },
    )
    interviewer_join = client.post(
        f"/sessions/{session_id}/events",
        json={
            "type": "participant_join",
            "timestamp": "2026-07-11T09:02:00Z",
            "participant_id": "p2",
            "display_name": "Anita Rao",
            "webcam_on": True,
        },
    )
    transcript = client.post(
        f"/sessions/{session_id}/events",
        json={
            "type": "transcript",
            "timestamp": "2026-07-11T09:02:30Z",
            "participant_id": "p1",
            "utterance": "Thanks for having me.",
            "duration_seconds": 25,
        },
    )

    assert join_candidate.status_code == 200
    assert interviewer_join.status_code == 200
    assert transcript.status_code == 200

    candidate_response = client.get(f"/sessions/{session_id}/candidate")
    history_response = client.get(f"/sessions/{session_id}/confidence-history")

    assert candidate_response.status_code == 200
    body = candidate_response.json()
    assert body["participant_id"] == "p1"
    assert body["confidence_tier"] in {"HIGH", "MEDIUM", "LOW", "UNCERTAIN"}
    assert body["evidence"]

    assert history_response.status_code == 200
    history = history_response.json()["history"]
    assert len(history) >= 3


def test_session_and_participant_endpoints_return_expected_state() -> None:
    store = get_store()
    store.clear()
    client = TestClient(app)

    create_response = client.post(
        "/sessions",
        json={
            "candidate_name": "Rahul Sharma",
            "candidate_email": "rahul.sharma@example.com",
            "interviewer_names": ["Alice Chen"],
            "scheduled_start_time": "2026-07-11T09:00:00Z",
        },
    )
    session_id = create_response.json()["session_id"]
    client.post(
        f"/sessions/{session_id}/events",
        json={
            "type": "participant_join",
            "timestamp": "2026-07-11T08:58:00Z",
            "participant_id": "p1",
            "display_name": "Rahul Sharma",
            "webcam_on": True,
        },
    )

    session_response = client.get(f"/sessions/{session_id}")
    participants_response = client.get(f"/sessions/{session_id}/participants")

    assert session_response.status_code == 200
    assert session_response.json()["session_id"] == session_id
    assert participants_response.status_code == 200
    assert participants_response.json()[0]["display_name"] == "Rahul Sharma"
    assert "candidate_probability" in participants_response.json()[0]


def test_api_returns_404_for_unknown_session_and_422_for_malformed_event() -> None:
    client = TestClient(app)

    missing_session = client.get("/sessions/does-not-exist")
    malformed_event = client.post(
        "/sessions/does-not-exist/events",
        json={"type": "participant_join", "participant_id": "p1"},
    )

    assert missing_session.status_code == 404
    assert malformed_event.status_code == 422
