from evaluation.comparison import build_comparison


def scorecard(overall: float) -> dict:
    return {
        "evaluator": "llm_judge",
        "benchmark_fingerprint": "same-benchmark",
        "case_ids": ["case-1"],
        "judge_protocol_version": "judge-v1",
        "judge_config_fingerprint": "same-judge-config",
        "judge_calibration_id": "calibration-v1",
        "overall_normalized_score": overall,
        "task_scores": {"report": {"cases": 1, "mean_normalized_score": overall}},
    }


def test_comparison_is_judge_only() -> None:
    result = build_comparison(scorecard(0.6), scorecard(0.8))

    assert result["evaluator"] == "llm_judge"
    assert result["overall_delta"] == 0.2


def test_comparison_rejects_legacy_statistical_scorecard() -> None:
    legacy = scorecard(0.6)
    legacy["evaluator"] = "statistical"

    try:
        build_comparison(legacy, scorecard(0.8))
    except ValueError as exc:
        assert "expected 'llm_judge'" in str(exc)
    else:
        raise AssertionError("Expected a legacy statistical scorecard to fail")


def test_comparison_rejects_different_judge_configuration() -> None:
    tuned = scorecard(0.8)
    tuned["judge_config_fingerprint"] = "different-judge-config"

    try:
        build_comparison(scorecard(0.6), tuned)
    except ValueError as exc:
        assert "different judge_config_fingerprint" in str(exc)
    else:
        raise AssertionError("Expected judge configuration drift to fail")


def test_comparison_rejects_in_progress_scorecard() -> None:
    baseline = scorecard(0.6)
    baseline["run_status"] = "in_progress"

    try:
        build_comparison(baseline, scorecard(0.8))
    except ValueError as exc:
        assert "not from a completed run" in str(exc)
    else:
        raise AssertionError("Expected an in-progress scorecard to fail")
