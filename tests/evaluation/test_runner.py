import json
from datetime import datetime, timezone
from pathlib import Path

from evaluation.runner import evaluate_cases, write_evaluation_checkpoint
from evaluation.scoring import build_case_score
from evaluation.schemas import BenchmarkCase


def benchmark_case(case_id: str) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        task_type="incident_report_generation",
        difficulty="mid",
        prompt="Evaluate this report.",
        scoring={"metric": "report_quality_1_5", "max_points": 5},
    )


def test_evaluation_generates_and_judges_cases_sequentially() -> None:
    events: list[str] = []
    checkpoints: list[tuple[int, int, bool]] = []

    class SequentialClient:
        def generate(self, case, messages):
            events.append(f"generate:{case.case_id}")
            return f"prediction-{case.case_id}"

    class SequentialJudge:
        def score(self, case, prediction):
            events.append(f"judge:{case.case_id}")
            return build_case_score(case, 4, {"prediction": prediction})

    predictions, scores = evaluate_cases(
        [benchmark_case("case-1"), benchmark_case("case-2")],
        client=SequentialClient(),
        judge=SequentialJudge(),
        prompt_config={},
        generation_config={},
        model_label="target",
        model_name="target-model",
        on_case_complete=lambda predictions, scores, complete: checkpoints.append(
            (len(predictions), len(scores), complete)
        ),
    )

    assert [row["case_id"] for row in predictions] == ["case-1", "case-2"]
    assert [row.case_id for row in scores] == ["case-1", "case-2"]
    assert events == [
        "generate:case-1",
        "judge:case-1",
        "generate:case-2",
        "judge:case-2",
    ]
    assert checkpoints == [(1, 1, False), (2, 2, True)]


def test_checkpoint_writes_every_evaluation_artifact(tmp_path: Path) -> None:
    case = benchmark_case("case-1")
    prediction = {
        "case_id": case.case_id,
        "task_type": case.task_type,
        "model_label": "target",
        "model": "target-model",
        "prediction": "candidate response",
    }
    score = build_case_score(case, 4, {"reason": "mostly correct"})

    write_evaluation_checkpoint(
        output_dir=tmp_path,
        predictions=[prediction],
        scores=[score],
        scoring_config={"judge": {"model": "judge-model"}},
        benchmark_fingerprint="benchmark-fingerprint",
        planned_case_count=2,
        is_complete=False,
        run_id="test-run",
        created_at=datetime.now(timezone.utc),
        config_path=Path("configs/evaluation.yaml"),
        cases_path=Path("evaluation/benchmark"),
        model_label="target",
        model_name="target-model",
        generation_mode="prediction_file",
    )

    predictions = [
        json.loads(line)
        for line in (tmp_path / "predictions.jsonl").read_text().splitlines()
    ]
    case_results = [
        json.loads(line)
        for line in (tmp_path / "scorecards/llm_judge/case_results.jsonl")
        .read_text()
        .splitlines()
    ]
    scores = json.loads((tmp_path / "scorecards/llm_judge/scores.json").read_text())
    manifest = json.loads((tmp_path / "evaluation_manifest.json").read_text())

    assert [row["case_id"] for row in predictions] == ["case-1"]
    assert [row["case_id"] for row in case_results] == ["case-1"]
    assert scores["run_status"] == "in_progress"
    assert scores["completed_case_count"] == 1
    assert scores["planned_case_count"] == 2
    assert manifest["status"] == "in_progress"
    assert manifest["case_count"] == 1
    assert manifest["planned_case_count"] == 2
    assert not list(tmp_path.rglob("*.tmp"))
