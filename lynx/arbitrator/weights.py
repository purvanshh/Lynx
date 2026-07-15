import json
from pathlib import Path
from typing import TYPE_CHECKING

from lynx.models.evidence import EvidenceItem

if TYPE_CHECKING:
    from lynx.agents.base import BaseAgent

DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "NameMatcher": 0.15,
    "TemporalAgent": 0.18,
    "BehavioralAgent": 0.22,
    "SoloWindowAgent": 0.22,
    "FaceConsistencyAgent": 0.08,
    "LLMReasoningAgent": 0.05,
    "ScreenShareAgent": 0.10,
}

ADAPTED_WEIGHTS_PATH = Path("data/adapted_weights.json")
_WEIGHT_LOWER_BOUND = 0.02
_WEIGHT_UPPER_BOUND = 0.50
_EMA_ALPHA = 0.15


def redistribute_global_weights(
    base_weights: dict[str, float],
    globally_active: set[str],
) -> dict[str, float]:
    if not globally_active:
        return {}

    total = sum(base_weights[name] for name in globally_active)
    return {name: base_weights[name] / total for name in globally_active}


def adapt_weights_from_feedback(
    session_id: str,
    agents: list["BaseAgent"],
    evidence: dict[str, list[EvidenceItem]],
    correct_candidate_id: str,
) -> dict[str, float]:
    current = _load_adapted_weights()

    for agent in agents:
        name = agent.name
        base_weight = current.get(name, DEFAULT_AGENT_WEIGHTS.get(name, 0.05))

        agent_scores_for_correct = [
            item.score for item in evidence.get(correct_candidate_id, []) if item.agent == name
        ]
        score = agent_scores_for_correct[0] if agent_scores_for_correct else None

        if score is not None:
            correction = base_weight + (score - 0.5) * 0.2
        else:
            correction = base_weight * 0.8

        new_weight = base_weight + _EMA_ALPHA * (correction - base_weight)
        new_weight = max(_WEIGHT_LOWER_BOUND, min(_WEIGHT_UPPER_BOUND, new_weight))
        current[name] = round(new_weight, 4)

    total = sum(current.values())
    if total > 0:
        current = {k: round(v / total, 4) for k, v in current.items()}

    for name in current:
        current[name] = max(_WEIGHT_LOWER_BOUND, min(_WEIGHT_UPPER_BOUND, current[name]))

    total = sum(current.values())
    if total > 0:
        current = {k: v / total for k, v in current.items()}

    _save_adapted_weights(current)
    return dict(current)


def _load_adapted_weights() -> dict[str, float]:
    if ADAPTED_WEIGHTS_PATH.exists():
        try:
            return json.loads(ADAPTED_WEIGHTS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_AGENT_WEIGHTS)


def _save_adapted_weights(weights: dict[str, float]) -> None:
    ADAPTED_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADAPTED_WEIGHTS_PATH.write_text(
        json.dumps(weights, indent=2) + "\n", encoding="utf-8"
    )
