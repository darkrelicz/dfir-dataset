from collections import Counter, defaultdict
from typing import Any

from evaluation.schemas import BenchmarkCase, CaseScore


def build_case_score(
    case: BenchmarkCase,
    score: float,
    details: dict[str, Any],
) -> CaseScore:
    """Build one bounded LLM-judge score for a benchmark case."""

    max_points = float(case.scoring.max_points)
    bounded_score = max(0.0, min(float(score), max_points))
    return CaseScore(
        case_id=case.case_id,
        task_type=case.task_type,
        metric=case.scoring.metric,
        score=round(bounded_score, 4),
        normalized_score=round(bounded_score / max_points, 4),
        max_points=max_points,
        details=details,
    )


def aggregate_scores(
    scores: list[CaseScore],
    *,
    benchmark_fingerprint: str,
) -> dict[str, Any]:
    """Aggregate the local judge scores for a non-empty benchmark subset."""

    by_task: dict[str, list[CaseScore]] = defaultdict(list)
    for score in scores:
        by_task[score.task_type].append(score)

    task_scores = {}
    for task_type, task_cases in sorted(by_task.items()):
        normalized = [case.normalized_score for case in task_cases]
        task_scores[task_type] = {
            "cases": len(task_cases),
            "mean_normalized_score": round(sum(normalized) / len(normalized), 4),
        }

    overall = sum(score.normalized_score for score in scores) / len(scores)
    return {
        "overall_normalized_score": round(overall, 4),
        "task_scores": task_scores,
        "metric_counts": dict(Counter(score.metric for score in scores)),
        "case_ids": sorted(score.case_id for score in scores),
        "benchmark_fingerprint": benchmark_fingerprint,
    }
