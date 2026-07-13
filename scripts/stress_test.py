from __future__ import annotations

import argparse
import asyncio
import json
import random
from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog

from lynx.api.main import app
from simulator.main import transform_event
from simulator.scheduler import ScheduledEvent

logger = structlog.get_logger(__name__)

SCHEDULED_START = "2026-07-11T09:00:00Z"
CANDIDATE_NAME = "Rahul Sharma"
CANDIDATE_EMAIL = "rahul.sharma@example.com"
INTERVIEWER_NAMES = ["Alice Chen"]
GENERIC_NAMES = {"android", "conference room", "guest", "ipad", "iphone",
                 "macbook pro", "meeting room", "teams user", "zoom user"}

DEFAULT_CHECKPOINTS_SECONDS = (30.0, 60.0, 120.0, 300.0)
ATTACK_TYPES = [
    "impersonation", "silent_candidate", "face_swap", "collusion",
    "name_collision", "rapid_name_change", "webcam_toggle", "generic_all",
]
VARIANTS_PER_TYPE = 125

REPORT_DIR = Path("output")


@dataclass(slots=True)
class AttackAttempt:
    scenario_id: str
    attack_type: str
    correct_candidate_id: str
    identified_at_seconds: float | None = None
    confidence_at_identification: float = 0.0
    final_accuracy: bool = False
    false_positive: bool = False
    uncertainty_flagged: bool = False
    final_candidate_id: str | None = None
    final_confidence_tier: str | None = None
    checkpoints_seen: list[float] | None = None


def _make_timestamp(scheduled_start: str, offset: float) -> str:
    from datetime import datetime, timezone, timedelta
    dt = datetime.fromisoformat(scheduled_start.replace("Z", "+00:00"))
    dt += timedelta(seconds=offset)
    return dt.isoformat()


def _scenario_events(data: dict) -> list[ScheduledEvent]:
    if "events" in data:
        return sorted([
            ScheduledEvent(
                offset_seconds=float(item["offset_seconds"]),
                event_type=str(item["event_type"]),
                payload=dict(item.get("payload", {})),
            )
            for item in data["events"]
        ], key=lambda e: e.offset_seconds)
    events: list[ScheduledEvent] = []
    start = data.get("scheduled_start_time")
    candidate = dict(data.get("candidate", {}))
    interviewers = list(data.get("interviewers", []))
    transcript = list(data.get("transcript", []))
    name_change = data.get("name_change")
    if candidate:
        events.append(ScheduledEvent(
            offset_seconds=float(candidate.get("join_offset_seconds", 0.0)),
            event_type="participant_join",
            payload={"participant_id": candidate.get("participant_id", "p_001"),
                     "display_name": candidate.get("display_name", "Candidate"),
                     "webcam_on": candidate.get("webcam_on", True),
                     "scheduled_start_time": start},
        ))
    for iv in interviewers:
        events.append(ScheduledEvent(
            offset_seconds=float(iv["join_offset_seconds"]),
            event_type="participant_join",
            payload={"participant_id": iv["participant_id"],
                     "display_name": iv["display_name"],
                     "webcam_on": iv.get("webcam_on", True),
                     "scheduled_start_time": start},
        ))
    if name_change:
        events.append(ScheduledEvent(
            offset_seconds=float(name_change["offset_seconds"]),
            event_type="name_change",
            payload={**dict(name_change), "scheduled_start_time": start},
        ))
    for utt in transcript:
        events.append(ScheduledEvent(
            offset_seconds=float(utt["offset_seconds"]),
            event_type="transcript",
            payload={**dict(utt), "scheduled_start_time": start},
        ))
    return sorted(events, key=lambda e: e.offset_seconds)


# ---------------------------------------------------------------------------
# Attack generators
# ---------------------------------------------------------------------------

