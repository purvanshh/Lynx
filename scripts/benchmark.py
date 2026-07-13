from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import httpx

from simulator.main import transform_event
from simulator.scheduler import ScheduledEvent, load_scenario

BASE_URL = os.environ.get("LYNX_BASE_URL", "http://localhost:8000")
SCENARIO_DIR = Path("simulator/scenarios")


def _scenario_scheduled(scenario: dict[str, object]) -> list[ScheduledEvent]:
    if "events" in scenario:
        events = [
            ScheduledEvent(
                offset_seconds=float(item["offset_seconds"]),
                event_type=str(item["event_type"]),
                payload=dict(item.get("payload", {})),
            )
            for item in scenario["events"]
        ]
        return sorted(events, key=lambda e: e.offset_seconds)

    events: list[ScheduledEvent] = []
    scheduled_start_time = scenario.get("scheduled_start_time")
    candidate = dict(scenario.get("candidate", {}))
    interviewers = list(scenario.get("interviewers", []))
    transcript = list(scenario.get("transcript", []))
    name_change = scenario.get("name_change")

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

    for iv in interviewers:
        events.append(
            ScheduledEvent(
                offset_seconds=float(iv["join_offset_seconds"]),
                event_type="participant_join",
                payload={
                    "participant_id": iv["participant_id"],
                    "display_name": iv["display_name"],
                    "webcam_on": iv.get("webcam_on", True),
                    "scheduled_start_time": scheduled_start_time,
                },
            )
        )

    if name_change:
        events.append(
            ScheduledEvent(
                offset_seconds=float(name_change["offset_seconds"]),
                event_type="name_change",
                payload={**dict(name_change), "scheduled_start_time": scheduled_start_time},
            )
        )

    for utt in transcript:
        events.append(
            ScheduledEvent(
                offset_seconds=float(utt["offset_seconds"]),
                event_type="transcript",
                payload={**dict(utt), "scheduled_start_time": scheduled_start_time},
            )
        )

    return sorted(events, key=lambda e: e.offset_seconds)


def _load_events(scenario_path: Path) -> list[dict[str, object]]:
    scenario = load_scenario(scenario_path)
    scheduled = _scenario_scheduled(scenario)
    return [transform_event(event) for event in scheduled]


def _ns() -> float:
    return time.perf_counter_ns()


def bench(label: str, results: list[float]) -> dict[str, float]:
    if not results:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
    results.sort()
    return {
        "count": len(results),
        "mean": statistics.mean(results),
        "p50": results[len(results) // 2],
        "p95": results[int(len(results) * 0.95)],
        "p99": results[int(len(results) * 0.99)],
    }


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    scenarios = sorted(SCENARIO_DIR.glob("*.json"))
    total_event_latencies: list[float] = []
    total_candidate_latencies: list[float] = []
    scenario_results: list[dict[str, object]] = []

    for scenario_path in scenarios:
        scenario_id = scenario_path.stem
        events = _load_events(scenario_path)

        session_resp = client.post("/sessions", json={
            "candidate_name": "Rahul Sharma",
            "candidate_email": "rahul.sharma@example.com",
            "interviewer_names": ["Alice Chen"],
            "scheduled_start_time": "2026-07-11T09:00:00Z",
        })
        session_id = session_resp.json()["session_id"]

        event_latencies: list[float] = []
        for event in events:
            start = _ns()
            resp = client.post(f"/sessions/{session_id}/events", json=event)
            elapsed = (_ns() - start) / 1e6
            event_latencies.append(elapsed)
            total_event_latencies.append(elapsed)
            if resp.status_code != 200:
                print(f"  WARN: event returned {resp.status_code} in scenario {scenario_id}")

        candidate_latencies: list[float] = []
        for _ in range(5):
            start = _ns()
            resp = client.get(f"/sessions/{session_id}/candidate")
            elapsed = (_ns() - start) / 1e6
            candidate_latencies.append(elapsed)
            total_candidate_latencies.append(elapsed)

        event_stats = bench("event", event_latencies)
        candidate_stats = bench("candidate", candidate_latencies)

        scenario_results.append({
            "scenario": scenario_id,
            "events_count": len(events),
            "event_latency_ms": event_stats,
            "candidate_latency_ms": candidate_stats,
        })

        print(f"{scenario_id:35s}  events={len(events):3d}  "
              f"event_p50={event_stats['p50']:7.2f}ms  candidate_p50={candidate_stats['p50']:7.2f}ms")

    overall_event = bench("event", total_event_latencies)
    overall_candidate = bench("candidate", total_candidate_latencies)

    print()
    print(f"{'OVERALL':35s}  "
          f"event_p50={overall_event['p50']:7.2f}ms  candidate_p50={overall_candidate['p50']:7.2f}ms")
    print(f"{'':35s}  "
          f"event_p95={overall_event['p95']:7.2f}ms  candidate_p95={overall_candidate['p95']:7.2f}ms")
    print(f"{'':35s}  "
          f"event_p99={overall_event['p99']:7.2f}ms  candidate_p99={overall_candidate['p99']:7.2f}ms")
    print(f"{'':35s}  "
          f"event_mean={overall_event['mean']:7.2f}ms  candidate_mean={overall_candidate['mean']:7.2f}ms")

    report = {
        "scenarios": scenario_results,
        "overall": {
            "event": overall_event,
            "candidate": overall_candidate,
        },
    }
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "benchmark_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("\nReport saved to output/benchmark_report.json")


if __name__ == "__main__":
    main()
