from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import httpx

from lynx.api.main import app
from simulator.main import transform_event
from simulator.scheduler import ScheduledEvent, load_scenario

DEFAULT_SCENARIOS = [
    "simulator/scenarios/happy_path.json",
    "simulator/scenarios/generic_name.json",
    "simulator/scenarios/multiple_interviewers.json",
    "simulator/scenarios/name_change.json",
    "simulator/scenarios/interviewer_candidate_name.json",
    "simulator/scenarios/no_solo_window.json",
    "simulator/scenarios/webcam_off.json",
]
DEFAULT_CHECKPOINTS_SECONDS = (30.0, 60.0, 120.0, 300.0)


@dataclass(slots=True)
class EvaluationResult:
    scenario_id: str
    correct_candidate_id: str
    identified_at_seconds: float | None
    confidence_at_identification: float
    final_accuracy: bool
    false_positive: bool
    uncertainty_flagged: bool
    final_candidate_id: str | None
    final_confidence_tier: str | None


class CandidateApiClient(Protocol):
    async def create_session(self, payload: dict[str, object]) -> str: ...

    async def inject_event(self, session_id: str, payload: dict[str, object]) -> None: ...

    async def get_candidate(self, session_id: str) -> dict[str, object]: ...

    async def close(self) -> None: ...


class HttpCandidateApiClient:
    def __init__(self, *, base_url: str | None = None, in_process: bool = False) -> None:
        self._client: httpx.AsyncClient
        if in_process:
            transport = httpx.ASGITransport(app=app)
            self._client = httpx.AsyncClient(transport=transport, base_url="http://lynx.local")
        elif base_url is not None:
            self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"))
        else:
            raise ValueError("Either base_url or in_process must be provided")

    async def create_session(self, payload: dict[str, object]) -> str:
        response = await self._client.post("/sessions", json=payload)
        response.raise_for_status()
        return str(response.json()["session_id"])

    async def inject_event(self, session_id: str, payload: dict[str, object]) -> None:
        response = await self._client.post(f"/sessions/{session_id}/events", json=payload)
        response.raise_for_status()

    async def get_candidate(self, session_id: str) -> dict[str, object]:
        response = await self._client.get(f"/sessions/{session_id}/candidate")
        response.raise_for_status()
        return dict(response.json())

    async def close(self) -> None:
        await self._client.aclose()


def _scenario_events(scenario: dict[str, object]) -> list[ScheduledEvent]:
    if "events" in scenario:
        events = [
            ScheduledEvent(
                offset_seconds=float(item["offset_seconds"]),
                event_type=str(item["event_type"]),
                payload=dict(item.get("payload", {})),
            )
            for item in scenario["events"]  # type: ignore[index]
        ]
        return sorted(events, key=lambda event: event.offset_seconds)

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

    for interviewer in interviewers:
        events.append(
            ScheduledEvent(
                offset_seconds=float(interviewer["join_offset_seconds"]),
                event_type="participant_join",
                payload={
                    "participant_id": interviewer["participant_id"],
                    "display_name": interviewer["display_name"],
                    "webcam_on": interviewer.get("webcam_on", True),
                    "scheduled_start_time": scheduled_start_time,
                },
            )
        )

    if name_change:
        events.append(
            ScheduledEvent(
                offset_seconds=float(name_change["offset_seconds"]),  # type: ignore[index]
                event_type="name_change",
                payload={
                    **dict(name_change),  # type: ignore[arg-type]
                    "scheduled_start_time": scheduled_start_time,
                },
            )
        )

    for utterance in transcript:
        events.append(
            ScheduledEvent(
                offset_seconds=float(utterance["offset_seconds"]),
                event_type="transcript",
                payload={
                    **dict(utterance),
                    "scheduled_start_time": scheduled_start_time,
                },
            )
        )

    return sorted(events, key=lambda event: event.offset_seconds)


def build_create_session_payload(scenario: dict[str, object]) -> dict[str, object]:
    interviewer_names = [
        interviewer["display_name"] for interviewer in scenario.get("interviewers", []) if interviewer.get("display_name")
    ]
    candidate = dict(scenario.get("candidate", {}))
    candidate_name = candidate.get("canonical_name") or scenario.get("candidate_name")
    if not candidate_name and candidate.get("display_name") not in {"MacBook Pro", "iPhone", "Guest", "Zoom User"}:
        candidate_name = candidate.get("display_name")

    return {
        "candidate_name": candidate_name or "Rahul Sharma",
        "candidate_email": scenario.get("candidate_email", "rahul.sharma@example.com"),
        "interviewer_names": interviewer_names,
        "scheduled_start_time": scenario.get("scheduled_start_time"),
    }


def compute_metrics(results: list[EvaluationResult]) -> dict[str, float | int]:
    total = len(results)
    identified_results = [result for result in results if result.identified_at_seconds is not None]
    correct_identification_count = len(identified_results)
    avg_time_to_id = (
        sum(result.identified_at_seconds for result in identified_results if result.identified_at_seconds is not None)
        / correct_identification_count
        if correct_identification_count
        else 0.0
    )

    return {
        "identification_accuracy": sum(1 for result in results if result.final_accuracy) / total if total else 0.0,
        "false_positive_rate": sum(1 for result in results if result.false_positive) / total if total else 0.0,
        "avg_time_to_correct_id_seconds": avg_time_to_id,
        "scenarios_passed": sum(1 for result in results if result.final_accuracy),
        "uncertainty_flags_correct": sum(1 for result in results if result.uncertainty_flagged),
    }