def _gen_impersonation(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "scenario_id": f"impersonation_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": INTERVIEWER_NAMES,
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": "Impersonation: interviewer mimics candidate speech",
        "events": [
            {
                "offset_seconds": -2.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(120.0, 240.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_utterance(rng, "p_002", offset, long_burst=True)
              for offset in [5, 35, 65, 95, 125, 155, 185, 215, 245, 275]],
            *[_make_utterance(rng, "p_001", offset, long_burst=False)
              for offset in range(250, 280, 10)],
        ],
    }


def _gen_silent_candidate(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "scenario_id": f"silent_candidate_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": INTERVIEWER_NAMES,
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": "Candidate never speaks; interviewer does all talking",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 5.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_utterance(rng, "p_002", offset, long_burst=True)
              for offset in range(10, 290, 20)],
        ],
    }


def _gen_face_swap(seed: int) -> dict:
    rng = random.Random(seed)
    swap_at = rng.uniform(60.0, 200.0)
    after_faces = rng.choice([0, 2, 0, 2, 3])
    join_delay = rng.uniform(0.0, 5.0)
    return {
        "scenario_id": f"face_swap_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": INTERVIEWER_NAMES,
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": f"Face swap at {swap_at:.0f}s, after={after_faces}",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": join_delay,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_frame("p_001", offset, 1) for offset in range(5, int(swap_at), 15)],
            *[_make_frame("p_001", offset, after_faces) for offset in range(int(swap_at), 295, 15)],
            *[_make_frame("p_002", offset, 1) for offset in range(int(join_delay) + 10, 295, 15)],
            *[_make_utterance(rng, "p_001", offset, long_burst=True)
              for offset in [10, 40, 70, 120, 180, 240]],
            *[_make_utterance(rng, "p_002", offset, long_burst=False)
              for offset in [25, 55, 85, 150, 210, 270]],
        ],
    }


def _gen_collusion(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "scenario_id": f"collusion_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": ["Alice Chen", "Bob Smith"],
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": "Two interviewers both speak in long bursts",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 3.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(1.0, 5.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_003",
                    "display_name": "Bob Smith",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_utterance(rng, "p_002", offset, long_burst=True)
              for offset in range(10, 290, 25)],
            *[_make_utterance(rng, "p_003", offset, long_burst=True)
              for offset in range(20, 290, 25)],
            *[_make_utterance(rng, "p_001", offset, long_burst=False)
              for offset in [15, 45, 75, 120, 180, 240]],
        ],
    }


def _gen_name_collision(seed: int) -> dict:
    rng = random.Random(seed)
    fake_names = ["Alex Johnson", "Jordan Lee", "Morgan Taylor",
                  "Casey Brown", "Drew Wilson", "Riley Moore"]
    fake_name = rng.choice(fake_names)
    return {
        "scenario_id": f"name_collision_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": [CANDIDATE_NAME],
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": f"Interviewer uses candidate name; candidate uses '{fake_name}'",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": fake_name,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 3.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_utterance(rng, "p_001", offset, long_burst=True)
              for offset in range(10, 290, 25)],
            *[_make_utterance(rng, "p_002", offset, long_burst=False)
              for offset in range(20, 290, 25)],
        ],
    }


def _gen_rapid_name_change(seed: int) -> dict:
    rng = random.Random(seed)
    names = ["Alex Johnson", "Jordan Lee", "Morgan Taylor",
             "Casey Brown", "Drew Wilson", CANDIDATE_NAME]
    rng.shuffle(names)
    n_changes = rng.randint(3, 6)
    change_offsets = sorted(rng.sample(range(30, 280), n_changes))
    name_events = []
    for i, offset in enumerate(change_offsets):
        name_events.append({
            "offset_seconds": float(offset),
            "event_type": "name_change",
            "payload": {
                "participant_id": "p_001",
                "new_name": names[i % len(names)],
                "scheduled_start_time": SCHEDULED_START,
            },
        })
    return {
        "scenario_id": f"rapid_name_change_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": ["Alice Chen"],
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": f"Name changes {n_changes}x at offsets {change_offsets}",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": names[0],
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 5.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *name_events,
            *[_make_utterance(rng, "p_001", offset, long_burst=True)
              for offset in range(10, 290, 20)],
            *[_make_utterance(rng, "p_002", offset, long_burst=False)
              for offset in range(25, 290, 20)],
        ],
    }


