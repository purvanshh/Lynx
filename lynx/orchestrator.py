from datetime import UTC, datetime

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.arbitrator import LogOddsArbitrator
from lynx.arbitrator.confidence import confidence_tier
from lynx.arbitrator.weights import redistribute_global_weights
from lynx.models.evidence import ArbitratorOutput, EvidenceItem
from lynx.models.session import SessionState


class AgentOrchestrator:
    def __init__(self, agents: list[BaseAgent], arbitrator: LogOddsArbitrator) -> None:
        self.agents = agents
        self.arbitrator = arbitrator
        self._result_cache: dict[str, tuple[int, ArbitratorOutput]] = {}

    def evaluate(self, session: SessionState) -> ArbitratorOutput:
        version = len(session.event_log)
        cached = self._result_cache.get(session.session_id)
        if cached is not None and cached[0] == version:
            return cached[1]

        result = self._evaluate(session)
        self._result_cache[session.session_id] = (version, result)
        return result

    def invalidate_cache(self, session_id: str) -> None:
        self._result_cache.pop(session_id, None)

    def _evaluate(self, session: SessionState) -> ArbitratorOutput:
        participant_ids = [participant.participant_id for participant in session.participants]
        if not participant_ids:
            return ArbitratorOutput(
                session_id=session.session_id,
                candidate_probabilities={},
                evidence={},
                top_candidate_id=None,
                top_candidate_probability=0.0,
                confidence_tier="UNCERTAIN",
                arbitrator_explanation="No participants available for evaluation.",
                updated_at=datetime.now(UTC),
            )

        raw_results: dict[str, dict[str, AgentResult | None]] = {}
        score_inputs: dict[str, dict[str, float | None]] = {}

        for agent in self.agents:
            agent_results: dict[str, AgentResult | None] = {}
            agent_scores: dict[str, float | None] = {}
            for participant_id in participant_ids:
                result = agent.evaluate(session, participant_id)
                agent_results[participant_id] = result
                agent_scores[participant_id] = None if result is None else result.score
            raw_results[agent.name] = agent_results
            score_inputs[agent.name] = agent_scores

        globally_active = {
            agent.name
            for agent in self.agents
            if any(result is not None for result in raw_results[agent.name].values())
        }
        redistributed_weights = redistribute_global_weights(
            {agent.name: agent.get_effective_weight() for agent in self.agents},
            globally_active,
        )

        default_prior = 1.0 / len(participant_ids)
        prior_probabilities = {
            participant_id: session.prior_probabilities.get(participant_id, default_prior)
            for participant_id in participant_ids
        }
        candidate_probabilities = self.arbitrator.update(
            participants=participant_ids,
            agent_results=score_inputs,
            prior_probabilities=prior_probabilities,
        )

        evidence: dict[str, list[EvidenceItem]] = {participant_id: [] for participant_id in participant_ids}
        for agent in self.agents:
            effective_weight = redistributed_weights.get(agent.name, 0.0)
            for participant_id in participant_ids:
                result = raw_results[agent.name][participant_id]
                evidence[participant_id].append(
                    EvidenceItem(
                        agent=agent.name,
                        score=None if result is None else result.score,
                        weight=effective_weight,
                        reasoning=(
                            f"{agent.name} inactive for this participant."
                            if result is None
                            else result.reasoning
                        ),
                    )
                )

        top_candidate_id = max(candidate_probabilities, key=candidate_probabilities.get, default=None)  # type: ignore[arg-type]
        top_candidate_probability = (
            candidate_probabilities[top_candidate_id] if top_candidate_id is not None else 0.0
        )

        if not globally_active:
            explanation = "No active agents produced evidence. Returning prior probabilities."
        else:
            explanation = (
                "Combined evidence from "
                f"{len(globally_active)} active agents with global weight redistribution applied."
            )

        return ArbitratorOutput(
            session_id=session.session_id,
            candidate_probabilities=candidate_probabilities,
            evidence=evidence,
            top_candidate_id=top_candidate_id,
            top_candidate_probability=top_candidate_probability,
            confidence_tier=confidence_tier(top_candidate_probability),
            arbitrator_explanation=explanation,
            updated_at=datetime.now(UTC),
        )
