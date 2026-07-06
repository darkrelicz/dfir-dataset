import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from collectors.schemas import RawDocument
from quality.references import QualityReferences, normalize_tool_name
from quality.schemas import (QualityCandidate, QualityDecision, QualityIssue,
                             QualityScore)
from validation.grounding import grounding_mismatch_message
from validation.indicators import invented_indicators, source_document_text
from validation.mappings import (ATLAS_ID_ANYWHERE_RE, ATLAS_ID_RE,
                                 MITRE_ID_ANYWHERE_RE, MITRE_ID_RE,
                                 normalized_mapping_id)
from validation.reasoning import (ReasoningValidationOptions, caveat_texts,
                                  final_answer_text,
                                  validate_reasoning_structure)

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.\\/-]{2,}")
MAX_RESPONSE_WORDS = 1200
MIN_FINAL_ANSWER_WORDS = 25
STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "been",
    "before",
    "being",
    "between",
    "could",
    "does",
    "from",
    "have",
    "into",
    "more",
    "should",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "when",
    "where",
    "which",
    "will",
    "with",
    "would",
    "your",
}


def validate_quality_row(
    row: Mapping[str, object],
    raw_docs_by_id: Mapping[str, RawDocument],
    references: QualityReferences,
    valid_categories: set[str],
    quality_config: Mapping[str, Any] | None = None,
) -> QualityDecision:
    """Run Phase 4 row-level gates without calling Phase 3 output validators."""

    issues: list[QualityIssue] = []
    try:
        candidate = QualityCandidate.model_validate(row)
    except ValidationError as exc:
        return QualityDecision(
            status="rejected",
            issues=[
                QualityIssue(
                    code="schema_invalid",
                    severity="reject",
                    message=f"QualityCandidate validation failed: {exc}",
                )
            ],
        )

    source_doc = raw_docs_by_id.get(candidate.source_doc_id)
    if source_doc is None:
        return QualityDecision(
            status="rejected",
            issues=[
                QualityIssue(
                    code="source_missing",
                    severity="reject",
                    message=f"Unknown source_doc_id: {candidate.source_doc_id}",
                )
            ],
        )

    if candidate.source != source_doc.source:
        issues.append(
            QualityIssue(
                code="source_mismatch",
                severity="reject",
                message=f"source mismatch: {candidate.source} != {source_doc.source}",
            )
        )

    if candidate.category not in valid_categories:
        issues.append(
            QualityIssue(
                code="category_invalid",
                severity="reject",
                message=f"Invalid category: {candidate.category}",
            )
        )

    issues.extend(validate_taxonomy(candidate, references.taxonomy_refs))
    issues.extend(validate_mapping_ids(candidate, references))
    issues.extend(validate_tools(candidate, source_doc, references))
    issues.extend(validate_reasoning(candidate.response, quality_config or {}))
    issues.extend(validate_grounding(candidate))
    issues.extend(validate_source_grounding(candidate, source_doc))

    score = score_candidate(candidate, source_doc, issues, quality_config or {})

    if any(issue.severity == "reject" for issue in issues):
        return QualityDecision(status="rejected", issues=issues, score=score)
    if issues:
        return QualityDecision(status="review", issues=issues, score=score)
    return QualityDecision(status="filtered", score=score)