def _gen_webcam_toggle(seed: int) -> dict:
    rng = random.Random(seed)
    toggle_count = rng.randint(3, 8)
    toggle_offsets = sorted(rng.sample(range(10, 280), toggle_count))
    frames = []
    for i, offset in enumerate(toggle_offsets):
        on = bool(i % 2 == 0)
        frames.append({
            "offset_seconds": float(offset),
            "event_type": "webcam_frame",
            "payload": {
                "participant_id": "p_001",
                "face_count": 1 if on else 0,
                "webcam_on": on,
                "scheduled_start_time": SCHEDULED_START,
            },
        })
    return {
        "scenario_id": f"webcam_toggle_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": ["Alice Chen"],
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": f"Webcam toggles {toggle_count}x at {toggle_offsets}",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": CANDIDATE_NAME,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 5.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": "Alice Chen",
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *frames,
            *[_make_utterance(rng, "p_001", offset, long_burst=True)
              for offset in range(10, 290, 25)],
            *[_make_utterance(rng, "p_002", offset, long_burst=False)
              for offset in range(20, 290, 25)],
        ],
    }


def _gen_generic_all(seed: int) -> dict:
    rng = random.Random(seed)
    g1 = rng.choice(sorted(GENERIC_NAMES))
    g2 = rng.choice(sorted(GENERIC_NAMES))
    return {
        "scenario_id": f"generic_all_{seed:04d}",
        "scheduled_start_time": SCHEDULED_START,
        "session_config": {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "interviewer_names": INTERVIEWER_NAMES,
        },
        "ground_truth_candidate_id": "p_001",
        "ground_truth_notes": f"Both participants use generic names: '{g1}', '{g2}'",
        "events": [
            {
                "offset_seconds": 0.0,
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_001",
                    "display_name": g1,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            {
                "offset_seconds": rng.uniform(0.0, 5.0),
                "event_type": "participant_join",
                "payload": {
                    "participant_id": "p_002",
                    "display_name": g2,
                    "webcam_on": True,
                    "scheduled_start_time": SCHEDULED_START,
                },
            },
            *[_make_utterance(rng, "p_001", offset, long_burst=True)
              for offset in range(10, 290, 25)],
            *[_make_utterance(rng, "p_002", offset, long_burst=False)
              for offset in range(20, 290, 25)],
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_utterance(rng: random.Random, pid: str,
                    offset: float, *, long_burst: bool) -> dict:
    duration = rng.uniform(25.0, 50.0) if long_burst else rng.uniform(3.0, 10.0)
    if long_burst:
        text = ("I believe the key challenge here is that we need to align our "
                "goals across all stakeholders. My experience has shown that "
                "when we focus on the core metrics, the results speak for "
                "themselves. Let me give you a specific example from my last "
                "project where we improved efficiency by over 40 percent.")
    else:
        text = "That's a good question. Could you elaborate a bit more on that?"
    return {
        "offset_seconds": offset,
        "event_type": "transcript",
        "payload": {
            "participant_id": pid,
            "utterance": text,
            "duration_seconds": round(duration, 1),
            "scheduled_start_time": SCHEDULED_START,
        },
    }


def _make_frame(pid: str, offset: float, face_count: int) -> dict:
    return {
        "offset_seconds": offset,
        "event_type": "webcam_frame",
        "payload": {
            "participant_id": pid,
            "face_count": face_count,
            "webcam_on": face_count > 0,
            "scheduled_start_time": SCHEDULED_START,
        },
    }


GENERATORS: dict[str, object] = {
    "impersonation": _gen_impersonation,
    "silent_candidate": _gen_silent_candidate,
    "face_swap": _gen_face_swap,
    "collusion": _gen_collusion,
    "name_collision": _gen_name_collision,
    "rapid_name_change": _gen_rapid_name_change,
    "webcam_toggle": _gen_webcam_toggle,
    "generic_all": _gen_generic_all,
}


def generate_scenarios(n_per_type: int = 125) -> list[dict]:
    scenarios: list[dict] = []
    for attack_type in ATTACK_TYPES:
        gen = GENERATORS[attack_type]
        for i in range(n_per_type):
            seed = hash(f"{attack_type}_{i}") & 0x7FFFFFFF
            scenarios.append(gen(seed))
    random.Random(42).shuffle(scenarios)
    return scenarios


# ---------------------------------------------------------------------------
# Stress test runner
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StressTestConfig:
    in_process: bool = True
    base_url: str = "http://localhost:8000"
    checkpoints: tuple[float, ...] = DEFAULT_CHECKPOINTS_SECONDS


async def run_scenario(client: httpx.AsyncClient, scenario: dict,
                       checkpoints: tuple[float, ...]) -> AttackAttempt:
    cfg = scenario["session_config"]
    session_id = await _create_session(client, cfg)
    events = _scenario_events(scenario)
    ground_truth = str(scenario.get("ground_truth_candidate_id", "p_001"))
    scenario_id = str(scenario.get("scenario_id", "unknown"))

    attempt = AttackAttempt(
        scenario_id=scenario_id,
        attack_type=scenario_id.rsplit("_", 1)[0],
        correct_candidate_id=ground_truth,
    )

    seen_checkpoints: list[float] = []
    identified_at: float | None = None

    for cp in checkpoints:
        batch = [e for e in events if e.offset_seconds <= cp]
        events = [e for e in events if e.offset_seconds > cp]
        for event in batch:
            payload = transform_event(event)
            await _inject_event(client, session_id, payload)
        candidate = await _get_candidate(client, session_id)
        seen_checkpoints.append(cp)

        prob = float(candidate.get("candidate_probability", 0.0))
        tier = str(candidate.get("confidence_tier", "UNCERTAIN"))
        identified = str(candidate.get("participant_id", "")) if candidate.get("participant_id") else None

        if tier == "UNCERTAIN":
            attempt.uncertainty_flagged = True

        if tier in ("HIGH", "MEDIUM") and identified and identified != ground_truth:
            attempt.false_positive = True

        if tier in ("HIGH", "MEDIUM") and identified == ground_truth and identified_at is None:
            identified_at = cp
            attempt.identified_at_seconds = cp
            attempt.confidence_at_identification = prob

    # Final evaluation
    final = await _get_candidate(client, session_id)
    attempt.checkpoints_seen = seen_checkpoints
    attempt.final_candidate_id = str(final.get("participant_id", "")) or None
    attempt.final_confidence_tier = str(final.get("confidence_tier", "UNCERTAIN"))
    attempt.final_accuracy = attempt.final_candidate_id == ground_truth
    if attempt.final_candidate_id and attempt.final_candidate_id != ground_truth:
        attempt.false_positive = True

    return attempt


async def _create_session(client: httpx.AsyncClient, cfg: dict) -> str:
    resp = await client.post("/sessions", json={
        "candidate_name": cfg.get("candidate_name", CANDIDATE_NAME),
        "candidate_email": cfg.get("candidate_email", CANDIDATE_EMAIL),
        "interviewer_names": cfg.get("interviewer_names", INTERVIEWER_NAMES),
        "scheduled_start_time": SCHEDULED_START,
    })
    resp.raise_for_status()
    return str(resp.json()["session_id"])


async def _inject_event(client: httpx.AsyncClient, session_id: str,
                        payload: dict) -> None:
    resp = await client.post(f"/sessions/{session_id}/events", json=payload)
    resp.raise_for_status()


async def _get_candidate(client: httpx.AsyncClient,
                         session_id: str) -> dict:
    resp = await client.get(f"/sessions/{session_id}/candidate")
    resp.raise_for_status()
    return dict(resp.json())


async def run_stress_test(config: StressTestConfig,
                          n_per_type: int = 125) -> list[AttackAttempt]:
    transport = httpx.ASGITransport(app=app) if config.in_process else None
    base = "http://lynx.local" if config.in_process else config.base_url.rstrip("/")
    async with httpx.AsyncClient(transport=transport, base_url=base) as client:
        scenarios = generate_scenarios(n_per_type=n_per_type)
        logger.info("generated_scenarios", count=len(scenarios))
        results: list[AttackAttempt] = []
        for i, scenario in enumerate(scenarios):
            result = await run_scenario(client, scenario, config.checkpoints)
            results.append(result)
            if (i + 1) % 100 == 0:
                logger.info("progress", completed=i + 1, total=len(scenarios))
        return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _attack_successful(attempt: AttackAttempt) -> bool:
    return bool(
        (not attempt.final_accuracy)
        or attempt.final_confidence_tier == "UNCERTAIN"
    )


def print_report(results: list[AttackAttempt]) -> dict:
    total = len(results)
    by_type: dict[str, list[AttackAttempt]] = {}
    for r in results:
        by_type.setdefault(r.attack_type, []).append(r)

    report: dict = {"total_variants": total, "attack_types": {}}
    total_successes = 0
    total_false_positives = 0

    for atype in ATTACK_TYPES:
        group = by_type.get(atype, [])
        n = len(group)
        successes = sum(1 for r in group if _attack_successful(r))
        fps = sum(1 for r in group if r.false_positive)
        acc = sum(1 for r in group if r.final_accuracy)
        unc = sum(1 for r in group if r.final_confidence_tier == "UNCERTAIN")
        med = sum(1 for r in group if r.final_confidence_tier in ("HIGH", "MEDIUM"))
        high = sum(1 for r in group if r.final_confidence_tier == "HIGH")
        rate = successes / n * 100 if n else 0.0

        report["attack_types"][atype] = {
            "variants": n,
            "attack_successes": successes,
            "attack_success_rate_pct": round(rate, 2),
            "false_positives": fps,
            "accuracy": round(acc / n * 100, 2) if n else 0.0,
            "uncertain_final": unc,
            "med_high_final": med,
            "high_confidence_final": high,
        }
        total_successes += successes
        total_false_positives += fps

    overall_rate = total_successes / total * 100 if total else 0.0
    overall_acc = sum(1 for r in results if r.final_accuracy) / total * 100
    report["overall"] = {
        "total_variants": total,
        "attack_successes": total_successes,
        "attack_success_rate_pct": round(overall_rate, 2),
        "false_positives": total_false_positives,
        "overall_accuracy_pct": round(overall_acc, 2),
        "passes_threshold": overall_rate < 5.0,
    }

    logger.info("stress_test_complete",
                total=total,
                success_rate=f"{overall_rate:.2f}%",
                false_positives=total_false_positives,
                passes=overall_rate < 5.0)

    print(f"\n{'=' * 70}")
    print(f"  STRESS TEST REPORT — {total} adversarial variants")
    print(f"{'=' * 70}")
    for atype in ATTACK_TYPES:
        s = report["attack_types"][atype]
        bar = "✅" if s["attack_success_rate_pct"] < 5.0 else "⚠️"
        print(f"  {bar} {atype:25s}  success={s['attack_success_rate_pct']:5.2f}%  "
              f"fp={s['false_positives']:3d}  acc={s['accuracy']:5.2f}%")
    print(f"{'─' * 70}")
    o = report["overall"]
    verdict = "✅ PASS" if o["passes_threshold"] else "❌ FAIL"
    print(f"  OVERALL  success={o['attack_success_rate_pct']:.2f}%  "
          f"fp={o['false_positives']}  acc={o['overall_accuracy_pct']:.2f}%  "
          f"threshold=<5%  {verdict}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Adversarial stress test")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="API base URL")
    parser.add_argument("--no-in-process", action="store_true",
                        help="Use HTTP client instead of in-process")
    parser.add_argument("--variants", type=int, default=125,
                        help="Variants per attack type (default: 125)")
    args = parser.parse_args()

    config = StressTestConfig(
        in_process=not args.no_in_process,
        base_url=args.url,
    )

    results = asyncio.run(run_stress_test(config, n_per_type=args.variants))
    report = print_report(results)

    REPORT_DIR.mkdir(exist_ok=True)
    path = REPORT_DIR / "stress_test_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("report_saved", path=str(path))

    assert report["overall"]["passes_threshold"], (
        f"Attack success rate {report['overall']['attack_success_rate_pct']:.2f}% "
        f"exceeds 5% threshold"
    )


if __name__ == "__main__":
    main()
