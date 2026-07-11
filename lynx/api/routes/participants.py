from fastapi import APIRouter, Depends, HTTPException

from lynx.api.dependencies import get_store
from lynx.arbitrator.confidence import confidence_tier
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
) -> dict[str, str | float]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.participants:
        raise HTTPException(status_code=400, detail="No participants in session")

    probabilities = session.prior_probabilities or {
        participant.participant_id: 1.0 / len(session.participants)
        for participant in session.participants
    }
    candidate_id = max(probabilities, key=probabilities.get)
    candidate_probability = probabilities[candidate_id]

    return {
        "participant_id": candidate_id,
        "candidate_probability": candidate_probability,
        "confidence_tier": confidence_tier(candidate_probability),
    }
