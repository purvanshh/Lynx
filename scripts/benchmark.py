"""Comprehensive latency and resource benchmark for Lynx."""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import httpx
import structlog

from simulator.main import transform_event
from simulator.scheduler import ScheduledEvent, load_scenario

logger = structlog.get_logger(__name__)

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


def measure_event_ingestion(client: httpx.Client, session_id: str, events: list[dict[str, object]]) -> dict[str, float]:
    latencies: list[float] = []
    for event in events:
        start = _ns()
        resp = client.post(f"/sessions/{session_id}/events", json=event)
        elapsed = (_ns() - start) / 1e6
        latencies.append(elapsed)
        if resp.status_code != 200:
            logger.warning("event_failed", status=resp.status_code)
    return bench("event_ingestion", latencies)


def measure_candidate_lookup(client: httpx.Client, session_id: str, samples: int = 10) -> dict[str, float]:
    latencies: list[float] = []
    for _ in range(samples):
        start = _ns()
        resp = client.get(f"/sessions/{session_id}/candidate")
        elapsed = (_ns() - start) / 1e6
        latencies.append(elapsed)
    return bench("candidate_lookup", latencies)


def measure_multi_participant_scale(client: httpx.Client, base_session_id: str) -> dict[str, object]:
    sizes = [2, 5, 10, 25, 50, 100]
    results: dict[str, object] = {}

    for size in sizes:
        resp = client.post("/sessions", json={"candidate_name": "Scale Test", "candidate_email": "scale@test.com"})
        sid = resp.json()["session_id"]

        participant_ids: list[str] = []
        for i in range(size):
            pid = f"p_{i}"
            participant_ids.append(pid)
            client.post(f"/sessions/{sid}/events", json={
                "type": "participant_join",
                "timestamp": "2026-07-11T09:00:00Z",
                "participant_id": pid,
                "display_name": f"User {i}",
                "webcam_on": i < size // 2,
            })

        eval_latencies: list[float] = []
        for _ in range(5):
            start = _ns()
            client.get(f"/sessions/{sid}/candidate")
            elapsed = (_ns() - start) / 1e6
            eval_latencies.append(elapsed)

        results[str(size)] = {
            "participants": size,
            "candidate_p50_ms": statistics.median(eval_latencies),
            "candidate_p95_ms": sorted(eval_latencies)[int(len(eval_latencies) * 0.95)],
        }
        logger.info("scale_measurement", participants=size, p50_ms=results[str(size)]["candidate_p50_ms"])

    return results


def measure_llm_token_estimate(client: httpx.Client, session_id: str, events: list[dict[str, object]]) -> dict[str, float]:
    transcript_events = [e for e in events if e.get("type") == "transcript"]
    total_chars = sum(len(str(e.get("utterance", ""))) for e in transcript_events)
    estimated_tokens = total_chars / 4.0
    return {
        "total_transcript_events": len(transcript_events),
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
    }


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    scenarios = sorted(SCENARIO_DIR.glob("*.json"))
    all_event_latencies: list[float] = []
    all_candidate_latencies: list[float] = []
    scenario_results: list[dict[str, object]] = []

    logger.info("benchmark_start", scenario_count=len(scenarios))

    for scenario_path in scenarios:
        scenario_id = scenario_path.stem
        events = _load_events(scenario_path)

        resp = client.post("/sessions", json={
            "candidate_name": "Rahul Sharma",
            "candidate_email": "rahul.sharma@example.com",
            "interviewer_names": ["Alice Chen"],
            "scheduled_start_time": "2026-07-11T09:00:00Z",
        })
        session_id = resp.json()["session_id"]

        event_stats = measure_event_ingestion(client, session_id, events)
        candidate_stats = measure_candidate_lookup(client, session_id, samples=5)
        llm_stats = measure_llm_token_estimate(client, session_id, events)

        all_event_latencies.extend(
            client.post(f"/sessions/{session_id}/events", json=e).elapsed.total_seconds() * 1000
            for e in events[:1]
        )
        all_candidate_latencies.append(candidate_stats.get("p50", 0.0))

        scenario_results.append({
            "scenario": scenario_id,
            "events_count": len(events),
            "event_ingestion_ms": event_stats,
            "candidate_lookup_ms": candidate_stats,
            "llm_estimate": llm_stats,
        })

        logger.info(
            "scenario_benchmarked",
            scenario=scenario_id,
            events=len(events),
            event_p50_ms=round(event_stats.get("p50", 0), 2),
            candidate_p50_ms=round(candidate_stats.get("p50", 0), 2),
        )

    scale_results = measure_multi_participant_scale(client, "")

    overall_event = bench("event_ingestion", all_event_latencies)
    overall_candidate = bench("candidate_lookup", all_candidate_latencies)

    logger.info("benchmark_complete")
    logger.info("overall_event", p50_ms=overall_event.get("p50"), p95_ms=overall_event.get("p95"))
    logger.info("overall_candidate", p50_ms=overall_candidate.get("p50"), p95_ms=overall_candidate.get("p95"))

    report = {
        "scenarios": scenario_results,
        "overall": {
            "event_ingestion_ms": overall_event,
            "candidate_lookup_ms": overall_candidate,
        },
        "multi_participant_scale_ms": scale_results,
    }
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print("  LYNX BENCHMARK RESULTS")
    print(f"{'=' * 60}")
    print(f"  Event ingestion P50: {overall_event.get('p50', 0):>8.2f}ms")
    print(f"  Event ingestion P95: {overall_event.get('p95', 0):>8.2f}ms")
    print(f"  Candidate lookup P50: {overall_candidate.get('p50', 0):>7.2f}ms")
    print(f"  Candidate lookup P95: {overall_candidate.get('p95', 0):>7.2f}ms")
    print(f"{'=' * 60}")
    print("  Multi-participant scaling:")
    for size_key, val in scale_results.items():
        if isinstance(val, dict):
            print(f"    {val.get('participants', size_key):>3d} participants  P50: {val.get('candidate_p50_ms', 0):>8.2f}ms")
    print(f"{'=' * 60}")
    print("Report saved to output/benchmark_report.json")


if __name__ == "__main__":
    main()
