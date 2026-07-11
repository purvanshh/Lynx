from datetime import datetime

from pydantic import BaseModel, Field

from lynx.models.participant import Participant
from lynx.models.transcript import TranscriptUtterance


class SessionState(BaseModel):
    session_id: str
    candidate_name: str | None = None
    candidate_email: str | None = None
    interviewer_names: list[str] = Field(default_factory=list)
    scheduled_start_time: datetime | None = None
    participants: list[Participant] = Field(default_factory=list)
    transcript: list[TranscriptUtterance] = Field(default_factory=list)
    prior_probabilities: dict[str, float] = Field(default_factory=dict)
