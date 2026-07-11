from datetime import datetime

from pydantic import BaseModel


class Participant(BaseModel):
    participant_id: str
    display_name: str
    join_timestamp: datetime | None = None
    leave_timestamp: datetime | None = None
    webcam_on: bool = False
    speaking_duration_total: float = 0.0
