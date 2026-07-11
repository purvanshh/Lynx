import math

from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS, redistribute_global_weights


class LogOddsArbitrator:
    def __init__(self, base_weights: dict[str, float] | None = None, epsilon: float = 1e-6) -> None:
        self.base_weights = base_weights or DEFAULT_AGENT_WEIGHTS
        self.epsilon = epsilon

    def _clamp(self, probability: float) -> float:
        return max(self.epsilon, min(1 - self.epsilon, probability))

    def _log_odds(self, probability: float) -> float:
        clamped = self._clamp(probability)
        return math.log(clamped / (1 - clamped))

    def update(
        self,
        participants: list[str],
        agent_results: dict[str, dict[str, float | None]],
        prior_probabilities: dict[str, float],
    ) -> dict[str, float]:
        globally_active = {
            agent_name
            for agent_name, scores in agent_results.items()
            if any(score is not None for score in scores.values())
        }

        if not globally_active:
            return prior_probabilities

        weights = redistribute_global_weights(self.base_weights, globally_active)
        default_prior = 1.0 / len(participants)
        odds: dict[str, float] = {}

        for participant_id in participants:
            prior = self._clamp(prior_probabilities.get(participant_id, default_prior))
            prior_log_odds = self._log_odds(prior)

            weight_sum = 0.0
            weighted_log_odds = 0.0

            for agent_name, scores in agent_results.items():
                if agent_name not in globally_active:
                    continue

                score = scores.get(participant_id)
                if score is None:
                    continue

                weight = weights[agent_name]
                weight_sum += weight
                weighted_log_odds += weight * self._log_odds(score)

            posterior_log_odds = ((1 - weight_sum) * prior_log_odds) + weighted_log_odds
            odds[participant_id] = math.exp(posterior_log_odds)

        total_odds = sum(odds.values())
        return {participant_id: odds[participant_id] / total_odds for participant_id in participants}
