from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from simulator.scheduler import EventScheduler, ScheduledEvent, load_scenario


def _iso_from_scheduled_start(scheduled_start: str, offset_seconds: float) -> str:
    scheduled_dt = datetime.fromisoformat(scheduled_start.replace("Z", "+00:00"))
    return (scheduled_dt + timedelta(seconds=offset_seconds)).isoformat()


def transform_event(event: ScheduledEvent) -> dict[str, object]:
    payload = event.payload
    scheduled_start = str(payload.get("scheduled_start_time") or "2024-01-15T10:00:00+00:00")
    timestamp = payload.get("timestamp") or _iso_from_scheduled_start(scheduled_start, event.offset_seconds)
    transformed = {
        "type": event.event_type,
        "timestamp": timestamp,
    }
    transformed.update({key: value for key, value in payload.items() if key != "scheduled_start_time"})
    if event.event_type == "name_change" and "new_name" not in transformed and "display_name" in transformed:
        transformed["new_name"] = transformed["display_name"]
    return transformed


async def _post_json(url: str, payload: dict[str, object]) -> None:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = await asyncio.to_thread(urlopen, request, 10)
    response.close()


async def run_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", help="Path to scenario JSON")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--session-id")
    args = parser.parse_args()

    scheduler = EventScheduler(speed_multiplier=args.speed)
    scenario = load_scenario(Path(args.scenario))
    scheduler.load_scenario(args.scenario)
    session_id = args.session_id or str(scenario.get("session_id", "simulated-session"))

    async def http_handler(event: ScheduledEvent) -> None:
        await _post_json(
            f"{args.api_url}/sessions/{session_id}/events",
            transform_event(event),
        )

    async def stdout_handler(event: ScheduledEvent) -> None:
        print(json.dumps({"event_type": event.event_type, "payload": event.payload}, default=str))

    scheduler.add_handler(http_handler)
    scheduler.add_handler(stdout_handler)
    await scheduler.run()


def main() -> None:
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
