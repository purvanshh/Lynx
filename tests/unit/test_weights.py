import pytest

from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS, redistribute_global_weights


def test_weight_redistribution_sums_to_one() -> None:
    redistributed = redistribute_global_weights(
        DEFAULT_AGENT_WEIGHTS,
        {"NameMatcher", "TemporalAgent"},
    )
    assert round(sum(redistributed.values()), 6) == 1.0


def test_weight_redistribution_scales_remaining_agents() -> None:
    redistributed = redistribute_global_weights(
        DEFAULT_AGENT_WEIGHTS,
        {"BehavioralAgent", "SoloWindowAgent", "FaceConsistencyAgent"},
    )

    total = sum(
        DEFAULT_AGENT_WEIGHTS[name]
        for name in {"BehavioralAgent", "SoloWindowAgent", "FaceConsistencyAgent"}
    )
    assert redistributed["BehavioralAgent"] == pytest.approx(DEFAULT_AGENT_WEIGHTS["BehavioralAgent"] / total, abs=1e-6)
    assert redistributed["SoloWindowAgent"] == pytest.approx(DEFAULT_AGENT_WEIGHTS["SoloWindowAgent"] / total, abs=1e-6)
    assert redistributed["FaceConsistencyAgent"] == pytest.approx(DEFAULT_AGENT_WEIGHTS["FaceConsistencyAgent"] / total, abs=1e-6)


def test_weight_redistribution_returns_original_values_when_all_are_present() -> None:
    redistributed = redistribute_global_weights(
        DEFAULT_AGENT_WEIGHTS,
        set(DEFAULT_AGENT_WEIGHTS),
    )

    for agent, weight in DEFAULT_AGENT_WEIGHTS.items():
        assert redistributed[agent] == pytest.approx(weight, abs=1e-6)


def test_weight_redistribution_returns_empty_mapping_for_empty_active_set() -> None:
    redistributed = redistribute_global_weights(DEFAULT_AGENT_WEIGHTS, set())

    assert redistributed == {}
