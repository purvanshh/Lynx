from datetime import datetime

from pydantic import BaseModel, Field


class WebcamFrame(BaseModel):
    captured_at: datetime | None = None
    face_count: int | None = None
    image_path: str | None = None


class Participant(BaseModel):
    participant_id: str
    display_name: str
    join_timestamp: datetime | None = None
    leave_timestamp: datetime | None = None
    webcam_on: bool = False
    webcam_frames: list[WebcamFrame] = Field(default_factory=list)
    speaking_activity: list[bool] = Field(default_factory=list)
    speaking_duration_total: float = 0.0
    screen_share_events: list[datetime] = Field(default_factory=list)
