from datetime import datetime, timezone

from fastapi.testclient import TestClient

from lynx.api.main import app
from lynx.api.dependencies import get_store
from lynx.models.participant import Participant
from lynx.models.session import SessionState


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_candidate_route_uses_orchestrator_output() -> None:
    store = get_store()
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
