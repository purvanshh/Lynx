from __future__ import annotations

import asyncio
import inspect
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ScheduledEvent:
    offset_seconds: float
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventScheduler:
    def __init__(self, speed_multiplier: float = 1.0) -> None:
        self.speed = speed_multiplier
        self.events: list[ScheduledEvent] = []
        self.handlers: list[Any] = []

    def load_scenario(self, scenario_path: str | Path) -> list[ScheduledEvent]:
        data = load_scenario(Path(scenario_path))
        self.events = self._scenario_to_events(data)
        return self.events

    def add_handler(self, handler: Any) -> None:
        self.handlers.append(handler)

    async def run(self) -> None:
        start_time = time.monotonic()
        for event in self.events:
            target_real_time = start_time + (event.offset_seconds / self.speed)
            wait_seconds = target_real_time - time.monotonic()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            for handler in self.handlers:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result

    def _scenario_to_events(self, data: dict[str, Any]) -> list[ScheduledEvent]:
        if data.get("events"):
            events = [
                ScheduledEvent(
                    offset_seconds=float(item["offset_seconds"]),
                    event_type=item["event_type"],
                    payload=item.get("payload", {}),
                )
                for item in data["events"]
            ]
            return sorted(events, key=lambda event: event.offset_seconds)

        scheduled_start_time = data.get("scheduled_start_time")
        candidate = data.get("candidate", {})
        interviewers = data.get("interviewers", [])
        transcript = data.get("transcript", [])
        events: list[ScheduledEvent] = []

        if candidate:
            events.append(
                ScheduledEvent(
                    offset_seconds=float(candidate.get("join_offset_seconds", 0.0)),
                    event_type="participant_join",
                    payload={
                        "participant_id": candidate.get("participant_id", "candidate"),
                        "display_name": candidate.get("display_name", "Candidate"),
                        "webcam_on": candidate.get("webcam_on", True),
                        "scheduled_start_time": scheduled_start_time,
                    },
                )
            )

        for interviewer in interviewers:
            events.append(
                ScheduledEvent(
                    offset_seconds=float(interviewer.get("join_offset_seconds", 0.0)),
                    event_type="participant_join",
                    payload={
                        "participant_id": interviewer["participant_id"],
                        "display_name": interviewer["display_name"],
                        "webcam_on": interviewer.get("webcam_on", True),
                        "scheduled_start_time": scheduled_start_time,
                    },
                )
            )

        name_change = data.get("name_change")
        if name_change:
            events.append(
                ScheduledEvent(
                    offset_seconds=float(name_change["offset_seconds"]),
                    event_type="name_change",
                    payload=name_change,
                )
            )

        for utterance in transcript:
            events.append(
                ScheduledEvent(
                    offset_seconds=float(utterance["offset_seconds"]),
                    event_type="transcript",
                    payload=utterance,
                )
            )

        return sorted(events, key=lambda event: event.offset_seconds)


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
