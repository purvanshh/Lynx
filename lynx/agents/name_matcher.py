from rapidfuzz import fuzz

from lynx.agents.base import AgentResult, BaseAgent
from lynx.models.session import SessionState


class NameMatcherAgent(BaseAgent):
    name = "NameMatcher"

    def evaluate(self, session: SessionState) -> list[AgentResult]:
        candidate_name = session.candidate_name or ""
        results: list[AgentResult] = []
        for participant in session.participants:
            score = fuzz.token_sort_ratio(participant.display_name, candidate_name) / 100
            results.append(
                AgentResult(
                    participant_id=participant.participant_id,
                    score=round(score, 3),
                    reasoning="Placeholder fuzzy name match based on display name and candidate name.",
                )
            )
        return results
