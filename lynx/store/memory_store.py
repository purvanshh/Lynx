from lynx.models.session import SessionState


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def save(self, session: SessionState) -> SessionState:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def list_participants(self, session_id: str) -> list[dict[str, str]]:
        session = self.get(session_id)
        if session is None:
            return []
        return [
            {
                "participant_id": participant.participant_id,
                "display_name": participant.display_name,
            }
            for participant in session.participants
        ]
