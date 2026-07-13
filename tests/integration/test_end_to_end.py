import json
from pathlib import Path

from fastapi.testclient import TestClient

from lynx.api.dependencies import get_store
from lynx.api.main import app


def test_happy_path_scenario_reaches_high_confidence_without_false_positive() -> None:
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

    fixture_path = Path("tests/fixtures/happy_path_events.json")
    events = json.loads(fixture_path.read_text(encoding="utf-8"))
    checkpoints: dict[str, dict[str, object]] = {}
    marks = [
        "2026-07-11T09:00:30Z",
        "2026-07-11T09:01:00Z",
        "2026-07-11T09:02:00Z",
        "2026-07-11T09:05:00Z",
    ]
    next_event_index = 0

    for mark in marks:
        while next_event_index < len(events) and events[next_event_index]["timestamp"] <= mark:
            response = client.post(f"/sessions/{session_id}/events", json=events[next_event_index])
            assert response.status_code == 200
            next_event_index += 1
        checkpoints[mark] = client.get(f"/sessions/{session_id}/candidate").json()

    candidate_response = client.get(f"/sessions/{session_id}/candidate")
    history_response = client.get(f"/sessions/{session_id}/confidence-history")

    assert candidate_response.status_code == 200
    body = candidate_response.json()
    assert body["participant_id"] == "p_001"
    assert body["confidence_tier"] == "HIGH"
    assert len(body["evidence"]) == 7

    history = history_response.json()["history"]
    assert len(history) >= 4
    assert checkpoints["2026-07-11T09:00:30Z"]["participant_id"] == "p_001"
    assert checkpoints["2026-07-11T09:02:00Z"]["participant_id"] == "p_001"
    assert checkpoints["2026-07-11T09:02:00Z"]["confidence_tier"] in {"HIGH", "MEDIUM"}
