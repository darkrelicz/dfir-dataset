import json
import logging
import random
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collectors.schemas import RawDocument
from quality.dataset import apply_dataset_gates
from quality.references import QualityReferences, build_quality_references
from quality.schemas import QualityDecision, QualityIssue, QualityManifest
from quality.validators import validate_row_quality
from synthesizers.io import load_raw_documents
from utils.io import append_jsonl, load_yaml, write_json

logger = logging.getLogger(__name__)


def run_quality_filter(args) -> int:
    overall_started = time.perf_counter()
    input_path = Path(args.input)
    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)

    logger.info(
        "Starting Phase 4 quality filter: input=%s raw_dir=%s output_dir=%s",
        input_path,
        raw_dir,
        output_dir,
    )

    stage_started = time.perf_counter()
    quality_config = load_yaml(Path(args.quality_config))
    task_config = load_yaml(Path(args.task_config))
    log_stage_complete(
        "loaded configs",
        stage_started,
        f"quality_config={args.quality_config} task_config={args.task_config}",
    )

    stage_started = time.perf_counter()
    output_paths = prepare_output_files(output_dir, append=args.append)
    log_stage_complete("prepared output files", stage_started, f"append={args.append}")

    stage_started = time.perf_counter()
    raw_docs_by_id = {doc.doc_id: doc for doc in load_raw_documents(raw_dir)}
    log_stage_complete("loaded raw documents", stage_started, f"documents={len(raw_docs_by_id)}")

    stage_started = time.perf_counter()
    references = build_quality_references(quality_config, raw_dir)
    log_stage_complete(
        "built quality references",
        stage_started,
        (
            f"taxonomy_refs={len(references.taxonomy_refs)} "
            f"attack_ids={len(references.attack_ids)} "
            f"atlas_ids={len(references.atlas_ids)} "
            f"tools={len(references.tool_allowlist)}"
        ),
    )
    valid_categories = set(task_config.get("categories", {}))

    created_at = datetime.now(timezone.utc)
    run_id = f"quality-{created_at.strftime('%Y%m%dT%H%M%SZ')}"

    stage_started = time.perf_counter()
    logger.info("Starting row-level quality validation")
    records, row_status_counts, total_pairs = validate_input_records(
        input_path,
        raw_docs_by_id,
        references,
        valid_categories,
        quality_config,
    )

    log_stage_complete(
        "completed row-level quality validation",
        stage_started,
        (
            f"rows={total_pairs} filtered={row_status_counts['filtered']} "
            f"review={row_status_counts['review']} "
            f"rejected={row_status_counts['rejected']}"
        ),
    )

    stage_started = time.perf_counter()
    logger.info("Starting dataset-level quality gates")
    dataset_audits = apply_dataset_gates(records, quality_config, task_config)
    log_stage_complete("completed dataset-level quality gates", stage_started)

    stage_started = time.perf_counter()
    counts = write_quality_outputs(records, output_paths, run_id)
    log_stage_complete(
        "wrote quality output JSONL files",
        stage_started,
        (
            f"filtered={counts['filtered_pairs']} "
            f"review={counts['review_pairs']} "
            f"rejected={counts['rejected_pairs']}"
        ),
    )

    stage_started = time.perf_counter()
    spot_check = write_spot_check_sample(records, output_dir, quality_config, run_id)
    dataset_audits["manual_spot_check"] = spot_check
    log_stage_complete(
        "wrote manual spot-check sample",
        stage_started,
        f"rows={spot_check['actual_sample_size']} path={spot_check['path']}",
    )

    manifest = build_quality_manifest(
        run_id=run_id,
        input_path=input_path,
        raw_dir=raw_dir,
        output_dir=output_dir,
        created_at=created_at,
        total_pairs=total_pairs,
        counts=counts,
        dataset_audits=dataset_audits,
    )
    stage_started = time.perf_counter()
    write_json(output_dir / "quality_manifest.json", manifest.model_dump(mode="json"))
    log_stage_complete(
        "wrote quality manifest",
        stage_started,
        f"path={output_dir / 'quality_manifest.json'}",
    )
    log_stage_complete("completed Phase 4 quality filter", overall_started)
    print(
        f"Quality filter complete: filtered={counts['filtered_pairs']}, "
        f"review={counts['review_pairs']}, rejected={counts['rejected_pairs']}, "
        f"total={total_pairs}"
    )
    return 0


