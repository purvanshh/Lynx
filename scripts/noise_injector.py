from __future__ import annotations

import copy
import random
from typing import Any

_EMOJIS = ["🔥", "🎉", "❤️", "😂", "😊", "💪", "🚀", "👀", "✨", "🌟"]
_TYPOS = {
    "Rahul": "Rahul", "Sharma": "Sharma", "Alice": "Alcie", "Chen": "Chen",
    "Bob": "Bobb", "Smith": "Smiht", "Candidate": "Candidte",
    "Alex": "Alx", "Jordan": "Jordn", "Morgan": "Morgn",
    "Casey": "Casey", "Drew": "Drew", "Riley": "Riley",
    "MacBook Pro": "MacBook", "iPhone": "IPhone",
    "Guest": "Gues", "Zoom User": "Zoom",
}


def _display_name_key(name: str) -> str:
    lower = name.strip().lower()
    for key in _TYPOS:
        if key.lower() == lower:
            return key
    return name


def deep_copy_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(scenario)


def apply_transcript_gaps(scenario: dict[str, Any], drop_rate: float) -> dict[str, Any]:
    s = deep_copy_scenario(scenario)
    events: list[dict[str, Any]] = s.get("events", [])
    s["events"] = [
        e for e in events
        if not (e.get("event_type") == "transcript" and random.random() < drop_rate)
    ]
    return s


def apply_timestamp_jitter(
    scenario: dict[str, Any], max_jitter: float = 5.0
) -> dict[str, Any]:
    s = deep_copy_scenario(scenario)
    for event in s.get("events", []):
        jitter = random.uniform(-max_jitter, max_jitter)
        event["offset_seconds"] = round(max(0.0, event["offset_seconds"] + jitter), 1)
    return s


def _corrupt_name(name: str) -> str:
    r = random.random()
    if r < 0.33:
        return name + " " + random.choice(_EMOJIS)
    elif r < 0.66:
        key = _display_name_key(name)
        base = _TYPOS.get(key, name)
        if random.random() < 0.5 and len(base) > 2:
            idx = random.randint(0, len(base) - 1)
            base = base[:idx] + random.choice("abcdefghijklmnopqrstuvwxyz") + base[idx + 1:]
        return base
    else:
        return "".join(chr(random.randint(0x0430, 0x044F)) for _ in range(len(name)))


def apply_name_corruption(scenario: dict[str, Any], corruption_rate: float = 1.0) -> dict[str, Any]:
    s = deep_copy_scenario(scenario)
    for event in s.get("events", []):
        if event.get("event_type") == "participant_join":
            payload = event.get("payload", {})
            if random.random() < corruption_rate:
                payload["display_name"] = _corrupt_name(str(payload.get("display_name", "")))
    return s


def apply_webcam_dropout(
    scenario: dict[str, Any], dropout_rate: float
) -> dict[str, Any]:
    s = deep_copy_scenario(scenario)
    for event in s.get("events", []):
        if event.get("event_type") == "webcam_frame" and random.random() < dropout_rate:
                event["payload"]["face_count"] = 0
                event["payload"]["webcam_on"] = False
    return s


def apply_combined_noise(
    scenario: dict[str, Any],
    transcript_drop: float = 0.25,
    jitter: float = 5.0,
    name_corrupt: float = 1.0,
    webcam_drop: float = 0.3,
) -> dict[str, Any]:
    s = deep_copy_scenario(scenario)
    s = apply_transcript_gaps(s, transcript_drop)
    s = apply_timestamp_jitter(s, max_jitter=jitter)
    s = apply_name_corruption(s, corruption_rate=name_corrupt)
    s = apply_webcam_dropout(s, dropout_rate=webcam_drop)
    return s
