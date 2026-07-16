from collections import Counter, defaultdict
from typing import Any

from evaluation.schemas import BenchmarkCase, CaseScore


def build_case_score(
    case: BenchmarkCase,
    score: float,
    details: dict[str, Any],
    *,
    metric: str | None = None,
    manual_review_recommended: bool = True,
) -> CaseScore:
    """Build one bounded LLM-judge score for a benchmark case."""

    max_points = float(case.scoring.max_points or 5.0)
    bounded_score = max(0.0, min(float(score), max_points))
    return CaseScore(
        case_id=case.case_id,
        task_type=case.task_type,
        evaluator="llm_judge",
        metric=metric or f"llm_judge:{case.scoring.metric}",
        score=round(bounded_score, 4),
        normalized_score=round(
            bounded_score / max_points if max_points else 0.0,
            4,
        ),
        max_points=max_points,
        details=details,
        manual_review_recommended=manual_review_recommended,
    )


def aggregate_scores(
    scores: list[CaseScore],
    *,
    benchmark_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Aggregate one judge scorecard without blending evaluator types."""

    if not scores:
        return {
            "evaluator": "llm_judge",
            "overall_normalized_score": 0.0,
            "task_scores": {},
            "case_ids": [],
        }
    evaluators = {score.evaluator for score in scores}
    if evaluators != {"llm_judge"}:
        raise ValueError("The scorecard may contain only llm_judge results")

    by_task: dict[str, list[CaseScore]] = defaultdict(list)
    for score in scores:
        by_task[score.task_type].append(score)

    task_scores = {}
    for task_type, task_cases in sorted(by_task.items()):
        normalized = [case.normalized_score for case in task_cases]
        task_scores[task_type] = {
            "cases": len(task_cases),
            "mean_normalized_score": round(sum(normalized) / len(normalized), 4),
            "manual_review_recommended": sum(
                1 for case in task_cases if case.manual_review_recommended
            ),
        }

    overall = sum(score.normalized_score for score in scores) / len(scores)
    result = {
        "evaluator": "llm_judge",
        "overall_normalized_score": round(overall, 4),
        "task_scores": task_scores,
        "metric_counts": dict(Counter(score.metric for score in scores)),
        "case_ids": sorted(score.case_id for score in scores),
    }
    if benchmark_fingerprint:
        result["benchmark_fingerprint"] = benchmark_fingerprint
    return result
