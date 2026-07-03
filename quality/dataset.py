import logging
import time
from collections import Counter, defaultdict
from typing import Any

from quality.schemas import QualityDecision, QualityIssue
from quality.validators import distinctive_tokens
from validation.reasoning import final_answer_text
from validation.taxonomy import valid_taxonomy_refs_from_config

DEFAULT_NEAR_DUPLICATE_THRESHOLD = 0.8
DEFAULT_MAX_SOURCE_SHARE = 0.25
DEFAULT_BALANCE_TOLERANCE = 0.10
logger = logging.getLogger(__name__)


def apply_dataset_gates(
    records: list[dict[str, Any]],
    quality_config: dict[str, Any],
    task_config: dict[str, Any],
) -> dict[str, Any]:
    """Apply Phase 4 gates that require a dataset-wide view."""

    stage_started = time.perf_counter()
    logger.info("Running dataset gate: near-duplicate detection")
    near_duplicate_audit = apply_near_duplicate_gate(records, quality_config)
    log_dataset_gate_complete(
        "near-duplicate detection",
        stage_started,
        f"duplicates={near_duplicate_audit['duplicate_pairs']}",
    )

    stage_started = time.perf_counter()
    logger.info("Running dataset gate: source balance")
    source_audit = apply_source_balance_gate(records, quality_config)
    log_dataset_gate_complete(
        "source balance",
        stage_started,
        f"overrepresented={len(source_audit.get('overrepresented', {}))}",
    )

    stage_started = time.perf_counter()
    logger.info("Running dataset audit: category balance")
    category_audit = distribution_audit(
        records,
        field="category",
        targets=task_config.get("distribution", {}).get("category_targets", {}),
        tolerance=balance_tolerance(quality_config),
    )
    log_dataset_gate_complete("category balance", stage_started)

    stage_started = time.perf_counter()
    logger.info("Running dataset audit: difficulty balance")
    difficulty_audit = distribution_audit(
        records,
        field="difficulty",
        targets=task_config.get("distribution", {}).get("difficulty_targets", {}),
        tolerance=balance_tolerance(quality_config),
    )
    log_dataset_gate_complete("difficulty balance", stage_started)

    stage_started = time.perf_counter()
    logger.info("Running dataset audit: taxonomy coverage")
    taxonomy_audit = taxonomy_coverage_audit(records, quality_config)
    log_dataset_gate_complete(
        "taxonomy coverage",
        stage_started,
        (
            f"covered={taxonomy_audit['covered_ref_count']}/"
            f"{taxonomy_audit['configured_ref_count']}"
        ),
    )

    return {
        "near_duplicates": near_duplicate_audit,
        "source_balance": source_audit,
        "category_balance": category_audit,
        "difficulty_balance": difficulty_audit,
        "taxonomy_coverage": taxonomy_audit,
    }


def log_dataset_gate_complete(stage: str, started_at: float, detail: str | None = None) -> None:
    elapsed = time.perf_counter() - started_at
    if detail:
        logger.info("Completed dataset gate: %s in %.1fs (%s)", stage, elapsed, detail)
    else:
        logger.info("Completed dataset gate: %s in %.1fs", stage, elapsed)


def apply_near_duplicate_gate(
    records: list[dict[str, Any]],
    quality_config: dict[str, Any],
) -> dict[str, Any]:
    threshold = float(
        quality_config.get("deduplication", {}).get(
            "jaccard_threshold", DEFAULT_NEAR_DUPLICATE_THRESHOLD
        )
    )
    eligible_indices = [
        index
        for index, record in enumerate(records)
        if decision(record).status != "rejected"
    ]
    token_sets = {
        index: record_tokens(records[index])
        for index in eligible_indices
    }
    ordered = sorted(
        eligible_indices,
        key=lambda index: (
            decision(records[index]).score.total
            if decision(records[index]).score is not None
            else 0.0
        ),
        reverse=True,
    )
    kept: set[int] = set()
    inverted_index: dict[str, list[int]] = defaultdict(list)
    duplicate_pairs: list[dict[str, Any]] = []

    for index in ordered:
        tokens = token_sets[index]
        if len(tokens) < 8:
            kept.add(index)
            for token in tokens:
                inverted_index[token].append(index)
            continue

        overlap_counts: Counter[int] = Counter()
        for token in tokens:
            overlap_counts.update(inverted_index.get(token, []))

        duplicate_of: int | None = None
        duplicate_score = 0.0
        for other, overlap in overlap_counts.most_common():
            other_tokens = token_sets[other]
            union_size = len(tokens | other_tokens)
            if not union_size:
                continue
            jaccard = overlap / union_size
            if jaccard >= threshold:
                duplicate_of = other
                duplicate_score = jaccard
                break

        if duplicate_of is not None:
            add_issue(
                records[index],
                QualityIssue(
                    code="duplicate_or_near_duplicate",
                    severity="reject",
                    message=(
                        "Near-duplicate training pair; kept line "
                        f"{records[duplicate_of].get('line_number')} "
                        f"with Jaccard similarity {duplicate_score:.3f}"
                    ),
                ),
            )
            duplicate_pairs.append(
                {
                    "line_number": records[index].get("line_number"),
                    "duplicate_of_line": records[duplicate_of].get("line_number"),
                    "jaccard": round(duplicate_score, 3),
                }
            )
            continue

        kept.add(index)
        for token in tokens:
            inverted_index[token].append(index)

    return {
        "threshold": threshold,
        "eligible_pairs": len(eligible_indices),
        "duplicate_pairs": len(duplicate_pairs),
        "examples": duplicate_pairs[:25],
    }


