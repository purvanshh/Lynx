from fastapi import APIRouter, Depends, HTTPException

from lynx.api.dependencies import get_orchestrator, get_store
from lynx.models.evidence import ArbitratorOutput
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore

router = APIRouter(prefix="/sessions", tags=["participants"])


@router.get("/{session_id}/participants")
def get_participants(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
) -> list[dict[str, str]]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return store.list_participants(session_id)


@router.get("/{session_id}/candidate")
def get_candidate(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, str | float]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.participants:
        raise HTTPException(status_code=400, detail="No participants in session")

    output: ArbitratorOutput = orchestrator.evaluate(session)
    if output.top_candidate_id is None:
        raise HTTPException(status_code=400, detail="No candidate probabilities available")

    return {
        "participant_id": output.top_candidate_id,
        "candidate_probability": output.top_candidate_probability,
        "confidence_tier": output.confidence_tier,
    }
