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

    assert redistributed["BehavioralAgent"] == pytest.approx(0.25 / 0.60, abs=1e-6)
    assert redistributed["SoloWindowAgent"] == pytest.approx(0.25 / 0.60, abs=1e-6)
    assert redistributed["FaceConsistencyAgent"] == pytest.approx(0.10 / 0.60, abs=1e-6)


def test_weight_redistribution_returns_original_values_when_all_are_present() -> None:
    redistributed = redistribute_global_weights(
        DEFAULT_AGENT_WEIGHTS,
        set(DEFAULT_AGENT_WEIGHTS),
    )

    assert redistributed == DEFAULT_AGENT_WEIGHTS


def test_weight_redistribution_returns_empty_mapping_for_empty_active_set() -> None:
    redistributed = redistribute_global_weights(DEFAULT_AGENT_WEIGHTS, set())

    assert redistributed == {}
