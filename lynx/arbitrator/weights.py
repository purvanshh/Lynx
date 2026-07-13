DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "NameMatcher": 0.15,
    "TemporalAgent": 0.18,
    "BehavioralAgent": 0.22,
    "SoloWindowAgent": 0.22,
    "FaceConsistencyAgent": 0.08,
    "LLMReasoningAgent": 0.05,
    "ScreenShareAgent": 0.10,
}


def redistribute_global_weights(
    base_weights: dict[str, float],
    globally_active: set[str],
) -> dict[str, float]:
    if not globally_active:
        return {}

    total = sum(base_weights[name] for name in globally_active)
    return {name: base_weights[name] / total for name in globally_active}