def validate_taxonomy(
    candidate: QualityCandidate,
    valid_taxonomy_refs: set[str],
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if not candidate.taxonomy_refs:
        issues.append(
            QualityIssue(
                code="taxonomy_invalid",
                severity="reject",
                message="taxonomy_refs must include at least one taxonomy ID",
            )
        )
    invalid_refs = sorted(set(candidate.taxonomy_refs) - valid_taxonomy_refs)
    if invalid_refs:
        issues.append(
            QualityIssue(
                code="taxonomy_invalid",
                severity="reject",
                message=f"Invalid taxonomy_refs: {invalid_refs}",
            )
        )
    return issues


def validate_mapping_ids(
    candidate: QualityCandidate,
    references: QualityReferences,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    invalid_mitre = [
        value for value in candidate.mitre_techniques if not MITRE_ID_RE.match(value)
    ]
    invalid_atlas = [
        value for value in candidate.atlas_techniques if not ATLAS_ID_RE.match(value)
    ]
    if invalid_mitre:
        issues.append(
            QualityIssue(
                code="attack_id_invalid",
                severity="reject",
                message=f"Invalid MITRE technique IDs: {invalid_mitre}",
            )
        )
    unknown_mitre = sorted(
        value
        for value in candidate.mitre_techniques
        if MITRE_ID_RE.match(value)
        and normalized_mapping_id(value) not in references.attack_ids
    )
    if unknown_mitre:
        issues.append(
            QualityIssue(
                code="attack_id_invalid",
                severity="reject",
                message=(
                    "MITRE technique ID(s) are not present in local ATT&CK "
                    f"reference corpus: {unknown_mitre}"
                ),
            )
        )
    if invalid_atlas:
        issues.append(
            QualityIssue(
                code="atlas_id_invalid",
                severity="reject",
                message=f"Invalid ATLAS technique IDs: {invalid_atlas}",
            )
        )
    unknown_atlas = sorted(
        value
        for value in candidate.atlas_techniques
        if ATLAS_ID_RE.match(value)
        and normalized_mapping_id(value) not in references.atlas_ids
    )
    if unknown_atlas:
        issues.append(
            QualityIssue(
                code="atlas_id_invalid",
                severity="reject",
                message=(
                    "ATLAS technique ID(s) are not present in local ATLAS "
                    f"reference corpus: {unknown_atlas}"
                ),
            )
        )

    response_ids = set(MITRE_ID_ANYWHERE_RE.findall(candidate.response))
    array_ids = set(candidate.mitre_techniques)
    untracked_response_ids = sorted(response_ids - array_ids)
    if untracked_response_ids:
        issues.append(
            QualityIssue(
                code="mapping_inconsistency",
                severity="review",
                message=(
                    "Response mentions MITRE technique ID(s) absent from metadata: "
                    f"{untracked_response_ids}"
                ),
            )
        )

    atlas_response_ids = set(ATLAS_ID_ANYWHERE_RE.findall(candidate.response))
    atlas_array_ids = set(candidate.atlas_techniques)
    untracked_atlas_ids = sorted(atlas_response_ids - atlas_array_ids)
    if untracked_atlas_ids:
        issues.append(
            QualityIssue(
                code="mapping_inconsistency",
                severity="review",
                message=(
                    "Response mentions ATLAS technique ID(s) absent from metadata: "
                    f"{untracked_atlas_ids}"
                ),
            )
        )
    return issues


def validate_tools(
    candidate: QualityCandidate,
    source_doc: RawDocument,
    references: QualityReferences,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    source_lower = source_corpus_text(source_doc).lower()
    unknown_tools = []
    for tool in candidate.tools_referenced:
        normalized = normalize_tool_name(tool)
        if not normalized:
            continue
        if normalized in references.tool_allowlist:
            continue
        if tool.lower() in source_lower or normalized in source_lower:
            continue
        unknown_tools.append(tool)

    if unknown_tools:
        issues.append(
            QualityIssue(
                code="tool_name_unknown",
                severity="review",
                message=(
                    "tools_referenced contains name(s) absent from the "
                    f"tool allowlist and source text: {sorted(set(unknown_tools))}"
                ),
            )
        )
    return issues


def validate_reasoning(
    response: str,
    quality_config: Mapping[str, Any] | None = None,
) -> list[QualityIssue]:
    reasoning_config = (quality_config or {}).get("reasoning", {})
    min_steps = int(reasoning_config.get("min_steps", 4))
    max_steps = int(reasoning_config.get("max_steps", 24))
    issues = validate_reasoning_structure(
        response,
        ReasoningValidationOptions(
            require_start_on_own_line=True,
            require_tags_on_own_line=True,
            require_known_line_format=True,
            require_conclusion_confidence=True,
            require_final_answer=True,
            min_steps=min_steps,
            max_steps=max_steps,
        ),
    )
    return [
        QualityIssue(
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
        )
        for issue in issues
    ]


def validate_grounding(candidate: QualityCandidate) -> list[QualityIssue]:
    message = grounding_mismatch_message(candidate.grounding, candidate.response)
    if message:
        return [
            QualityIssue(
                code="grounding_mismatch",
                severity="reject",
                message=message,
            )
        ]
    return []


def validate_source_grounding(
    candidate: QualityCandidate,
    source_doc: RawDocument,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []

    invented = find_invented_indicators(candidate, source_doc)
    if invented:
        severity = "review" if candidate.grounding == "source_plus_general" else "reject"
        issues.append(
            QualityIssue(
                code="invented_indicator",
                severity=severity,
                message=f"Concrete indicators not present in source document: {invented}",
            )
        )

    return issues


def score_candidate(
    candidate: QualityCandidate,
    source_doc: RawDocument,
    issues: list[QualityIssue],
    quality_config: Mapping[str, Any],
) -> QualityScore:
    hard_codes = {issue.code for issue in issues if issue.severity == "reject"}

    factual_accuracy = 5.0
    if "invented_indicator" in hard_codes:
        factual_accuracy = 1.0
    elif "grounding_mismatch" in hard_codes:
        factual_accuracy = 2.0

    reasoning_quality = 5.0
    if "reasoning_links_invalid" in hard_codes:
        reasoning_quality = 1.0

    operational_relevance = 5.0 if has_operational_signal(candidate) else 2.5
    specificity = 5.0 if has_source_specific_overlap(final_answer_text(candidate.response), source_doc) else 2.5

    completeness = 5.0
    if word_count(final_answer_text(candidate.response)) < MIN_FINAL_ANSWER_WORDS:
        completeness -= 1.5
    if not caveat_texts(candidate.response):
        completeness -= 1.0
    if word_count(candidate.response) > MAX_RESPONSE_WORDS:
        completeness -= 0.75

    dimensions = {
        "factual_accuracy": clamp_score(factual_accuracy),
        "reasoning_quality": clamp_score(reasoning_quality),
        "operational_relevance": clamp_score(operational_relevance),
        "specificity": clamp_score(specificity),
        "completeness": clamp_score(completeness),
    }
    weights = quality_config.get("scoring", {}).get("weights", {})
    total = sum(
        dimensions[name] * float(weights.get(name, default_weight(name)))
        for name in dimensions
    )
    weight_total = sum(float(weights.get(name, default_weight(name))) for name in dimensions)
    if weight_total:
        total /= weight_total

    return QualityScore(**dimensions, total=round(total, 3))


def find_invented_indicators(candidate: QualityCandidate, source_doc: RawDocument) -> list[str]:
    output_text = "\n".join(
        [
            candidate.instruction,
            candidate.response,
            " ".join(candidate.mitre_techniques),
            " ".join(candidate.atlas_techniques),
            " ".join(candidate.tools_referenced),
        ]
    )
    return invented_indicators(output_text, source_corpus_text(source_doc))


def word_count(value: str) -> int:
    return len(value.split())


def source_corpus_text(source_doc: RawDocument) -> str:
    return source_document_text(
        source_doc.title,
        source_doc.source_url,
        source_doc.content_markdown,
        source_doc.metadata,
    )


def has_source_specific_overlap(final_answer: str, source_doc: RawDocument) -> bool:
    if not final_answer:
        return False
    source_tokens = distinctive_tokens(source_corpus_text(source_doc))
    answer_tokens = distinctive_tokens(final_answer)
    return bool(source_tokens & answer_tokens)


def distinctive_tokens(text: str) -> set[str]:
    tokens = set()
    for token in TOKEN_RE.findall(text):
        normalized = token.strip(".,:;()[]{}'\"`").lower()
        if len(normalized) < 4 or normalized in STOPWORDS:
            continue
        tokens.add(normalized)
    return tokens


def has_operational_signal(candidate: QualityCandidate) -> bool:
    text = final_answer_text(candidate.response).lower()
    if not text:
        return False
    category_signals = {
        "artifact_analysis": (
            "artifact",
            "path",
            "field",
            "log",
            "evidence",
            "parse",
            "timeline",
        ),
        "ttp_identification": (
            "attack",
            "mitre",
            "technique",
            "candidate",
            "mapping",
            "tactic",
        ),
        "triage_and_hunting": (
            "check",
            "collect",
            "corroborate",
            "hunt",
            "investigate",
            "pivot",
            "review",
            "triage",
        ),
        "detection_engineering": (
            "detection",
            "false positive",
            "logic",
            "query",
            "rule",
            "telemetry",
            "tuning",
        ),
        "report_generation": (
            "confidence",
            "caveat",
            "evidence",
            "finding",
            "report",
            "summary",
        ),
    }
    signals = category_signals.get(candidate.category, ())
    return any(signal in text for signal in signals)


def clamp_score(value: float) -> float:
    return max(1.0, min(5.0, round(value, 3)))


def default_weight(name: str) -> float:
    return {
        "factual_accuracy": 0.25,
        "reasoning_quality": 0.25,
        "operational_relevance": 0.20,
        "specificity": 0.15,
        "completeness": 0.15,
    }[name]
