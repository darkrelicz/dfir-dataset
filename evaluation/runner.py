import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.judge import LocalLLMJudge
from evaluation.metrics import aggregate_scores, metric_family, score_case
from evaluation.model_clients import build_client
from evaluation.schemas import BenchmarkCase, CaseScore, EvaluationManifest
from utils.io import (
    load_jsonl_rows,
    load_yaml,
    log_stage_complete,
    write_json,
    write_jsonl,
)

logger = logging.getLogger(__name__)
EVALUATOR_MODES = {"statistical", "llm_judge", "both"}


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
    evaluator_mode = str(
        getattr(args, "evaluator", None)
        or scoring_config.get("evaluator", "statistical")
    ).strip().casefold()
    if evaluator_mode not in EVALUATOR_MODES:
        raise ValueError(
            f"Unsupported evaluator mode {evaluator_mode!r}; "
            f"choose one of {sorted(EVALUATOR_MODES)}"
        )
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
        "model_label=%s model=%s mode=%s evaluator=%s",
        run_id,
        cases_path,
        output_dir,
        model_label,
        model_name,
        mode,
        evaluator_mode,
    )

    stage_started = time.perf_counter()
    client = build_client(mode, generation_config, input_predictions_path)
    judge = build_judge(evaluator_mode, scoring_config)
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
    predictions = []
    scores_by_evaluator: dict[str, list[CaseScore]] = {
        evaluator: [] for evaluator in selected_evaluators(evaluator_mode)
    }

    stage_started = time.perf_counter()
    for index, case in enumerate(cases, 1):
        case_started = time.perf_counter()
        logger.info(
            "Starting case %s/%s: case_id=%s task_type=%s metric=%s",
            index,
            len(cases),
            case.case_id,
            case.task_type,
            case.scoring.metric,
        )
        messages = build_messages(case, config.get("prompt", {}), scoring_config)
        prediction = client.generate(case, messages)
        predictions.append(
            {
                "case_id": case.case_id,
                "task_type": case.task_type,
                "model_label": model_label,
                "model": model_name,
                "prediction": prediction,
            }
        )

        if "statistical" in scores_by_evaluator:
            scores_by_evaluator["statistical"].append(
                score_case(case, prediction, scoring_config)
            )
        if "llm_judge" in scores_by_evaluator:
            if judge is None:
                raise ValueError("llm_judge evaluator selected without judge config")
            scores_by_evaluator["llm_judge"].append(judge.score(case, prediction))
        log_stage_complete(
            logger,
            "finished case",
            case_started,
            f"case_id={case.case_id} progress={index}/{len(cases)}",
        )
    log_stage_complete(
        logger,
        "completed prediction and scoring",
        stage_started,
        f"cases={len(cases)} evaluator={evaluator_mode}",
    )

    stage_started = time.perf_counter()
    write_jsonl(output_dir / "predictions.jsonl", predictions)
    scorecard_manifest = write_scorecards(
        output_dir,
        scores_by_evaluator,
        benchmark_fingerprint,
        scoring_config,
    )
    manifest = EvaluationManifest(
        run_id=run_id,
        created_at=created_at,
        config_path=str(config_path),
        cases_path=str(cases_path),
        output_dir=str(output_dir),
        model_label=model_label,
        model=model_name,
        generation_mode=mode,
        evaluator_mode=evaluator_mode,
        case_count=len(cases),
        case_ids=sorted(case.case_id for case in cases),
        benchmark_fingerprint=benchmark_fingerprint,
        scorecards=scorecard_manifest,
    )
    write_json(
        output_dir / "evaluation_manifest.json",
        manifest.model_dump(mode="json"),
    )
    log_stage_complete(logger, "wrote evaluation outputs", stage_started)

    summaries = ", ".join(
        f"{name}={row['overall_normalized_score']:.4f}"
        for name, row in scorecard_manifest.items()
    )
    log_stage_complete(logger, "completed Phase 6 evaluation", overall_started)
    print(f"Evaluation complete: cases={len(cases)}, {summaries}, output={output_dir}")
    return 0


def build_judge(
    evaluator_mode: str,
    scoring_config: dict[str, Any],
) -> LocalLLMJudge | None:
    if evaluator_mode not in {"llm_judge", "both"}:
        return None
    judge_config = scoring_config.get("judge")
    if not isinstance(judge_config, dict):
        raise ValueError("scoring.judge configuration is required for LLM judging")
    return LocalLLMJudge(judge_config)


def selected_evaluators(mode: str) -> list[str]:
    if mode == "both":
        return ["statistical", "llm_judge"]
    return [mode]


def write_scorecards(
    output_dir: Path,
    scores_by_evaluator: dict[str, list[CaseScore]],
    benchmark_fingerprint: str,
    scoring_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for evaluator, scores in scores_by_evaluator.items():
        scorecard_dir = output_dir / "scorecards" / evaluator
        case_results_path = scorecard_dir / "case_results.jsonl"
        scores_path = scorecard_dir / "scores.json"
        write_jsonl(
            case_results_path,
            [score.model_dump(mode="json") for score in scores],
        )
        aggregate = aggregate_scores(
            scores,
            benchmark_fingerprint=benchmark_fingerprint,
        )
        write_json(scores_path, aggregate)
        row: dict[str, Any] = {
            "evaluator": evaluator,
            "case_results_path": str(case_results_path),
            "scores_path": str(scores_path),
            "overall_normalized_score": aggregate["overall_normalized_score"],
            "task_scores": aggregate["task_scores"],
        }
        if evaluator == "statistical":
            row["config"] = {
                "ndcg_k": int(scoring_config.get("ndcg_k", 5)),
                "structured_outputs": bool(
                    scoring_config.get("structured_outputs", {}).get("enabled", True)
                ),
                "structured_outputs_required": bool(
                    scoring_config.get("structured_outputs", {}).get("required", False)
                ),
            }
        else:
            judge_config = scoring_config.get("judge", {})
            row["config"] = {
                "model": judge_config.get("model"),
                "base_url": judge_config.get("base_url"),
                "temperature": judge_config.get("temperature", 0.0),
                "validation_retries": judge_config.get("validation_retries", 1),
            }
        manifest[evaluator] = row
    return manifest


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
    for case in cases:
        metric_family(case.scoring.metric)


def fingerprint_cases(cases: list[BenchmarkCase]) -> str:
    payload = [case.model_dump(mode="json") for case in sorted(cases, key=lambda row: row.case_id)]
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
    scoring_config: dict[str, Any] | None = None,
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
    output_instruction = structured_output_instruction(case, scoring_config or {})
    if output_instruction:
        user_parts.append(output_instruction)
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": "\n\n".join(user_parts)})
    return messages


def structured_output_instruction(
    case: BenchmarkCase,
    scoring_config: dict[str, Any],
) -> str | None:
    config = scoring_config.get("structured_outputs", {})
    if not bool(config.get("enabled", True)):
        return None
    family = metric_family(case.scoring.metric)
    if family == "technique_f1":
        return (
            "Output format: Return one JSON object with `techniques` as an array of "
            "ATT&CK or ATLAS IDs and `answer` as your concise evidence-based explanation."
        )
    if family == "ioc_f1":
        return (
            "Output format: Return one JSON object with `iocs` as an array of objects "
            "having `type` and `value`, plus `answer` as a concise explanation. Use "
            "normalized, refanged indicator values."
        )
    if family == "ndcg":
        return (
            "Output format: Return one JSON object with `ranked_actions` as an ordered "
            "array of action IDs and `answer` as your concise ranking rationale."
        )
    return None


def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def message_char_count(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)
