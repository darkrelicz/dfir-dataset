import argparse
import logging
import time
from pathlib import Path
from typing import Any

from utils.io import load_json, log_stage_complete, write_json

logger = logging.getLogger(__name__)


def compare_evaluations(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    baseline_dir = Path(args.baseline_dir)
    tuned_dir = Path(args.tuned_dir)
    output_dir = Path(args.output_dir)
    evaluator = "llm_judge"
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_scores = load_scorecard(baseline_dir)
    tuned_scores = load_scorecard(tuned_dir)
    comparison = build_comparison(
        baseline_scores,
        tuned_scores,
        minimum_overall_delta=float(getattr(args, "minimum_overall_delta", 0.0)),
        max_task_regression=float(getattr(args, "max_task_regression", 0.05)),
    )

    write_json(output_dir / f"comparison_{evaluator}.json", comparison)
    (output_dir / f"comparison_{evaluator}.md").write_text(
        render_markdown(comparison),
        encoding="utf-8",
    )
    log_stage_complete(
        logger,
        "completed evaluation comparison",
        started,
        f"path={output_dir} evaluator={evaluator}",
    )
    print(
        "Comparison complete: "
        f"evaluator={evaluator}, "
        f"baseline={comparison['baseline_overall']:.4f}, "
        f"tuned={comparison['tuned_overall']:.4f}, "
        f"delta={comparison['overall_delta']:.4f}, "
        f"passes={comparison['passes_regression_gate']}"
    )
    return 0


def load_scorecard(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "scorecards" / "llm_judge" / "scores.json"
    scores = load_json(path, logger)
    if not scores:
        raise FileNotFoundError(f"Missing LLM-judge scorecard: {path}")
    return scores


def build_comparison(
    baseline_scores: dict[str, Any],
    tuned_scores: dict[str, Any],
    *,
    minimum_overall_delta: float = 0.0,
    max_task_regression: float = 0.05,
) -> dict[str, Any]:
    validate_compatible_scorecards(baseline_scores, tuned_scores)
    baseline_overall = float(baseline_scores["overall_normalized_score"])
    tuned_overall = float(tuned_scores["overall_normalized_score"])
    baseline_tasks = baseline_scores.get("task_scores", {})
    tuned_tasks = tuned_scores.get("task_scores", {})
    task_deltas = {}
    severe_regressions = []
    for task_type in sorted(set(baseline_tasks) | set(tuned_tasks)):
        baseline = float(
            baseline_tasks.get(task_type, {}).get("mean_normalized_score", 0.0)
        )
        tuned = float(tuned_tasks.get(task_type, {}).get("mean_normalized_score", 0.0))
        delta = tuned - baseline
        regressed_beyond_gate = delta < -max_task_regression
        if regressed_beyond_gate:
            severe_regressions.append(task_type)
        task_deltas[task_type] = {
            "baseline": round(baseline, 4),
            "tuned": round(tuned, 4),
            "delta": round(delta, 4),
            "regressed_beyond_gate": regressed_beyond_gate,
        }
    overall_delta = tuned_overall - baseline_overall
    passes = overall_delta > minimum_overall_delta and not severe_regressions
    return {
        "evaluator": "llm_judge",
        "benchmark_fingerprint": baseline_scores["benchmark_fingerprint"],
        "case_count": len(baseline_scores["case_ids"]),
        "baseline_overall": round(baseline_overall, 4),
        "tuned_overall": round(tuned_overall, 4),
        "overall_delta": round(overall_delta, 4),
        "minimum_overall_delta": minimum_overall_delta,
        "max_task_regression": max_task_regression,
        "task_deltas": task_deltas,
        "severe_regressions": severe_regressions,
        "passes_regression_gate": passes,
    }


def validate_compatible_scorecards(
    baseline_scores: dict[str, Any],
    tuned_scores: dict[str, Any],
) -> None:
    for label, scores in (("baseline", baseline_scores), ("tuned", tuned_scores)):
        if scores.get("evaluator") != "llm_judge":
            raise ValueError(
                f"{label} scorecard evaluator is {scores.get('evaluator')!r}, "
                "expected 'llm_judge'"
            )
        if not scores.get("benchmark_fingerprint"):
            raise ValueError(f"{label} scorecard lacks a benchmark fingerprint")
        if not isinstance(scores.get("case_ids"), list):
            raise ValueError(f"{label} scorecard lacks case IDs")
        if scores.get("run_status", "complete") != "complete":
            raise ValueError(f"{label} scorecard is not from a completed run")
    if (
        baseline_scores["benchmark_fingerprint"]
        != tuned_scores["benchmark_fingerprint"]
    ):
        raise ValueError("Cannot compare scorecards from different benchmark content")
    if baseline_scores["case_ids"] != tuned_scores["case_ids"]:
        raise ValueError("Cannot compare scorecards with different case IDs")
    for field in (
        "judge_protocol_version",
        "judge_config_fingerprint",
        "judge_calibration_id",
    ):
        if not baseline_scores.get(field) or not tuned_scores.get(field):
            raise ValueError(f"Cannot compare scorecards without matching {field}")
        if baseline_scores[field] != tuned_scores[field]:
            raise ValueError(f"Cannot compare scorecards with different {field}")


def render_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# Phase 6 Evaluation Comparison",
        "",
        f"Evaluator: `{comparison['evaluator']}`",
        "",
        "| Metric | Baseline | Fine-tuned | Delta |",
        "|---|---:|---:|---:|",
        (
            f"| Overall | {comparison['baseline_overall']:.4f} | "
            f"{comparison['tuned_overall']:.4f} | "
            f"{comparison['overall_delta']:.4f} |"
        ),
        "",
        "## Task Deltas",
        "",
        "| Task | Baseline | Fine-tuned | Delta | Gate |",
        "|---|---:|---:|---:|---|",
    ]
    for task_type, row in comparison["task_deltas"].items():
        gate = "fail" if row["regressed_beyond_gate"] else "pass"
        lines.append(
            f"| `{task_type}` | {row['baseline']:.4f} | "
            f"{row['tuned']:.4f} | {row['delta']:.4f} | {gate} |"
        )
    lines.extend(
        [
            "",
            "## Decision Gate",
            "",
            (
                "This scorecard passes the configured regression gate."
                if comparison["passes_regression_gate"]
                else "This scorecard does not pass the configured regression gate."
            ),
            "",
        ]
    )
    return "\n".join(lines)
