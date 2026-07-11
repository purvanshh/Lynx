from rapidfuzz import fuzz

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState

GENERIC_NAMES = {
    "android",
    "conference room",
    "guest",
    "ipad",
    "iphone",
    "macbook pro",
    "meeting room",
    "teams user",
    "zoom user",
}


class NameMatcherAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "NameMatcher"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        display_name = participant.display_name.strip()
        normalized_display_name = display_name.lower()
        candidate_name = (session.candidate_name or "").strip().lower()
        candidate_email_prefix = ((session.candidate_email or "").split("@")[0]).strip().lower()

        if not normalized_display_name:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.0,
                weight=self.weight,
                reasoning="Display name is empty. No candidate-identifying signal available.",
            )

        for interviewer_name in session.interviewer_names:
            interviewer_score = fuzz.token_sort_ratio(normalized_display_name, interviewer_name.strip().lower())
            if interviewer_score > 80:
                return AgentResult(
                    agent=self.name,
                    participant_id=participant.participant_id,
                    score=0.0,
                    weight=self.weight,
                    reasoning=(
                        f"Display name matches interviewer '{interviewer_name}'. Strong negative identity signal."
                    ),
                )

        if normalized_display_name in GENERIC_NAMES:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.1,
                weight=self.weight,
                reasoning=f"Generic device-style name '{participant.display_name}' is weak evidence.",
            )

        candidate_name_score = (
            fuzz.token_sort_ratio(normalized_display_name, candidate_name) / 100 if candidate_name else 0.0
        )
        email_prefix_score = (
            fuzz.token_sort_ratio(normalized_display_name, candidate_email_prefix) / 100
            if candidate_email_prefix
            else 0.0
        )
        score = round(max(candidate_name_score, email_prefix_score), 3)
        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=score,
            weight=self.weight,
            reasoning=(
                f"Name similarity: {candidate_name_score:.2f}; "
                f"email prefix similarity: {email_prefix_score:.2f}."
            ),
        )
