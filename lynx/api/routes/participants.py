from fastapi import APIRouter, Depends, HTTPException

from lynx.api.dependencies import get_orchestrator, get_store
from lynx.models.evidence import ArbitratorOutput
from lynx.models.session import ConfidenceHistoryEntry
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore
from lynx.utils.time import utc_now

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
) -> dict[str, object]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.participants:
        raise HTTPException(status_code=400, detail="No participants in session")

    output: ArbitratorOutput = orchestrator.evaluate(session)
    if output.top_candidate_id is None:
        raise HTTPException(status_code=400, detail="No candidate probabilities available")

    session.prior_probabilities = output.candidate_probabilities
    session.confidence_history.append(
        ConfidenceHistoryEntry(
            timestamp=utc_now(),
            probabilities=output.candidate_probabilities,
        )
    )
    store.update(session)

    top_participant = next(
        participant for participant in session.participants if participant.participant_id == output.top_candidate_id
    )

    return {
        "participant_id": output.top_candidate_id,
        "display_name": top_participant.display_name,
        "candidate_probability": output.top_candidate_probability,
        "is_candidate": output.confidence_tier in {"HIGH", "MEDIUM"},
        "confidence_tier": output.confidence_tier,
        "evidence": [item.model_dump(mode="json") for item in output.evidence.get(output.top_candidate_id, [])],
        "arbitrator_explanation": output.arbitrator_explanation,
        "updated_at": output.updated_at.isoformat(),
    }
