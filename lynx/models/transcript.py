from datetime import datetime

from pydantic import BaseModel


class TranscriptUtterance(BaseModel):
    speaker_id: str
    utterance: str
    timestamp: datetime
    duration_seconds: float | None = None
