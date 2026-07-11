from fastapi.testclient import TestClient

from lynx.api.dependencies import get_store
from lynx.api.main import app
from simulator.main import transform_event
from simulator.scheduler import EventScheduler, ScheduledEvent


def test_scheduler_events_can_drive_api_pipeline() -> None:
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
    session_id = create_response.json()["session_id"]

    scheduler = EventScheduler()
    scheduler.events = [
        ScheduledEvent(
            offset_seconds=0,
            event_type="participant_join",
            payload={
                "participant_id": "p1",
                "display_name": "Rahul Sharma",
                "webcam_on": True,
                "scheduled_start_time": "2026-07-11T09:00:00+00:00",
            },
        ),
        ScheduledEvent(
            offset_seconds=120,
            event_type="participant_join",
            payload={
                "participant_id": "p2",
                "display_name": "Anita Rao",
                "webcam_on": True,
                "scheduled_start_time": "2026-07-11T09:00:00+00:00",
            },
        ),
        ScheduledEvent(
            offset_seconds=150,
            event_type="transcript",
            payload={
                "participant_id": "p1",
                "utterance": "Thanks for having me.",
                "duration_seconds": 25,
                "scheduled_start_time": "2026-07-11T09:00:00+00:00",
            },
        ),
    ]

    for event in scheduler.events:
        response = client.post(f"/sessions/{session_id}/events", json=transform_event(event))
        assert response.status_code == 200

    candidate_response = client.get(f"/sessions/{session_id}/candidate")
    assert candidate_response.status_code == 200
    assert candidate_response.json()["participant_id"] == "p1"
