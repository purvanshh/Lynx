from fastapi import APIRouter, Depends, HTTPException

from lynx.api.dependencies import get_store
from lynx.models.session import SessionState
from lynx.store.memory_store import InMemorySessionStore

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}")
def get_session(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
) -> SessionState:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
