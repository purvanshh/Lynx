from datetime import datetime

from pydantic import BaseModel, Field

from lynx.models.participant import Participant
from lynx.models.transcript import TranscriptUtterance


class ConfidenceHistoryEntry(BaseModel):
    timestamp: datetime
    probabilities: dict[str, float]


class SessionEventEntry(BaseModel):
    timestamp: datetime
    type: str
    participant_id: str | None = None
    display_name: str | None = None
    details: str | None = None


class SessionState(BaseModel):
    session_id: str
    candidate_name: str | None = None
    candidate_email: str | None = None
    interviewer_names: list[str] = Field(default_factory=list)
    scheduled_start_time: datetime | None = None
    calendar_invite_text: str | None = None
    created_at: datetime | None = None
    current_time: datetime | None = None
    participants: list[Participant] = Field(default_factory=list)
    transcript: list[TranscriptUtterance] = Field(default_factory=list)
    prior_probabilities: dict[str, float] = Field(default_factory=dict)
    confidence_history: list[ConfidenceHistoryEntry] = Field(default_factory=list)
    event_log: list[SessionEventEntry] = Field(default_factory=list)
    correct_candidate_id: str | None = None
