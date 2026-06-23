from collections import defaultdict

from collectors.schemas import RawDocument
from synthesizers.source_profiles import DEFAULT_PILOT_TARGETS


def _sort_key(doc: RawDocument) -> tuple[int, str]:
    # Prefer richer docs in the pilot without making the sample fully
    # longest-document-biased. The doc_id tie-breaker keeps it deterministic.
    richness_bucket = min(doc.word_count // 500, 10)
    return (-richness_bucket, doc.doc_id)


def sample_pilot_documents(
    docs: list[RawDocument],
    targets: dict[str, int] | None = None,
) -> list[RawDocument]:
    targets = targets or DEFAULT_PILOT_TARGETS
    by_source: dict[str, list[RawDocument]] = defaultdict(list)
    seen_doc_ids: set[str] = set()

    for doc in docs:
        if doc.doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc.doc_id)
        by_source[doc.source].append(doc)

    selected: list[RawDocument] = []
    for source, limit in targets.items():
        source_docs = sorted(by_source.get(source, []), key=_sort_key)
        selected.extend(source_docs[:limit])

    return selected

