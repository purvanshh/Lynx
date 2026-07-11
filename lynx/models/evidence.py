from pydantic import BaseModel


class EvidenceItem(BaseModel):
    agent: str
    score: float | None
    weight: float
    reasoning: str
