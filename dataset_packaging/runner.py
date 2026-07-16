import logging
import random
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dataset_packaging.schemas import PackagedSplitSummary, PackagingManifest
from utils.io import (load_json, load_jsonl_rows, load_yaml,
                      log_stage_complete, write_json, write_jsonl)
from validation.reasoning import final_answer_text

logger = logging.getLogger(__name__)

SPLIT_NAMES = ("train", "validation", "test")
GENERAL_KNOWLEDGE_ANNOTATION = "[GENERAL KNOWLEDGE]"
CANONICAL_REASONING_START = "<reasoning>"
CANONICAL_REASONING_END = "</reasoning>"
GLM_REASONING_START = "<think>"
GLM_REASONING_END = "</think>"


def run_packaging(args) -> int:
    overall_started = time.perf_counter()
    config_path = Path(args.config)
    config = load_yaml(config_path)

    quality_dir = Path(args.quality_dir)
    output_dir = Path(args.output_dir)

    logger.info(
        "Starting Phase 5 packaging: quality_dir=%s output_dir=%s",
        quality_dir,
        output_dir,
    )

    stage_started = time.perf_counter()
    input_paths = resolve_input_paths(quality_dir)
    output_paths = resolve_output_paths(output_dir)
    log_stage_complete(logger, "resolved packaging paths", stage_started)

    stage_started = time.perf_counter()
    quality_manifest = load_json(input_paths["quality_manifest"], logger)
    filtered_rows = load_jsonl_rows(input_paths["filtered"])
    review_rows = load_jsonl_rows(input_paths["review"])
    style_config = config.get("response_style", {})
    package_rows = [
        (row, str(style_config.get("filtered")))
        for row in filtered_rows
    ] + [
        (row, str(style_config.get("review")))
        for row in review_rows
    ]
    log_stage_complete(
        logger,
        "loaded Phase 4 rows",
        stage_started,
        f"filtered={len(filtered_rows)} review={len(review_rows)}",
    )

    created_at = datetime.now(timezone.utc)
    run_id = f"package-{created_at.strftime('%Y%m%dT%H%M%SZ')}"

    stage_started = time.perf_counter()
    packaged_records = [
        build_packaged_record(row, index, config, response_style)
        for index, (row, response_style) in enumerate(package_rows, 1)
    ]
    validate_packaged_records(packaged_records, config)
    log_stage_complete(
        logger,
        "built packaged records",
        stage_started,
        f"records={len(packaged_records)}",
    )

    stage_started = time.perf_counter()
    split_config = config.get("split", {})
    split_rows = split_records_by_source_doc(packaged_records, split_config)
    log_stage_complete(
        logger,
        "split packaged records",
        stage_started,
        " ".join(f"{name}={len(rows)}" for name, rows in split_rows.items()),
    )

    stage_started = time.perf_counter()
    prepare_output_dir(output_dir, output_paths)
    write_packaged_splits(split_rows, output_paths)
    log_stage_complete(logger, "wrote packaged split JSONL files", stage_started)

    stage_started = time.perf_counter()
    manifest = build_packaging_manifest(
        run_id=run_id,
        created_at=created_at,
        config_path=config_path,
        quality_dir=quality_dir,
        output_dir=output_dir,
        output_paths=output_paths,
        packaged_records=packaged_records,
        split_rows=split_rows,
        split_config=split_config,
        quality_manifest=quality_manifest,
    )
    write_json(output_paths["manifest"], manifest.model_dump(mode="json"))
    log_stage_complete(
        logger,
        "wrote packaging manifest",
        stage_started,
        f"path={output_paths['manifest']}",
    )

    log_stage_complete(logger, "completed Phase 5 packaging", overall_started)
    print(
        "Packaging complete: "
        f"records={len(packaged_records)}, "
        f"train={len(split_rows['train'])}, "
        f"validation={len(split_rows['validation'])}, "
        f"test={len(split_rows['test'])}"
    )
    return 0


def resolve_input_paths(quality_dir: Path) -> dict[str, Path]:
    return {
        "filtered": quality_dir / "filtered.jsonl",
        "review": quality_dir / "review_queue.jsonl",
        "quality_manifest": quality_dir / "quality_manifest.json"
    }


def resolve_output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "train": output_dir / "train.jsonl",
        "validation": output_dir / "validation.jsonl",
        "test": output_dir / "test.jsonl",
        "manifest": output_dir / "packaging_manifest.json"
    }