def assert_prd_targets(metrics: dict[str, float | int]) -> None:
    accuracy = float(metrics["identification_accuracy"])
    false_positive_rate = float(metrics["false_positive_rate"])
    if accuracy < (6 / 7):
        raise AssertionError(f"Accuracy too low: {accuracy:.2%}")
    if false_positive_rate > 0:
        raise AssertionError(f"False positive rate too high: {false_positive_rate:.2%}")


async def run_scenario(
    scenario_path: str | Path,
    client: CandidateApiClient,
    *,
    checkpoints_seconds: tuple[float, ...] = DEFAULT_CHECKPOINTS_SECONDS,
) -> EvaluationResult:
    scenario = load_scenario(Path(scenario_path))
    events = _scenario_events(scenario)
    session_id = await client.create_session(build_create_session_payload(scenario))
    scenario_id = str(scenario.get("scenario_id", Path(scenario_path).stem))
    correct_candidate_id = str(scenario["ground_truth_candidate_id"])

    identified_at_seconds: float | None = None
    confidence_at_identification = 0.0
    false_positive = False
    uncertainty_flagged = False
    final_candidate_payload: dict[str, object] | None = None

    next_event_index = 0
    all_checkpoints = sorted({*checkpoints_seconds, *(max((event.offset_seconds for event in events), default=0.0),)})

    for checkpoint in all_checkpoints:
        while next_event_index < len(events) and events[next_event_index].offset_seconds <= checkpoint:
            await client.inject_event(session_id, transform_event(events[next_event_index]))
            next_event_index += 1

        try:
            candidate_payload = await client.get_candidate(session_id)
        except httpx.HTTPStatusError:
            continue

        final_candidate_payload = candidate_payload
        predicted_candidate_id = candidate_payload.get("participant_id")
        confidence_tier = candidate_payload.get("confidence_tier")
        candidate_probability = float(candidate_payload.get("candidate_probability", 0.0))

        if confidence_tier == "UNCERTAIN":
            uncertainty_flagged = True

        if confidence_tier == "HIGH" and predicted_candidate_id != correct_candidate_id:
            false_positive = True

        if (
            identified_at_seconds is None
            and confidence_tier == "HIGH"
            and predicted_candidate_id == correct_candidate_id
        ):
            identified_at_seconds = checkpoint
            confidence_at_identification = candidate_probability

    if final_candidate_payload is None:
        raise RuntimeError(f"Scenario '{scenario_id}' did not produce any candidate output")

    final_candidate_id = final_candidate_payload.get("participant_id")
    final_confidence_tier = final_candidate_payload.get("confidence_tier")
    final_accuracy = final_candidate_id == correct_candidate_id

    return EvaluationResult(
        scenario_id=scenario_id,
        correct_candidate_id=correct_candidate_id,
        identified_at_seconds=identified_at_seconds,
        confidence_at_identification=confidence_at_identification,
        final_accuracy=final_accuracy,
        false_positive=false_positive,
        uncertainty_flagged=uncertainty_flagged,
        final_candidate_id=str(final_candidate_id) if final_candidate_id is not None else None,
        final_confidence_tier=str(final_confidence_tier) if final_confidence_tier is not None else None,
    )


async def run_evaluation(
    scenarios: list[str],
    *,
    api_url: str = "http://localhost:8000",
    in_process: bool = False,
) -> tuple[list[EvaluationResult], dict[str, float | int]]:
    client = HttpCandidateApiClient(base_url=api_url, in_process=in_process)
    try:
        results: list[EvaluationResult] = []
        for scenario_path in scenarios:
            result = await run_scenario(scenario_path, client)
            results.append(result)
            print(
                f"[{result.scenario_id}] final_candidate={result.final_candidate_id} "
                f"tier={result.final_confidence_tier} accurate={result.final_accuracy}"
            )
        metrics = compute_metrics(results)
        return results, metrics
    finally:
        await client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lynx scenario evaluation suite.")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base URL for a running Lynx API service.")
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run against the FastAPI app in-process instead of an external HTTP service.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Optional scenario path. Repeat to run a subset.",
    )
    return parser.parse_args()


async def _async_main() -> None:
    args = parse_args()
    scenarios = args.scenarios or DEFAULT_SCENARIOS
    results, metrics = await run_evaluation(scenarios, api_url=args.api_url, in_process=args.in_process)

    print("\n" + "=" * 50)
    print("EVALUATION REPORT")
    print("=" * 50)
    print(json.dumps(metrics, indent=2))
    print("\nSCENARIO DETAILS")
    for result in results:
        print(json.dumps(asdict(result), indent=2))

    assert_prd_targets(metrics)
    print("\nAll PRD targets met.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
