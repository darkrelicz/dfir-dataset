import argparse
import hashlib
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.judge import LocalLLMJudge, judge_reproducibility_metadata
from evaluation.model_clients import EvaluationClient, build_client
from evaluation.scoring import aggregate_scores
from evaluation.schemas import BenchmarkCase, CaseScore, EvaluationManifest
from evaluation.structured_output import structured_output_instruction
from utils.io import (
    load_jsonl_rows,
    load_yaml,
    log_stage_complete,
    write_json,
    write_jsonl,
)

logger = logging.getLogger(__name__)


def run_evaluation(args: argparse.Namespace) -> int:
    overall_started = time.perf_counter()
    config_path = Path(args.config)
    logger.info("Loading evaluation config: path=%s", config_path)
    config = load_yaml(config_path)
    generation_config = dict(config.get("generation", {}))
    scoring_config = dict(config.get("scoring", {}))

    cases_path = Path(args.cases or config.get("benchmark", {}).get("cases_path"))
    model_label = str(args.model_label or generation_config.get("model_label", "model"))
    model_name = str(args.model or generation_config.get("model", model_label))
    mode = str(args.mode or generation_config.get("mode", "prediction_file"))
    predictions_value = args.predictions or generation_config.get("predictions_path")
    input_predictions_path = Path(predictions_value) if predictions_value else None
    generation_config["model"] = model_name

    created_at = datetime.now(timezone.utc)
    run_id = args.run_id or (
        f"eval-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{slug(model_label)}"
    )
    base_output_dir = Path(config.get("output", {}).get("base_dir", "data/evaluation"))
    output_dir = Path(args.output_dir or base_output_dir / run_id)

    logger.info(
        "Starting Phase 6 evaluation: run_id=%s cases=%s output_dir=%s "
        "model_label=%s model=%s mode=%s",
        run_id,
        cases_path,
        output_dir,
        model_label,
        model_name,
        mode,
    )

    stage_started = time.perf_counter()
    client = build_client(mode, generation_config, input_predictions_path)
    judge_config = scoring_config.get("judge")
    if not isinstance(judge_config, dict):
        raise ValueError("scoring.judge configuration is required for LLM judging")
    judge = LocalLLMJudge(judge_config)
    log_stage_complete(logger, "initialized evaluation clients", stage_started)

    stage_started = time.perf_counter()
    cases = load_cases(cases_path)
    if args.max_cases is not None:
        cases = cases[: args.max_cases]
    validate_cases(cases)
    benchmark_fingerprint = fingerprint_cases(cases)
    log_stage_complete(
        logger,
        "loaded benchmark cases",
        stage_started,
        f"cases={len(cases)} fingerprint={benchmark_fingerprint[:12]}",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_summary: dict[str, Any] = {}

    def checkpoint_outputs(
        completed_predictions: list[dict[str, Any]],
        completed_scores: list[CaseScore],
        is_complete: bool,
    ) -> None:
        nonlocal scorecard_summary
        scorecard_summary = write_evaluation_checkpoint(
            output_dir=output_dir,
            predictions=completed_predictions,
            scores=completed_scores,
            scoring_config=scoring_config,
            benchmark_fingerprint=benchmark_fingerprint,
            planned_case_count=len(cases),
            is_complete=is_complete,
            run_id=run_id,
            created_at=created_at,
            config_path=config_path,
            cases_path=cases_path,
            model_label=model_label,
            model_name=model_name,
            generation_mode=mode,
        )

    stage_started = time.perf_counter()
    evaluate_cases(
        cases,
        client=client,
        judge=judge,
        prompt_config=dict(config.get("prompt", {})),
        generation_config=generation_config,
        model_label=model_label,
        model_name=model_name,
        on_case_complete=checkpoint_outputs,
    )
    log_stage_complete(
        logger,
        "completed prediction and scoring",
        stage_started,
        f"cases={len(cases)}",
    )

    overall_score = scorecard_summary["overall_normalized_score"]
    log_stage_complete(logger, "completed Phase 6 evaluation", overall_started)
    print(
        "Evaluation complete: "
        f"cases={len(cases)}, score={overall_score:.4f}, output={output_dir}"
    )
    return 0


def evaluate_cases(
    cases: list[BenchmarkCase],
    *,
    client: EvaluationClient,
    judge: LocalLLMJudge,
    prompt_config: dict[str, Any],
    generation_config: dict[str, Any],
    model_label: str,
    model_name: str,
    on_case_complete: Callable[[list[dict[str, Any]], list[CaseScore], bool], None],
) -> None:
    """Generate and judge each benchmark case sequentially."""

    predictions: list[dict[str, Any]] = []
    scores: list[CaseScore] = []
    for index, case in enumerate(cases, 1):
        case_started = time.perf_counter()
        logger.info(
            "Starting case %s/%s: case_id=%s task_type=%s target_output=%s",
            index,
            len(cases),
            case.case_id,
            case.task_type,
            case.target_output.format,
        )
        target_started = time.perf_counter()
        logger.info(
            "Starting target generation: case_id=%s task_type=%s target_output=%s",
            case.case_id,
            case.task_type,
            case.target_output.format,
        )
        messages = build_messages(case, prompt_config, generation_config)
        prediction = client.generate(case, messages)
        log_stage_complete(
            logger,
            "finished target generation",
            target_started,
            f"case_id={case.case_id}",
        )

        judge_started = time.perf_counter()
        logger.info("Starting LLM judgement: case_id=%s", case.case_id)
        score = judge.score(case, prediction)
        log_stage_complete(
            logger,
            "finished LLM judgement",
            judge_started,
            f"case_id={case.case_id}",
        )
        predictions.append(
            {
                "case_id": case.case_id,
                "task_type": case.task_type,
                "model_label": model_label,
                "model": model_name,
                "prediction": prediction,
            }
        )
        scores.append(score)
        on_case_complete(predictions, scores, index == len(cases))
        log_stage_complete(
            logger,
            "finished case",
            case_started,
            f"case_id={case.case_id} progress={index}/{len(cases)}",
        )


def write_scorecard(
    output_dir: Path,
    scores: list[CaseScore],
    benchmark_fingerprint: str,
    scoring_config: dict[str, Any],
    *,
    planned_case_count: int,
    is_complete: bool,
) -> dict[str, Any]:
    scorecard_dir = output_dir / "scorecard"
    case_results_path = scorecard_dir / "case_results.jsonl"
    scores_path = scorecard_dir / "scores.json"
    write_jsonl_atomic(
        case_results_path,
        [score.model_dump(mode="json") for score in scores],
    )
    aggregate = aggregate_scores(
        scores,
        benchmark_fingerprint=benchmark_fingerprint,
    )
    judge_config = scoring_config.get("judge", {})
    judge_metadata = judge_reproducibility_metadata(judge_config)
    run_status = "complete" if is_complete else "in_progress"
    aggregate.update(
        {
            **judge_metadata,
            "run_status": run_status,
            "completed_case_count": len(scores),
            "planned_case_count": planned_case_count,
        }
    )
    write_json_atomic(scores_path, aggregate)
    return {
        "case_results_path": str(case_results_path),
        "scores_path": str(scores_path),
        "overall_normalized_score": aggregate["overall_normalized_score"],
        "task_scores": aggregate["task_scores"],
        "run_status": run_status,
        "completed_case_count": len(scores),
        "planned_case_count": planned_case_count,
        "config": {
            "model": judge_config.get("model"),
            "base_url": judge_config.get("base_url"),
            "temperature": judge_config.get("temperature", 0.0),
            "top_p": judge_config.get("top_p", 1.0),
            "max_tokens": judge_config.get("max_tokens"),
            "timeout_seconds": judge_config.get("timeout_seconds"),
            "response_format": judge_config.get("response_format"),
            "request_overrides": judge_config.get("request_overrides", {}),
            "validation_retries": judge_config.get("validation_retries", 1),
            **judge_metadata,
        },
    }


def write_evaluation_checkpoint(
    *,
    output_dir: Path,
    predictions: list[dict[str, Any]],
    scores: list[CaseScore],
    scoring_config: dict[str, Any],
    benchmark_fingerprint: str,
    planned_case_count: int,
    is_complete: bool,
    run_id: str,
    created_at: datetime,
    config_path: Path,
    cases_path: Path,
    model_label: str,
    model_name: str,
    generation_mode: str,
) -> dict[str, Any]:
    """Atomically refresh every run artifact after a completed case."""

    write_jsonl_atomic(output_dir / "predictions.jsonl", predictions)
    scorecard_summary = write_scorecard(
        output_dir,
        scores,
        benchmark_fingerprint,
        scoring_config,
        planned_case_count=planned_case_count,
        is_complete=is_complete,
    )
    manifest = EvaluationManifest(
        run_id=run_id,
        created_at=created_at,
        status="complete" if is_complete else "in_progress",
        planned_case_count=planned_case_count,
        config_path=str(config_path),
        cases_path=str(cases_path),
        output_dir=str(output_dir),
        model_label=model_label,
        model=model_name,
        generation_mode=generation_mode,
        case_count=len(scores),
        case_ids=sorted(score.case_id for score in scores),
        benchmark_fingerprint=benchmark_fingerprint,
        scorecard=scorecard_summary,
    )
    write_json_atomic(
        output_dir / "evaluation_manifest.json",
        manifest.model_dump(mode="json"),
    )
    logger.info(
        "Wrote evaluation checkpoint: completed=%s/%s status=%s output=%s",
        len(scores),
        planned_case_count,
        manifest.status,
        output_dir,
    )
    return scorecard_summary


def write_json_atomic(path: Path, data: Any) -> None:
    temporary_path = path.with_name(path.name + ".tmp")
    write_json(temporary_path, data)
    temporary_path.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary_path = path.with_name(path.name + ".tmp")
    write_jsonl(temporary_path, rows)
    temporary_path.replace(path)


def load_cases(path: Path) -> list[BenchmarkCase]:
    if path.is_dir():
        rows = []
        jsonl_paths = sorted(path.glob("*.jsonl"))
        for jsonl_path in jsonl_paths:
            rows.extend(load_jsonl_rows(jsonl_path))
    else:
        rows = load_jsonl_rows(path)
    return [BenchmarkCase.model_validate(row) for row in rows]


def validate_cases(cases: list[BenchmarkCase]) -> None:
    if not cases:
        raise ValueError("Evaluation benchmark contains no cases")
    case_ids = [case.case_id for case in cases]
    duplicates = sorted(
        case_id for case_id in set(case_ids) if case_ids.count(case_id) > 1
    )
    if duplicates:
        raise ValueError(f"Duplicate benchmark case IDs: {duplicates}")


def fingerprint_cases(cases: list[BenchmarkCase]) -> str:
    payload = [
        case.model_dump(mode="json")
        for case in sorted(cases, key=lambda row: row.case_id)
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_messages(
    case: BenchmarkCase,
    prompt_config: dict[str, Any],
    generation_config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    system_message = str(prompt_config.get("system_message", "")).strip()
    include_context_heading = bool(prompt_config.get("include_context_heading", True))
    user_parts = []
    if case.context:
        if include_context_heading:
            user_parts.append("Context:\n" + case.context.strip())
        else:
            user_parts.append(case.context.strip())
    user_parts.append("Question:\n" + case.prompt.strip())
    output_instruction = structured_output_instruction(case, generation_config or {})
    if output_instruction:
        user_parts.append(output_instruction)
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages
def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
