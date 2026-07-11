from lynx.arbitrator.arbitrator import LogOddsArbitrator


def test_arbitrator_normalizes_probabilities() -> None:
    arbitrator = LogOddsArbitrator()
    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.8, "p2": 0.2},
            "TemporalAgent": {"p1": 0.7, "p2": 0.3},
        },
        prior_probabilities={"p1": 0.5, "p2": 0.5},
    )

    assert round(sum(results.values()), 6) == 1.0
    assert results["p1"] > results["p2"]
