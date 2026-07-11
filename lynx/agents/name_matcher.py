from rapidfuzz import fuzz

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class NameMatcherAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "NameMatcher"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        candidate_name = session.candidate_name or ""
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        score = fuzz.token_sort_ratio(participant.display_name, candidate_name) / 100
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning="Placeholder fuzzy name match based on display name and candidate name.",
        )
