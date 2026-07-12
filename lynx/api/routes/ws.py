from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from lynx.api.dependencies import get_orchestrator, get_store
from lynx.api.ws_manager import ws_manager
from lynx.models.evidence import ArbitratorOutput
from lynx.models.session import ConfidenceHistoryEntry
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore
from lynx.utils.time import utc_now

router = APIRouter(prefix="/sessions", tags=["websocket"])


def _build_candidate_payload(output: ArbitratorOutput, session_id: str) -> dict:
    return {
        "type": "candidate_update",
        "session_id": session_id,
        "data": {
            "participant_id": output.top_candidate_id,
            "candidate_probability": output.top_candidate_probability,
            "confidence_tier": output.confidence_tier,
            "is_candidate": output.confidence_tier in {"HIGH", "MEDIUM"},
            "candidate_probabilities": output.candidate_probabilities,
            "evidence": {
                pid: [item.model_dump(mode="json") for item in items]
                for pid, items in output.evidence.items()
            },
            "arbitrator_explanation": output.arbitrator_explanation,
            "updated_at": output.updated_at.isoformat(),
        },
    }


@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> None:
    session = store.get(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await ws_manager.connect(session_id, websocket)

    if session.participants:
        output = orchestrator.evaluate(session)
        session.prior_probabilities = output.candidate_probabilities
        session.confidence_history.append(
            ConfidenceHistoryEntry(
                timestamp=utc_now(),
                probabilities=output.candidate_probabilities,
            )
        )
        store.update(session)
        await ws_manager.broadcast(session_id, _build_candidate_payload(output, session_id))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(session_id, websocket)
