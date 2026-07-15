from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    candidate_name: str | None = None
    candidate_email: str | None = None
    interviewer_names: list[str] = Field(default_factory=list)
    scheduled_start_time: datetime | None = None
    calendar_invite_text: str | None = None


class EventRequest(BaseModel):
    type: str
    timestamp: datetime
    participant_id: str | None = None
    display_name: str | None = None
    webcam_on: bool | None = None
    new_name: str | None = None
    utterance: str | None = None
    duration_seconds: float | None = None
    activity: list[bool] = Field(default_factory=list)
    face_count: int | None = None
    image_path: str | None = None


class FeedbackRequest(BaseModel):
    correct_candidate_id: str
    confidence: float | None = None
    notes: str | None = None
