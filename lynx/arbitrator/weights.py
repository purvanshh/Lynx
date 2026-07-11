DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "NameMatcher": 0.15,
    "TemporalAgent": 0.20,
    "BehavioralAgent": 0.25,
    "SoloWindowAgent": 0.25,
    "FaceConsistencyAgent": 0.10,
    "LLMReasoningAgent": 0.05,
}


def redistribute_global_weights(
    base_weights: dict[str, float],
    globally_active: set[str],
) -> dict[str, float]:
    if not globally_active:
        return {}

    total = sum(base_weights[name] for name in globally_active)
    return {name: base_weights[name] / total for name in globally_active}
