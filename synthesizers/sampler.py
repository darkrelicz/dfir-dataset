from collections import defaultdict

from collectors.schemas import RawDocument
from synthesizers.source_profiles import DEFAULT_PILOT_TARGETS


def _richness_bucket(doc: RawDocument) -> int:
    if doc.word_count < 250:
        return 0
    if doc.word_count < 750:
        return 1
    if doc.word_count < 2000:
        return 2
    return 3


def _sample_source_documents(docs: list[RawDocument], limit: int) -> list[RawDocument]:
    buckets: dict[tuple[int, str], list[RawDocument]] = defaultdict(list)
    for doc in docs:
        buckets[(_richness_bucket(doc), doc.content_type)].append(doc)

    for bucket_docs in buckets.values():
        bucket_docs.sort(key=lambda doc: doc.doc_id)

    bucket_keys = sorted(buckets)
    selected: list[RawDocument] = []
    while len(selected) < limit:
        selected_this_round = False
        for key in bucket_keys:
            if not buckets[key]:
                continue
            selected.append(buckets[key].pop(0))
            selected_this_round = True
            if len(selected) == limit:
                break
        if not selected_this_round:
            break

    return selected


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
        selected.extend(_sample_source_documents(by_source.get(source, []), limit))

    return selected
