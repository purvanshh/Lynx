from collections import Counter

from fastapi import APIRouter, Depends

from lynx.api.dependencies import get_store
from lynx.store.memory_store import InMemorySessionStore

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def get_analytics_summary(
    store: InMemorySessionStore = Depends(get_store),
) -> dict[str, object]:
    session_ids = store.get_all_session_ids()
    total_sessions = len(session_ids)
    total_participants = 0
    total_events = 0
    tier_counts: dict[str, int] = Counter()
    agent_activations: dict[str, int] = Counter()
    confidence_values: list[float] = []

    for sid in session_ids:
        session = store.get(sid)
        if session is None:
            continue

        total_participants += len(session.participants)
        total_events += len(session.event_log)

        if session.confidence_history:
            latest = session.confidence_history[-1]
            if latest.probabilities:
                top_prob = max(latest.probabilities.values())
                confidence_values.append(top_prob)

                if top_prob >= 0.85:
                    tier_counts["HIGH"] += 1
                elif top_prob >= 0.65:
                    tier_counts["MEDIUM"] += 1
                elif top_prob >= 0.45:
                    tier_counts["LOW"] += 1
                else:
                    tier_counts["UNCERTAIN"] += 1

        for entry in session.event_log:
            if entry.type == "transcript":
                agent_activations["NameMatcher"] += 1
                agent_activations["TemporalAgent"] += 1
                agent_activations["BehavioralAgent"] += 1

    confidence_histogram = _build_histogram(confidence_values, bins=10)

    return {
        "total_sessions": total_sessions,
        "total_participants": total_participants,
        "total_events": total_events,
        "tier_distribution": dict(tier_counts),
        "agent_activation_count": dict(agent_activations),
        "confidence_histogram": confidence_histogram,
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
    }


def _build_histogram(values: list[float], bins: int = 10) -> list[dict[str, float]]:
    if not values:
        return []
    step = 1.0 / bins
    result: list[dict[str, float]] = []
    for i in range(bins):
        lower = round(i * step, 2)
        upper = round((i + 1) * step, 2)
        count = sum(1 for v in values if lower <= v < upper) or 0
        result.append({"bucket_lower": lower, "bucket_upper": upper, "count": count})
    return result
