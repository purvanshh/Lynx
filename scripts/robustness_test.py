from __future__ import annotations

import argparse
import asyncio
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

from lynx.api.main import app
from scripts.evaluate import (
    DEFAULT_CHECKPOINTS_SECONDS,
    DEFAULT_SCENARIOS,
    EvaluationResult,
    build_create_session_payload,
)
from scripts.noise_injector import (
    apply_combined_noise,
    apply_name_corruption,
    apply_timestamp_jitter,
    apply_transcript_gaps,
    apply_webcam_dropout,
)
from simulator.scheduler import ScheduledEvent

logger = structlog.get_logger(__name__)

NOISE_LEVELS = {
    "transcript_gaps": [0.0, 0.1, 0.25, 0.50],
    "timestamp_jitter": [0.0, 1.0, 3.0, 5.0],
    "name_corruption": [0.0, 1.0],
    "webcam_dropout": [0.0, 0.30, 0.60, 0.90],
    "combined": [0.0, 0.25],
}

REPORT_DIR = Path("output")


def _load_scenario(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _scheduled_start(scenario: dict[str, Any]) -> str | None:
    raw = scenario.get("scheduled_start_time")
    return str(raw) if raw else None


def _checkpoints_for_scenario(
    scenario: dict[str, Any],
    base: tuple[float, ...] = DEFAULT_CHECKPOINTS_SECONDS,
) -> list[float]:
    events_data = scenario.get("events", [])
    max_offset = max((float(e["offset_seconds"]) for e in events_data), default=0.0) if events_data else 0.0
    return sorted({*base, max_offset})


def _scenario_events_from_list(data: dict[str, Any]) -> list[ScheduledEvent]:
    return sorted([
        ScheduledEvent(
            offset_seconds=float(item["offset_seconds"]),
            event_type=str(item["event_type"]),
            payload=dict(item.get("payload", {})),
        )
        for item in data.get("events", [])
    ], key=lambda e: e.offset_seconds)


async def run_noisy_scenario(
    client: httpx.AsyncClient,
    scenario: dict[str, Any],
    checkpoints: list[float],
) -> EvaluationResult:
    events = _scenario_events_from_list(scenario)
    session_id = await _create_session(client, scenario)
    scenario_id = str(scenario.get("scenario_id", "unknown"))
    correct_id = str(scenario.get("ground_truth_candidate_id", "p_001"))

    identified_at: float | None = None
    confidence_at_id = 0.0
    false_positive = False
    uncertainty = False
    final_payload: dict[str, Any] | None = None
    seen_cps: list[float] = []

    for cp in checkpoints:
        batch = [e for e in events if e.offset_seconds <= cp]
        events = [e for e in events if e.offset_seconds > cp]
        for event in batch:
            from simulator.main import transform_event
            payload = transform_event(event)
            await _inject_event(client, session_id, payload)
        try:
            candidate = await _get_candidate(client, session_id)
        except httpx.HTTPStatusError:
            continue
        final_payload = candidate
        seen_cps.append(cp)
        predicted_id = candidate.get("participant_id")
        tier = candidate.get("confidence_tier")
        prob = float(candidate.get("candidate_probability", 0.0))

        if tier == "UNCERTAIN":
            uncertainty = True
        if tier == "HIGH" and predicted_id != correct_id:
            false_positive = True
        if identified_at is None and tier == "HIGH" and predicted_id == correct_id:
            identified_at = cp
            confidence_at_id = prob

    if final_payload is None:
        raise RuntimeError(f"Scenario '{scenario_id}' did not produce candidate output")

    final_id = final_payload.get("participant_id")
    final_tier = final_payload.get("confidence_tier")
    final_acc = final_id == correct_id

    return EvaluationResult(
        scenario_id=scenario_id,
        correct_candidate_id=correct_id,
        identified_at_seconds=identified_at,
        confidence_at_identification=confidence_at_id,
        final_accuracy=final_acc,
        false_positive=false_positive,
        uncertainty_flagged=uncertainty,
        final_candidate_id=str(final_id) if final_id else None,
        final_confidence_tier=str(final_tier) if final_tier else None,
        checkpoints_seen=seen_cps,
    )


async def _create_session(
    client: httpx.AsyncClient, scenario: dict[str, Any]
) -> str:
    payload = build_create_session_payload(scenario)
    resp = await client.post("/sessions", json=payload)
    resp.raise_for_status()
    return str(resp.json()["session_id"])


async def _inject_event(
    client: httpx.AsyncClient, session_id: str, payload: dict[str, Any]
) -> None:
    resp = await client.post(f"/sessions/{session_id}/events", json=payload)
    resp.raise_for_status()


async def _get_candidate(
    client: httpx.AsyncClient, session_id: str
) -> dict[str, Any]:
    resp = await client.get(f"/sessions/{session_id}/candidate")
    resp.raise_for_status()
    return dict(resp.json())


@dataclass
class NoiseResult:
    noise_type: str
    noise_level: float
    scenario_id: str
    accuracy: bool
    confidence_tier: str
    time_to_id: float | None


def print_degradation_table(rows: list[NoiseResult]) -> dict[str, Any]:
    by_type: dict[str, dict[float, list[NoiseResult]]] = {}
    for r in rows:
        by_type.setdefault(r.noise_type, {}).setdefault(r.noise_level, []).append(r)

    report: dict[str, Any] = {}
    target_95_at_zero = True
    target_60_at_50 = True
    no_catastrophic = True

    print(f"\n{'=' * 72}")
    print("  NOISE DEGRADATION REPORT")
    print(f"{'=' * 72}")
    for noise_type in NOISE_LEVELS:
        levels = by_type.get(noise_type, {})
        print(f"\n  [{noise_type}]")
        print(f"  {'Level':<12} {'Acc%':<8} {'High%':<8} {'Med%':<8} {'Unc%':<8} {'AvgID(s)':<10}")
        print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
        type_report: dict[float, dict[str, float]] = {}
        for level in sorted(levels):
            group = levels[level]
            n = len(group)
            acc = sum(1 for r in group if r.accuracy) / n * 100
            high = sum(1 for r in group if r.confidence_tier == "HIGH") / n * 100
            med = sum(1 for r in group if r.confidence_tier == "MEDIUM") / n * 100
            unc = sum(1 for r in group if r.confidence_tier == "UNCERTAIN") / n * 100
            ids = [r.time_to_id for r in group if r.time_to_id is not None]
            avg_id = sum(ids) / len(ids) if ids else 0.0
            type_report[level] = {
                "accuracy_pct": round(acc, 1),
                "high_pct": round(high, 1),
                "medium_pct": round(med, 1),
                "uncertain_pct": round(unc, 1),
                "avg_time_to_id_s": round(avg_id, 1),
            }
            print(f"  {level:<12} {acc:<8.1f} {high:<8.1f} {med:<8.1f} {unc:<8.1f} {avg_id:<10.1f}")
            if level == 0.0 and acc < 95.0:
                    target_95_at_zero = False
                    logger.warning("accuracy_below_95_at_zero", noise_type=noise_type, acc=acc)
            if noise_type == "transcript_gaps" and level >= 0.50 and acc < 60.0:
                target_60_at_50 = False
                logger.warning("accuracy_below_60_at_50_pct_gaps", acc=acc)
            if acc < 30.0:
                no_catastrophic = False
                logger.warning("catastrophic_degradation", noise_type=noise_type, level=level, acc=acc)
        report[noise_type] = type_report

    print(f"\n{'─' * 72}")
    print("  Targets:")
    print(f"    @ 0% noise: accuracy >= 95%  →  {'PASS' if target_95_at_zero else 'FAIL'}")
    print(f"    @ 50% transcript gaps: accuracy >= 60%  →  {'PASS' if target_60_at_50 else 'FAIL'}")
    print(f"    No catastrophic failures (< 30% accuracy)  →  {'PASS' if no_catastrophic else 'FAIL'}")
    print(f"{'=' * 72}")
    return report


async def run_robustness_test(
    scenario_paths: list[Path],
    in_process: bool = True,
    base_url: str = "http://localhost:8000",
) -> list[NoiseResult]:
    transport = httpx.ASGITransport(app=app) if in_process else None
    base = "http://lynx.local" if in_process else base_url.rstrip("/")
    async with httpx.AsyncClient(transport=transport, base_url=base) as client:
        results: list[NoiseResult] = []

        for scenario_path in scenario_paths:
            scenario = _load_scenario(scenario_path)
            sid = str(scenario.get("scenario_id", scenario_path.stem))

            for noise_type, levels in NOISE_LEVELS.items():
                for level in levels:
                    rng_state = random.getstate()
                    random.seed(hash(f"{sid}_{noise_type}_{level}") & 0x7FFFFFFF)

                    noisy = _apply_noise(scenario, noise_type, level)

                    checkpoints = _checkpoints_for_scenario(noisy)
                    result = await run_noisy_scenario(client, noisy, checkpoints)

                    results.append(NoiseResult(
                        noise_type=noise_type,
                        noise_level=level,
                        scenario_id=sid,
                        accuracy=result.final_accuracy,
                        confidence_tier=str(result.final_confidence_tier or "UNCERTAIN"),
                        time_to_id=result.identified_at_seconds,
                    ))

                    random.setstate(rng_state)

        return results


def _apply_noise(
    scenario: dict[str, Any], noise_type: str, level: float
) -> dict[str, Any]:
    if noise_type == "transcript_gaps":
        return apply_transcript_gaps(scenario, level)
    elif noise_type == "timestamp_jitter":
        return apply_timestamp_jitter(scenario, max_jitter=level)
    elif noise_type == "name_corruption":
        return apply_name_corruption(scenario, corruption_rate=level)
    elif noise_type == "webcam_dropout":
        return apply_webcam_dropout(scenario, dropout_rate=level)
    elif noise_type == "combined":
        return apply_combined_noise(scenario, transcript_drop=level, jitter=level * 20, webcam_drop=level)
    return scenario


async def main() -> None:
    parser = argparse.ArgumentParser(description="Robustness test — noise injection")
    parser.add_argument("--scenario", action="append", dest="scenarios", help="Scenario path")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--no-in-process", action="store_true", help="Use HTTP instead of in-process")
    args = parser.parse_args()

    scenario_paths = [
        Path(s) for s in args.scenarios or DEFAULT_SCENARIOS
    ]
    logger.info("robustness_test_start", scenario_count=len(scenario_paths))

    results = await run_robustness_test(
        scenario_paths,
        in_process=not args.no_in_process,
        base_url=args.url,
    )

    report = print_degradation_table(results)

    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / "robustness_report.json"
    rows_dicts = [asdict(r) for r in results]
    report["rows"] = rows_dicts
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("report_saved", path=str(path))

    zero_levels = ["transcript_gaps", "name_corruption", "webcam_dropout"]
    for z in zero_levels:
        group = [r for r in results if r.noise_type == z and r.noise_level == 0.0]
        if group:
            acc = sum(1 for r in group if r.accuracy) / len(group) * 100
            assert acc >= 95.0, (
                f"Accuracy at 0% {z} noise is {acc:.1f}% (target ≥ 95%)"
            )

    gaps_50 = [r for r in results if r.noise_type == "transcript_gaps" and r.noise_level >= 0.50]
    if gaps_50:
        acc = sum(1 for r in gaps_50 if r.accuracy) / len(gaps_50) * 100
        assert acc >= 60.0, (
            f"Accuracy at ≥50% transcript gaps is {acc:.1f}% (target ≥ 60%)"
        )

    for nt in NOISE_LEVELS:
        for r in results:
            if r.noise_type == nt and not r.accuracy:
                overall = sum(1 for x in results if x.noise_type == nt and x.accuracy)
                total = sum(1 for x in results if x.noise_type == nt)
                if total > 0:
                    pct = overall / total * 100
                    if pct < 30.0:
                        raise AssertionError(
                            f"Catastrophic failure: {nt} accuracy = {pct:.1f}%"
                        )

    logger.info("All robustness targets met.")


if __name__ == "__main__":
    asyncio.run(main())