def prepare_output_files(output_dir: Path, *, append: bool) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "filtered": output_dir / "filtered.jsonl",
        "rejected": output_dir / "rejected.jsonl",
        "review": output_dir / "review_queue.jsonl",
    }
    for path in output_paths.values():
        if path.exists() and not append:
            path.unlink()
        path.touch(exist_ok=True)
    return output_paths


def validate_input_records(
    input_path: Path,
    raw_docs_by_id: dict[str, RawDocument],
    references: QualityReferences,
    valid_categories: set[str],
    quality_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    total_pairs = 0

    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue

            total_pairs += 1
            row, decision = validate_input_line(
                line,
                line_number,
                raw_docs_by_id,
                references,
                valid_categories,
                quality_config,
            )
            records.append(
                {
                    "row": row,
                    "decision": decision,
                    "line_number": line_number,
                }
            )
            status_counts[decision.status] += 1

    return records, status_counts, total_pairs


def validate_input_line(
    line: str,
    line_number: int,
    raw_docs_by_id: dict[str, RawDocument],
    references: QualityReferences,
    valid_categories: set[str],
    quality_config: dict[str, Any],
) -> tuple[dict[str, Any], QualityDecision]:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        issue = QualityIssue(
            code="schema_invalid",
            severity="reject",
            message=f"Invalid JSON at line {line_number}: {exc}",
        )
        return {}, QualityDecision(status="rejected", issues=[issue])

    if not isinstance(row, dict):
        issue = QualityIssue(
            code="schema_invalid",
            severity="reject",
            message=f"Expected JSON object at line {line_number}",
        )
        return {}, QualityDecision(status="rejected", issues=[issue])

    decision = validate_row_quality(
        row,
        raw_docs_by_id,
        references,
        valid_categories,
        quality_config,
    )
    return row, decision


def build_quality_manifest(
    *,
    run_id: str,
    input_path: Path,
    raw_dir: Path,
    output_dir: Path,
    created_at: datetime,
    total_pairs: int,
    counts: dict[str, Any],
    dataset_audits: dict[str, Any],
) -> QualityManifest:
    return QualityManifest(
        run_id=run_id,
        input_path=str(input_path),
        raw_dir=str(raw_dir),
        output_dir=str(output_dir),
        created_at=created_at,
        total_pairs=total_pairs,
        filtered_pairs=counts["filtered_pairs"],
        review_pairs=counts["review_pairs"],
        rejected_pairs=counts["rejected_pairs"],
        rejection_counts=counts["rejection_counts"],
        review_counts=counts["review_counts"],
        source_distribution=counts["source_distribution"],
        category_distribution=counts["category_distribution"],
        difficulty_distribution=counts["difficulty_distribution"],
        taxonomy_distribution=counts["taxonomy_distribution"],
        dataset_audits=dataset_audits,
        notes=[
            (
                "Phase 4 does not call Phase 3 output validators; both stages "
                "share pure validation primitives with separate stage policies."
            ),
            "ATT&CK and ATLAS validation uses local STIX/YAML reference caches when present.",
            "Tool validation uses configs/quality.yaml as the allowlist source of truth.",
            (
                "Quality scores are emitted as metadata and used only to rank "
                "rows for duplicate retention and source-balance review."
            ),
            "Reduced-pair subset run: historical 10k-15k filtered target is not expected.",
            "review_queue.jsonl is excluded from filtered training output until reviewed.",
        ],
    )


def log_stage_complete(stage: str, started_at: float, detail: str | None = None) -> None:
    elapsed = time.perf_counter() - started_at
    if detail:
        logger.info("%s in %.1fs (%s)", stage, elapsed, detail)
    else:
        logger.info("%s in %.1fs", stage, elapsed)


def write_quality_outputs(
    records: list[dict[str, Any]],
    output_paths: dict[str, Path],
    run_id: str,
) -> dict[str, Any]:
    filtered_pairs = 0
    rejected_pairs = 0
    review_pairs = 0
    rejection_counts: Counter[str] = Counter()
    review_counts: Counter[str] = Counter()
    source_distribution: Counter[str] = Counter()
    category_distribution: Counter[str] = Counter()
    difficulty_distribution: Counter[str] = Counter()
    taxonomy_distribution: Counter[str] = Counter()

    for record in records:
        row = record["row"]
        decision = record["decision"]
        if decision.status == "filtered":
            filtered_pairs += 1
            add_distribution_counts(
                row,
                source_distribution,
                category_distribution,
                difficulty_distribution,
                taxonomy_distribution,
            )
            append_jsonl(output_paths["filtered"], quality_row(row, run_id, decision))
        elif decision.status == "review":
            review_pairs += 1
            for issue in decision.issues:
                review_counts[issue.code] += 1
            append_jsonl(output_paths["review"], quality_row(row, run_id, decision))
        else:
            rejected_pairs += 1
            for issue in decision.issues:
                rejection_counts[issue.code] += 1
            append_jsonl(
                output_paths["rejected"],
                rejection_row(
                    row,
                    run_id,
                    decision,
                    line_number=record.get("line_number"),
                ),
            )

    return {
        "filtered_pairs": filtered_pairs,
        "review_pairs": review_pairs,
        "rejected_pairs": rejected_pairs,
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "review_counts": dict(sorted(review_counts.items())),
        "source_distribution": dict(sorted(source_distribution.items())),
        "category_distribution": dict(sorted(category_distribution.items())),
        "difficulty_distribution": dict(sorted(difficulty_distribution.items())),
        "taxonomy_distribution": dict(sorted(taxonomy_distribution.items())),
    }


def quality_row(
    row: dict[str, Any],
    run_id: str,
    decision: QualityDecision,
) -> dict[str, Any]:
    output = dict(row)
    output["quality_run_id"] = run_id
    output["quality_status"] = decision.status
    output["quality_issues"] = [
        issue.model_dump(mode="json") for issue in decision.issues
    ]
    if decision.score is not None:
        output["quality_score"] = decision.score.model_dump(mode="json")
    return output


def rejection_row(
    row: dict[str, Any],
    run_id: str,
    decision: QualityDecision,
    line_number: int | None = None,
) -> dict[str, Any]:
    output = quality_row(row, run_id, decision)
    if line_number is not None:
        output["line_number"] = line_number
    return output


def add_distribution_counts(
    row: dict[str, Any],
    source_distribution: Counter[str],
    category_distribution: Counter[str],
    difficulty_distribution: Counter[str],
    taxonomy_distribution: Counter[str],
) -> None:
    source_distribution[str(row.get("source", "<missing>"))] += 1
    category_distribution[str(row.get("category", "<missing>"))] += 1
    difficulty_distribution[str(row.get("difficulty", "<missing>"))] += 1
    taxonomy_refs = row.get("taxonomy_refs", [])
    if isinstance(taxonomy_refs, list):
        for ref in taxonomy_refs:
            taxonomy_distribution[str(ref)] += 1


def write_spot_check_sample(
    records: list[dict[str, Any]],
    output_dir: Path,
    quality_config: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    spot_config = quality_config.get("manual_spot_check", {})
    sample_size = int(spot_config.get("sample_size", 100))
    seed = int(spot_config.get("seed", 1337))
    filtered_records = [
        record
        for record in records
        if record["decision"].status == "filtered"
    ]
    sampler = random.Random(seed)
    sample = list(filtered_records)
    sampler.shuffle(sample)
    sample = sample[: min(sample_size, len(sample))]

    output_path = output_dir / "manual_spot_check_sample.jsonl"
    if output_path.exists():
        output_path.unlink()
    output_path.touch()
    for index, record in enumerate(sample, 1):
        row = quality_row(record["row"], run_id, record["decision"])
        row["spot_check_id"] = f"spot-{index:03d}"
        row["spot_check_status"] = "pending"
        row["spot_check_score"] = None
        row["spot_check_notes"] = ""
        append_jsonl(output_path, row)
    return {
        "path": str(output_path),
        "requested_sample_size": sample_size,
        "actual_sample_size": len(sample),
        "seed": seed,
        "status": "pending_manual_review",
    }
