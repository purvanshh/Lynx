import asyncio

from scripts.evaluate import assert_prd_targets, compute_metrics, run_evaluation, EvaluationResult


def test_compute_metrics_aggregates_results() -> None:
    metrics = compute_metrics(
        [
            EvaluationResult(
                scenario_id="happy_path",
                correct_candidate_id="p1",
                identified_at_seconds=60.0,
                confidence_at_identification=0.91,
                final_accuracy=True,
                false_positive=False,
                uncertainty_flagged=False,
                final_candidate_id="p1",
                final_confidence_tier="HIGH",
                checkpoints_seen=[30.0, 60.0],
            ),
            EvaluationResult(
                scenario_id="generic_name",
                correct_candidate_id="p1",
                identified_at_seconds=None,
                confidence_at_identification=0.0,
                final_accuracy=False,
                false_positive=True,
                uncertainty_flagged=True,
                final_candidate_id="p2",
                final_confidence_tier="HIGH",
                checkpoints_seen=[30.0, 60.0, 120.0],
            ),
        ]
    )

    assert metrics["identification_accuracy"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["avg_time_to_correct_id_seconds"] == 60.0
    assert metrics["scenarios_passed"] == 1
    assert metrics["uncertainty_flags_correct"] == 1
    assert metrics["happy_path_time_to_correct_id_seconds"] == 60.0
    assert metrics["happy_path_confidence_at_id"] == 0.91


def test_assert_prd_targets_rejects_failed_metrics() -> None:
    try:
        assert_prd_targets(
            {
                "identification_accuracy": 0.5,
                "false_positive_rate": 0.2,
                "avg_time_to_correct_id_seconds": 0.0,
                "scenarios_passed": 1,
                "uncertainty_flags_correct": 0,
                "happy_path_time_to_correct_id_seconds": 180.0,
                "happy_path_confidence_at_id": 0.6,
            }
        )
    except AssertionError as error:
        assert "Accuracy too low" in str(error)
    else:
        raise AssertionError("Expected PRD target assertion to fail")


def test_run_evaluation_in_process_happy_path() -> None:
    results, metrics = asyncio.run(
        run_evaluation(
            ["simulator/scenarios/happy_path.json"],
            in_process=True,
        )
    )

    assert len(results) == 1
    assert results[0].scenario_id == "happy_path"
    assert results[0].final_accuracy is True
    assert metrics["identification_accuracy"] == 1.0


def test_assert_prd_targets_accepts_healthy_metrics() -> None:
    assert_prd_targets(
        {
            "identification_accuracy": 1.0,
            "false_positive_rate": 0.0,
            "avg_time_to_correct_id_seconds": 30.0,
            "scenarios_passed": 7,
            "uncertainty_flags_correct": 1,
            "happy_path_time_to_correct_id_seconds": 30.0,
            "happy_path_confidence_at_id": 0.9,
        }
    )
