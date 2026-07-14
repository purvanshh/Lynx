from fastapi import APIRouter, Depends

from lynx.api.anomaly import get_recent_anomalies
from lynx.api.dependencies import get_store
from lynx.store.memory_store import InMemorySessionStore

router = APIRouter(prefix="/sessions", tags=["analytics"])


@router.get("/{session_id}/anomalies")
def get_session_anomalies(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
) -> dict[str, object]:
    session = store.get(session_id)
    if session is None:
        return {"session_id": session_id, "anomalies": []}
    anomalies = get_recent_anomalies(session_id)
    return {
        "session_id": session_id,
        "anomalies": [
            {"rule": a.rule, "severity": a.severity, "message": a.message, "details": a.details}
            for a in anomalies
        ],
    }