def apply_source_balance_gate(
    records: list[dict[str, Any]],
    quality_config: dict[str, Any],
) -> dict[str, Any]:
    max_share = float(
        quality_config.get("balance", {}).get(
            "max_source_share", DEFAULT_MAX_SOURCE_SHARE
        )
    )
    filtered_indices = [
        index
        for index, record in enumerate(records)
        if decision(record).status == "filtered"
    ]
    source_counts = Counter(str(records[index]["row"].get("source", "<missing>")) for index in filtered_indices)
    total = len(filtered_indices)
    if total == 0 or len(source_counts) <= 1:
        return {
            "max_source_share": max_share,
            "total_filtered": total,
            "source_distribution": dict(sorted(source_counts.items())),
            "overrepresented": {},
        }

    max_allowed = max(1, int(total * max_share))
    overrepresented: dict[str, int] = {}
    for source, count in source_counts.items():
        if count <= max_allowed:
            continue
        surplus = count - max_allowed
        overrepresented[source] = surplus
        source_indices = [
            index
            for index in filtered_indices
            if str(records[index]["row"].get("source", "<missing>")) == source
        ]
        source_indices.sort(key=lambda index: score_total(records[index]))
        for index in source_indices[:surplus]:
            add_issue(
                records[index],
                QualityIssue(
                    code="source_overrepresented",
                    severity="review",
                    message=(
                        f"Source {source} exceeds max filtered share "
                        f"{max_share:.2f}; row moved to review for balance"
                    ),
                ),
            )

    final_counts = Counter(
        str(record["row"].get("source", "<missing>"))
        for record in records
        if decision(record).status == "filtered"
    )
    return {
        "max_source_share": max_share,
        "initial_filtered": total,
        "final_filtered": sum(final_counts.values()),
        "initial_source_distribution": dict(sorted(source_counts.items())),
        "final_source_distribution": dict(sorted(final_counts.items())),
        "overrepresented": dict(sorted(overrepresented.items())),
    }


def distribution_audit(
    records: list[dict[str, Any]],
    field: str,
    targets: dict[str, float],
    tolerance: float,
) -> dict[str, Any]:
    filtered = [
        record["row"]
        for record in records
        if decision(record).status == "filtered"
    ]
    counts = Counter(str(row.get(field, "<missing>")) for row in filtered)
    total = sum(counts.values())
    values: dict[str, Any] = {}
    for name in sorted(set(counts) | set(targets)):
        actual = counts[name] / total if total else 0.0
        target = float(targets.get(name, 0.0))
        delta = actual - target
        values[name] = {
            "count": counts[name],
            "actual": round(actual, 4),
            "target": round(target, 4),
            "delta": round(delta, 4),
            "within_tolerance": abs(delta) <= tolerance,
        }
    return {
        "total_filtered": total,
        "tolerance": tolerance,
        "values": values,
    }


def taxonomy_coverage_audit(
    records: list[dict[str, Any]],
    quality_config: dict[str, Any],
) -> dict[str, Any]:
    configured_refs = sorted(valid_taxonomy_refs_from_config(quality_config))
    counts: Counter[str] = Counter()
    for record in records:
        if decision(record).status != "filtered":
            continue
        taxonomy_refs = record["row"].get("taxonomy_refs", [])
        if isinstance(taxonomy_refs, list):
            counts.update(str(ref) for ref in taxonomy_refs)

    covered = sorted(ref for ref in configured_refs if counts[ref] > 0)
    missing = sorted(ref for ref in configured_refs if counts[ref] == 0)
    total_filtered = sum(
        1 for record in records if decision(record).status == "filtered"
    )
    density = {
        ref: taxonomy_density(counts[ref], total_filtered)
        for ref in configured_refs
    }
    domain_summary: dict[str, dict[str, Any]] = {}
    for domain, config in quality_config.get("taxonomy", {}).get("domains", {}).items():
        ids = [str(value) for value in config.get("ids", [])]
        covered_ids = [ref for ref in ids if counts[ref] > 0]
        domain_summary[str(domain)] = {
            "configured": len(ids),
            "covered": len(covered_ids),
            "missing": sorted(set(ids) - set(covered_ids)),
            "counts": {ref: counts[ref] for ref in ids if counts[ref] > 0},
        }

    return {
        "configured_ref_count": len(configured_refs),
        "covered_ref_count": len(covered),
        "missing_ref_count": len(missing),
        "covered_refs": covered,
        "missing_refs": missing,
        "counts": dict(sorted(counts.items())),
        "density": density,
        "domain_summary": domain_summary,
    }


def taxonomy_density(count: int, total_filtered: int) -> str:
    if count == 0 or total_filtered == 0:
        return "absent"
    share = count / total_filtered
    if count < 5 or share < 0.005:
        return "thin"
    if count < 25 or share < 0.025:
        return "moderate"
    return "dense"


def record_tokens(record: dict[str, Any]) -> set[str]:
    row = record["row"]
    text = "\n".join(
        [
            str(row.get("instruction", "")),
            final_answer_text(str(row.get("response", ""))),
        ]
    )
    return distinctive_tokens(text)


def add_issue(record: dict[str, Any], issue: QualityIssue) -> None:
    current = decision(record)
    current.issues.append(issue)
    if any(item.severity == "reject" for item in current.issues):
        current.status = "rejected"
    elif current.issues:
        current.status = "review"


def decision(record: dict[str, Any]) -> QualityDecision:
    return record["decision"]


def score_total(record: dict[str, Any]) -> float:
    score = decision(record).score
    if score is None:
        return 0.0
    return score.total


def balance_tolerance(quality_config: dict[str, Any]) -> float:
    return float(
        quality_config.get("balance", {}).get(
            "distribution_tolerance", DEFAULT_BALANCE_TOLERANCE
        )
    )
