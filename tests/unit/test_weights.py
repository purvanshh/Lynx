from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS, redistribute_global_weights


def test_weight_redistribution_sums_to_one() -> None:
    redistributed = redistribute_global_weights(
        DEFAULT_AGENT_WEIGHTS,
        {"NameMatcher", "TemporalAgent"},
    )
    assert round(sum(redistributed.values()), 6) == 1.0
