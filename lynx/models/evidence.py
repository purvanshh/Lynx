from datetime import datetime

from pydantic import BaseModel


class EvidenceItem(BaseModel):
    agent: str
    score: float | None
    weight: float
    reasoning: str


class ArbitratorOutput(BaseModel):
    session_id: str
    candidate_probabilities: dict[str, float]
    evidence: dict[str, list[EvidenceItem]]
    top_candidate_id: str | None
    top_candidate_probability: float
    confidence_tier: str
    arbitrator_explanation: str
    updated_at: datetime
