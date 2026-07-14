from collections import defaultdict
from dataclasses import dataclass, field

from lynx.models.evidence import ArbitratorOutput
from lynx.models.participant import Participant
from lynx.models.session import SessionState

_recent: dict[str, list["AnomalyAlert"]] = defaultdict(list)
_MAX_PER_SESSION = 20


@dataclass
class AnomalyAlert:
    rule: str
    severity: str
    message: str
    session_id: str
    details: dict[str, object] = field(default_factory=dict)


def check_anomalies(
    session: SessionState, output: ArbitratorOutput, prev_output: ArbitratorOutput | None
) -> list[AnomalyAlert]:
    alerts: list[AnomalyAlert] = []

    sid = session.session_id
    top_id = output.top_candidate_id
    top_prob = output.top_candidate_probability
    tier = output.confidence_tier

    prev_top_id = prev_output.top_candidate_id if prev_output else None
    prev_top_prob = prev_output.top_candidate_probability if prev_output else 0.0
    prev_tier = prev_output.confidence_tier if prev_output else None

    if prev_tier in ("HIGH", "MEDIUM") and prev_top_id and top_prob < prev_top_prob - 0.3:
        drop = round((prev_top_prob - top_prob) * 100, 1)
        alerts.append(AnomalyAlert(
            rule="confidence_drop",
            severity="warning",
            message=f"Confidence dropped by {drop}% for previous top candidate ({prev_top_id})",
            session_id=sid,
            details={"previous_top_id": prev_top_id, "previous_probability": prev_top_prob,
                     "current_probability": top_prob, "drop_pct": drop},
        ))

    face_evidence = output.evidence.get(top_id or "", [])
    for item in face_evidence:
        if item.agent == "FaceConsistencyAgent" and item.score is not None and item.score < 0.5:
            alerts.append(AnomalyAlert(
                rule="face_score_drop",
                severity="warning",
                message=f"Face consistency score is {item.score:.2f} for top candidate",
                session_id=sid,
                details={"score": item.score, "participant_id": top_id},
            ))

    candidate_count = sum(
        1 for p in session.participants
        if _is_candidate_like(p, output)
    )
    if candidate_count > 1:
        alerts.append(AnomalyAlert(
            rule="dual_candidate",
            severity="info",
            message=f"{candidate_count} participants have candidate-like signals",
            session_id=sid,
            details={"candidate_count": candidate_count},
        ))

    latest_join = max(
        (p.join_timestamp for p in session.participants if p.join_timestamp),
        default=None,
    )
    if latest_join and session.scheduled_start_time and latest_join > session.scheduled_start_time:
        delay_seconds = (latest_join - session.scheduled_start_time).total_seconds()
        if delay_seconds > 180:
            alerts.append(AnomalyAlert(
                rule="late_join",
                severity="info",
                message=f"Participant joined {int(delay_seconds)}s after scheduled start",
                session_id=sid,
                details={"delay_seconds": delay_seconds},
            ))

    confidence_drops = _detect_confidence_oscillation(session)
    if confidence_drops is not None:
        alerts.append(AnomalyAlert(
            rule="confidence_oscillation",
            severity="warning",
            message=(
                f"Confidence oscillating between tiers (tier={tier}, "
                f"history_size={len(session.confidence_history)})"
            ),
            session_id=sid,
            details={"oscillation_count": confidence_drops, "current_tier": tier,
                     "history_size": len(session.confidence_history)},
        ))

    _recent[sid].extend(alerts)
    if len(_recent[sid]) > _MAX_PER_SESSION:
        _recent[sid] = _recent[sid][-_MAX_PER_SESSION:]

    return alerts


def get_recent_anomalies(session_id: str) -> list[AnomalyAlert]:
    return list(_recent.get(session_id, []))


def _is_candidate_like(p: Participant, output: ArbitratorOutput) -> bool:
    prob = output.candidate_probabilities.get(p.participant_id, 0.0)
    return prob > 0.3


def _detect_confidence_oscillation(session: SessionState) -> int | None:
    if len(session.confidence_history) < 4:
        return None

    recent = session.confidence_history[-4:]
    top_ids: list[str | None] = []
    for entry in recent:
        if entry.probabilities:
            top_id = max(entry.probabilities, key=lambda pid: entry.probabilities[pid])
            top_ids.append(top_id)
        else:
            top_ids.append(None)

    if len(set(top_ids)) > 2:
        return len(set(top_ids))
    return None
