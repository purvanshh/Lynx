import pytest

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


def test_arbitrator_retains_prior_when_single_agent_is_active() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={"BehavioralAgent": {"p1": 0.7, "p2": 0.3}},
        prior_probabilities={"p1": 0.5, "p2": 0.5},
    )

    assert results["p1"] > 0.5
    assert results["p1"] > 0.7


def test_arbitrator_replaces_prior_when_all_agents_are_active() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.9, "p2": 0.1},
            "TemporalAgent": {"p1": 0.8, "p2": 0.2},
            "BehavioralAgent": {"p1": 0.85, "p2": 0.15},
            "SoloWindowAgent": {"p1": 1.0, "p2": 0.0},
            "FaceConsistencyAgent": {"p1": 0.9, "p2": 0.1},
            "LLMReasoningAgent": {"p1": 0.8, "p2": 0.2},
        },
        prior_probabilities={"p1": 0.01, "p2": 0.99},
    )

    assert results["p1"] > results["p2"]


def test_arbitrator_handles_extreme_scores_stably() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={"SoloWindowAgent": {"p1": 1.0, "p2": 0.0}},
        prior_probabilities={"p1": 0.5, "p2": 0.5},
    )

    assert 0.0 < results["p2"] < 1.0
    assert 0.0 < results["p1"] < 1.0


def test_arbitrator_skips_missing_agent_scores_for_one_participant() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.85, "p2": None},
            "TemporalAgent": {"p1": 0.7, "p2": 0.6},
        },
        prior_probabilities={"p1": 0.5, "p2": 0.5},
    )

    assert results["p1"] > results["p2"]


def test_arbitrator_redistributes_weights_for_globally_inactive_agent() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.8, "p2": 0.2},
            "SoloWindowAgent": {"p1": None, "p2": None},
        },
        prior_probabilities={"p1": 0.5, "p2": 0.5},
    )

    assert results["p1"] > 0.5


def test_arbitrator_converges_with_repeated_supporting_updates() -> None:
    arbitrator = LogOddsArbitrator()
    prior = {"p1": 0.5, "p2": 0.5}

    first = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.8, "p2": 0.2},
            "FaceConsistencyAgent": {"p1": 0.7, "p2": None},
        },
        prior_probabilities=prior,
    )
    second = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={
            "NameMatcher": {"p1": 0.8, "p2": 0.2},
            "FaceConsistencyAgent": {"p1": 0.7, "p2": None},
        },
        prior_probabilities=first,
    )

    assert second["p1"] > first["p1"]


def test_arbitrator_normalizes_multi_class_probabilities() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2", "p3"],
        agent_results={
            "NameMatcher": {"p1": 0.8, "p2": 0.2, "p3": 0.1},
            "TemporalAgent": {"p1": 0.7, "p2": 0.3, "p3": 0.4},
        },
        prior_probabilities={"p1": 0.34, "p2": 0.33, "p3": 0.33},
    )

    assert pytest.approx(sum(results.values()), abs=1e-6) == 1.0
    assert results["p1"] == max(results.values())


def test_arbitrator_handles_small_prior_with_strong_evidence() -> None:
    arbitrator = LogOddsArbitrator()

    results = arbitrator.update(
        participants=["p1", "p2"],
        agent_results={"SoloWindowAgent": {"p1": 0.99, "p2": 0.01}},
        prior_probabilities={"p1": 0.001, "p2": 0.999},
    )

    assert results["p1"] > 0.001
