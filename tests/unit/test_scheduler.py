import json
from pathlib import Path

from simulator.main import transform_event
from simulator.scheduler import EventScheduler, ScheduledEvent


def test_scheduler_loads_and_sorts_events(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(
        json.dumps(
            {
                "events": [
                    {"offset_seconds": 30, "event_type": "transcript", "payload": {"utterance": "late"}},
                    {"offset_seconds": 0, "event_type": "participant_join", "payload": {"participant_id": "p1"}},
                ]
            }
        ),
        encoding="utf-8",
    )

    scheduler = EventScheduler()
    events = scheduler.load_scenario(scenario_path)

    assert [event.offset_seconds for event in events] == [0.0, 30.0]


def test_scheduler_runs_handlers_in_event_order() -> None:
    scheduler = EventScheduler(speed_multiplier=10.0)
    scheduler.events = [
        ScheduledEvent(offset_seconds=0.0, event_type="participant_join", payload={"participant_id": "p1"}),
        ScheduledEvent(offset_seconds=0.01, event_type="transcript", payload={"participant_id": "p1"}),
    ]
    received: list[str] = []

    async def handler(event: ScheduledEvent) -> None:
        received.append(event.event_type)

    scheduler.add_handler(handler)
    import asyncio

    asyncio.run(scheduler.run())

    assert received == ["participant_join", "transcript"]


def test_transform_event_maps_scheduler_payload_to_api_event() -> None:
    event = ScheduledEvent(
        offset_seconds=15,
        event_type="participant_join",
        payload={
            "participant_id": "p1",
            "display_name": "Rahul Sharma",
            "scheduled_start_time": "2026-07-11T09:00:00+00:00",
        },
    )

    transformed = transform_event(event)

    assert transformed["type"] == "participant_join"
    assert transformed["participant_id"] == "p1"
    assert transformed["timestamp"].startswith("2026-07-11T09:00:15")
