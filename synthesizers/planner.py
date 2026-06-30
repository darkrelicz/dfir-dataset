from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from collectors.schemas import RawDocument
from synthesizers.io import load_raw_documents
from synthesizers.prompt_builder import PromptBuilder
from synthesizers.prompt_policy import DIFFICULTY_ORDER
from synthesizers.sampler import sample_pilot_documents, sample_subset_documents
from synthesizers.schemas import Difficulty, PromptRecord
from utils.text import stable_index


@dataclass(frozen=True)
class PromptPlan:
    docs: list[RawDocument]
    prompt_records: list[PromptRecord]


def select_documents(
    raw_dir: Path,
    mode: str,
    limit: int | None = None,
) -> list[RawDocument]:
    docs = load_raw_documents(raw_dir)

    if mode == "pilot":
        docs = sample_pilot_documents(docs)
    elif mode == "subset":
        docs = sample_subset_documents(docs)
    else:
        docs = sorted(docs, key=lambda doc: (doc.source, doc.doc_id))

    if limit is not None:
        docs = docs[:limit]

    return docs


def category_targets_from_task_config(task_config: dict) -> dict[str, float]:
    distribution = task_config.get("distribution")
    if not isinstance(distribution, dict):
        raise ValueError("configs/task_categories.yaml must define distribution")

    raw_targets = distribution.get("category_targets")
    if not isinstance(raw_targets, dict):
        raise ValueError("configs/task_categories.yaml must define distribution.category_targets")

    targets: dict[str, float] = {}
    for category, weight in raw_targets.items():
        try:
            parsed_weight = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"category_targets.{category} must be numeric") from exc
        if parsed_weight < 0:
            raise ValueError(f"category_targets.{category} must be non-negative")
        if parsed_weight > 0:
            targets[str(category)] = parsed_weight
    if not targets:
        raise ValueError("category_targets must contain at least one positive weight")
    return targets


def assign_categories(
    docs: list[RawDocument],
    builder: PromptBuilder,
    task_config: dict,
) -> dict[str, str]:
    targets = category_targets_from_task_config(task_config)

    pair_weights = {doc.doc_id: builder.pairs_for_doc(doc) for doc in docs}
    total_pairs = sum(pair_weights.values())
    target_total = sum(targets.values())
    target_pairs = {
        category: total_pairs * (weight / target_total)
        for category, weight in targets.items()
    }

    assigned_pairs: Counter[str] = Counter()
    assignments: dict[str, str] = {}
    assignment_order = sorted(
        docs,
        key=lambda doc: (
            len(builder.categories_for_doc(doc)),
            stable_index(doc.doc_id, 1_000_000),
            doc.source,
            doc.doc_id,
        ),
    )

    for doc in assignment_order:
        allowed_categories = [
            category
            for category in builder.categories_for_doc(doc)
            if category in target_pairs
        ]
        if not allowed_categories:
            allowed_categories = list(builder.categories_for_doc(doc))

        def score(category: str) -> tuple[float, int]:
            deficit = target_pairs.get(category, 0.0) - assigned_pairs[category]
            jitter = stable_index(f"{doc.doc_id}:{category}", 10_000)
            return deficit, -jitter

        category = max(allowed_categories, key=score)
        assignments[doc.doc_id] = category
        assigned_pairs[category] += pair_weights[doc.doc_id]

    return assignments


def assign_difficulties(docs: list[RawDocument], builder: PromptBuilder) -> dict[str, Difficulty]:
    weights = builder.policy.difficulty_targets
    total = sum(weights.values())
    assignments: dict[str, Difficulty] = {}

    for doc in docs:
        bucket = stable_index(doc.doc_id, 10_000) / 10_000
        cumulative = 0.0
        for label in DIFFICULTY_ORDER:
            cumulative += weights[label] / total
            if bucket < cumulative:
                assignments[doc.doc_id] = label
                break
        else:
            assignments[doc.doc_id] = DIFFICULTY_ORDER[-1]

    return assignments


def build_prompt_plan(
    raw_dir: Path,
    synthesis_config: dict,
    task_config: dict,
    mode: str,
    limit: int | None = None,
) -> PromptPlan:
    docs = select_documents(raw_dir, mode, limit=limit)
    builder = PromptBuilder(synthesis_config, task_config)
    category_assignments = assign_categories(docs, builder, task_config)
    difficulty_assignments = assign_difficulties(docs, builder)
    prompt_records = [
        builder.build(
            doc,
            category=category_assignments[doc.doc_id],
            difficulty=difficulty_assignments[doc.doc_id],
        )
        for doc in docs
    ]
    return PromptPlan(docs=docs, prompt_records=prompt_records)


def pair_count_summary(prompt_records: list[PromptRecord], field: str) -> str:
    counts: Counter[str] = Counter()
    for record in prompt_records:
        counts[str(getattr(record, field))] += record.pairs_requested
    return ", ".join(f"{name}={counts[name]}" for name in sorted(counts))
