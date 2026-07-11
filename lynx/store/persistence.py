import json
from pathlib import Path

from lynx.models.session import SessionState


def save_session(path: Path, session: SessionState) -> None:
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def load_session(path: Path) -> SessionState:
    return SessionState.model_validate(json.loads(path.read_text(encoding="utf-8")))