def prepare_output_dir(output_dir: Path, output_paths: dict[str, Path]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_paths.values():
        if path.exists():
            path.unlink()


def build_packaged_record(
    row: dict[str, Any],
    index: int,
    config: dict[str, Any],
    reasoning_style: str,
) -> dict[str, Any]:
    content = format_content_by_reasoning_style(
        str(row.get("response", "")),
        reasoning_style,
    )
    content, model_transforms = apply_model_specific_transforms(
        content,
        config.get("model_transform", {}),
    )

    messages = []
    format_config = config.get("format", {})
    if bool(format_config.get("include_system_message", True)):
        messages.append(
            {
                "role": "system",
                "content": str(format_config.get("system_message")).strip(),
            }
        )
    messages.extend(
        [
            {"role": "user", "content": str(row.get("instruction", "")).strip()},
            {"role": "assistant", "content": content},
        ]
    )

    source_doc_id = str(row.get("source_doc_id", "unknown"))
    prompt_id = str(row.get("prompt_id", "prompt"))
    pair_index = str(row.get("pair_index", 0))

    return {
        "id": f"dfir-{index:06d}",
        "messages": messages,
        "metadata": {
            "source_doc_id": source_doc_id,
            "source": row.get("source"),
            "category": row.get("category"),
            "difficulty": row.get("difficulty"),
            "confidence": row.get("confidence"),
            "taxonomy_refs": row.get("taxonomy_refs", []),
            "mitre_techniques": row.get("mitre_techniques", []),
            "atlas_techniques": row.get("atlas_techniques", []),
            "tools_referenced": row.get("tools_referenced", []),
            "grounding": row.get("grounding"),
            "quality_status": row.get("quality_status"),
            "quality_issues": row.get("quality_issues", []),
            "quality_score": row.get("quality_score"),
            "reasoning_style": reasoning_style,
            "response_transform": (
                "strip_reasoning_block" if reasoning_style == "direct" else "none"
            ),
            "model_transforms": model_transforms,
            "run_id": row.get("run_id"),
            "prompt_id": prompt_id,
            "prompt_hash": row.get("prompt_hash"),
            "pair_index": row.get("pair_index"),
            "model": row.get("model"),
            "generated_at": row.get("generated_at"),
            "quality_run_id": row.get("quality_run_id"),
            "source_pair_key": f"{prompt_id}:{pair_index}",
        },
    }


def format_content_by_reasoning_style(response: str, reasoning_style: str) -> str:
    if reasoning_style != "direct":
        return response.strip()
    direct_answer = final_answer_text(response)
    return (direct_answer or response).strip()


def apply_model_specific_transforms(
    content: str,
    transform_config: dict[str, Any],
) -> tuple[str, list[str]]:
    """Create a model-specific response view without mutating canonical data."""

    transformed = content
    applied: list[str] = []

    if bool(transform_config.get("remove_general_knowledge_annotations", False)):
        if GENERAL_KNOWLEDGE_ANNOTATION in transformed:
            transformed = transformed.replace(GENERAL_KNOWLEDGE_ANNOTATION, "")
            applied.append("remove_general_knowledge_annotations")

    if bool(transform_config.get("glm_reasoning_tags", False)):
        if (
            CANONICAL_REASONING_START in transformed
            or CANONICAL_REASONING_END in transformed
        ):
            transformed = transformed.replace(
                CANONICAL_REASONING_START,
                GLM_REASONING_START,
            ).replace(
                CANONICAL_REASONING_END,
                GLM_REASONING_END,
            )
            applied.append("canonical_reasoning_to_glm_think")

    return normalize_transformed_content(transformed), applied


def normalize_transformed_content(content: str) -> str:
    lines = [re.sub(r"[ \t]+$", "", line) for line in content.splitlines()]
    return "\n".join(lines).strip()


def validate_packaged_records(
    records: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    preflight_config = config.get("preflight", {})
    if not bool(preflight_config.get("enabled", False)):
        return

    issues: list[str] = []
    for record in records:
        record_id = str(record.get("id", "<unknown>"))
        messages = record.get("messages", [])
        assistant_content = ""
        if messages and isinstance(messages[-1], dict):
            assistant_content = str(messages[-1].get("content", "")).strip()

        if not assistant_content:
            issues.append(f"{record_id}: empty assistant response")
        if GENERAL_KNOWLEDGE_ANNOTATION in assistant_content:
            issues.append(f"{record_id}: retained grounding annotation")
        if (
            CANONICAL_REASONING_START in assistant_content
            or CANONICAL_REASONING_END in assistant_content
        ):
            issues.append(f"{record_id}: retained canonical reasoning tag")
        if assistant_content.count(GLM_REASONING_START) != assistant_content.count(
            GLM_REASONING_END
        ):
            issues.append(f"{record_id}: unbalanced GLM reasoning tags")

        if len(issues) >= 20:
            break

    if issues:
        raise ValueError(
            "Packaged-record preflight failed:\n- " + "\n- ".join(issues)
        )


def split_records_by_source_doc(
    records: list[dict[str, Any]],
    split_config: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        source_doc_id = str(record["metadata"].get("source_doc_id", "unknown"))
        grouped[source_doc_id].append(record)

    groups = list(grouped.values())
    random.Random(int(split_config.get("seed", 1337))).shuffle(groups)
    groups.sort(key=len, reverse=True)

    total = len(records)
    targets = split_targets(total, split_config)
    split_rows = {name: [] for name in SPLIT_NAMES}

    for group in groups:
        split_name = choose_split(split_rows, targets)
        split_rows[split_name].extend(group)

    return split_rows


def split_targets(total: int, split_config: dict[str, Any]) -> dict[str, int]:
    train = int(round(total * float(split_config.get("train", 0.8))))
    validation = int(round(total * float(split_config.get("validation", 0.1))))
    test = total - train - validation
    return {"train": train, "validation": validation, "test": test}


def choose_split(
    split_rows: dict[str, list[dict[str, Any]]],
    targets: dict[str, int],
) -> str:
    def remaining_ratio(name: str) -> tuple[float, int]:
        target = max(targets[name], 1)
        remaining = targets[name] - len(split_rows[name])
        return (remaining / target, remaining)

    return max(SPLIT_NAMES, key=remaining_ratio)


def write_packaged_splits(
    split_rows: dict[str, list[dict[str, Any]]],
    output_paths: dict[str, Path],
) -> None:
    for split_name in SPLIT_NAMES:
        write_jsonl(output_paths[split_name], split_rows[split_name])


def build_packaging_manifest(
    *,
    run_id: str,
    created_at: datetime,
    config_path: Path,
    quality_dir: Path,
    output_dir: Path,
    output_paths: dict[str, Path],
    packaged_records: list[dict[str, Any]],
    split_rows: dict[str, list[dict[str, Any]]],
    split_config: dict[str, Any],
    quality_manifest: dict[str, Any],
) -> PackagingManifest:
    splits = {
        name: PackagedSplitSummary(
            path=str(output_paths[name]),
            records=len(rows),
            source_doc_ids=len(source_doc_ids(rows)),
        )
        for name, rows in split_rows.items()
    }
    overlap = split_source_doc_overlap(split_rows)

    return PackagingManifest(
        run_id=run_id,
        created_at=created_at,
        config_path=str(config_path),
        input_quality_dir=str(quality_dir),
        quality_run_id=quality_manifest.get("run_id"),
        output_dir=str(output_dir),
        packaged_pairs=len(packaged_records),
        response_style=response_style_summary(packaged_records),
        split_config={
            "train": split_config.get("train", 0.8),
            "validation": split_config.get("validation", 0.1),
            "test": split_config.get("test", 0.1),
            "seed": split_config.get("seed", 1337),
            "group_by": split_config.get("group_by", "source_doc_id"),
        },
        splits=splits,
        source_doc_overlap=overlap,
    )


def response_style_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for record in records:
        style = record.get("metadata", {}).get("reasoning_style", "<missing>")
        counter[str(style)] += 1

    counts = dict(sorted(counter.items()))
    total = max(len(records), 1)
    return {
        "counts": counts,
        "fractions": {
            key: round(value / total, 4)
            for key, value in sorted(counts.items())
        },
    }


def source_doc_ids(records: Iterable[dict[str, Any]]) -> set[str]:
    return {
        str(record.get("metadata", {}).get("source_doc_id", "unknown"))
        for record in records
    }


def split_source_doc_overlap(
    split_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    ids_by_split = {
        name: source_doc_ids(rows)
        for name, rows in split_rows.items()
    }
    overlap: dict[str, list[str]] = {}
    for index, left in enumerate(SPLIT_NAMES):
        for right in SPLIT_NAMES[index + 1:]:
            key = f"{left}_vs_{right}"
            overlap[key] = sorted(ids_by_split[left] & ids_by_split[right])
    return overlap
