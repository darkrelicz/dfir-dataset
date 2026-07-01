import json
import re
from collections.abc import Mapping
from typing import Any

from collectors.schemas import RawDocument
from pydantic import ValidationError
from quality.references import QualityReferences, normalize_tool_name
from quality.schemas import QualityCandidate, QualityDecision, QualityIssue, QualityScore


REASONING_START_RE = re.compile(r"^\s*<reasoning>\s*$", re.MULTILINE)
REASONING_END_RE = re.compile(r"^\s*</reasoning>\s*$", re.MULTILINE)
REASONING_BLOCK_RE = re.compile(r"<reasoning>\s*(.*?)\s*</reasoning>", re.DOTALL)
EVIDENCE_RE = re.compile(r"^E(\d+):\s*(.*)$", re.MULTILINE)
ANALYSIS_RE = re.compile(r"^A(\d+)\s+\[uses\s+([^\]]+)\]:\s*(.*)$", re.MULTILINE)
CONCLUSION_RE = re.compile(
    r"^C(\d+)\s+\[uses\s+([^\]]+)\]\s+Confidence:\s+"
    r"(high|medium|low)\.\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
CAVEAT_RE = re.compile(r"^CV(\d+)\s+\[applies_to\s+([^\]]+)\]:\s*(.*)$", re.MULTILINE)
ID_LINE_RE = re.compile(r"^(?:E\d+:|A\d+\s+\[uses|C\d+\s+\[uses|CV\d+\s+\[applies_to)")
REF_RE = re.compile(r"\b(?:E|A|C|CV)\d+\b")
GENERAL_KNOWLEDGE_RE = re.compile(r"\[GENERAL KNOWLEDGE\]", re.IGNORECASE)
MITRE_ID_RE = re.compile(r"^T\d{4}(?:\.\d{3})?\??$")
MITRE_ID_ANYWHERE_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\??\b")
ATLAS_ID_RE = re.compile(r"^AML\.T\d{4}(?:\.\d{3})?\??$")
ATLAS_ID_ANYWHERE_RE = re.compile(r"\bAML\.T\d{4}(?:\.\d{3})?\??\b")
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
HASH_RE = re.compile(r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b")
IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
DOMAIN_RE = re.compile(
    r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"(?:com|net|org|io|gov|edu|mil|co|uk|ru|cn|de|jp|br|au|ca|fr|nl|"
    r"info|biz|dev|cloud|app|tech|site|online)\b"
)
WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\[^\s\"'<>|]+")
REGISTRY_PATH_RE = re.compile(
    r"(?i)\b(?:HKLM|HKCU|HKCR|HKU|HKCC|HKEY_LOCAL_MACHINE|"
    r"HKEY_CURRENT_USER|HKEY_CLASSES_ROOT|HKEY_USERS|"
    r"HKEY_CURRENT_CONFIG)\\[A-Za-z0-9_\\/*.$%{}-]+"
)
UNIX_PATH_RE = re.compile(
    r"(?<![\w])/(?:etc|var|tmp|home|usr|bin|sbin|opt|root|Users|"
    r"Library|System|Applications|private|Volumes)/[^\s\"'<>]+"
)
EVENT_ID_RE = re.compile(r"\b(?:Event\s+ID|EID)\s*[:#-]?\s*(\d{3,5})\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.\\/-]{2,}")

PLACEHOLDER_TEXT = {
    "",
    "...",
    "[source-grounded evidence]",
    "[analysis of evidence]",
    "[conclusion]",
}
BROAD_CLAIM_TERMS = (
    "compromise",
    "command and control",
    "c2",
    "exfiltration",
    "isolate",
    "lateral movement",
    "malware",
    "persistence",
    "privilege escalation",
)
OVERCLAIM_TERMS = (
    "confirmed compromise",
    "definitive compromise",
    "proof of compromise",
    "immediate isolation",
    "immediately isolate",
)
GENERIC_CAVEAT_TERMS = (
    "additional evidence",
    "additional logs",
    "corroborate",
    "further investigation",
    "review logs",
)
MIN_RESPONSE_WORDS = 80
MAX_RESPONSE_WORDS = 1200
MIN_FINAL_ANSWER_WORDS = 25
DEFAULT_ACCEPT_THRESHOLD = 3.5
DEFAULT_REVIEW_THRESHOLD = 3.0
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
    """Run Phase 4 row-level gates without using Phase 3 output validators."""

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
    issues.extend(review_heuristics(candidate, source_doc))

    score = score_candidate(candidate, source_doc, issues, quality_config or {})
    issues.extend(score_gate_issues(score, quality_config or {}))

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
    issues: list[QualityIssue] = []
    if not REASONING_BLOCK_RE.search(response):
        return [
            QualityIssue(
                code="reasoning_links_invalid",
                severity="reject",
                message="Missing <reasoning> block",
            )
        ]

    nonempty_lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not nonempty_lines or nonempty_lines[0] != "<reasoning>":
        issues.append(
            QualityIssue(
                code="reasoning_links_invalid",
                severity="reject",
                message="Response must begin with <reasoning> on its own line",
            )
        )
    if not REASONING_START_RE.search(response) or not REASONING_END_RE.search(response):
        issues.append(
            QualityIssue(
                code="reasoning_links_invalid",
                severity="reject",
                message="<reasoning> and </reasoning> must each be on their own line",
            )
        )

    block = REASONING_BLOCK_RE.search(response)
    if block is None:
        return issues

    reasoning_text = block.group(1)
    for line in reasoning_text.splitlines():
        stripped = line.strip()
        if stripped and not ID_LINE_RE.match(stripped):
            issues.append(
                QualityIssue(
                    code="reasoning_links_invalid",
                    severity="reject",
                    message=f"Unexpected line inside reasoning block: {stripped[:80]}",
                )
            )

    evidence_matches = EVIDENCE_RE.findall(reasoning_text)
    analysis_matches = ANALYSIS_RE.findall(reasoning_text)
    conclusion_matches = CONCLUSION_RE.findall(reasoning_text)
    caveat_matches = CAVEAT_RE.findall(reasoning_text)

    evidence_ids = [f"E{number}" for number, _ in evidence_matches]
    analysis_ids = [f"A{number}" for number, _, _ in analysis_matches]
    conclusion_ids = [f"C{number}" for number, _, _, _ in conclusion_matches]
    caveat_ids = [f"CV{number}" for number, _, _ in caveat_matches]

    evidence_set = set(evidence_ids)
    analysis_set = set(analysis_ids)
    conclusion_set = set(conclusion_ids)
    step_count = (
        len(evidence_ids)
        + len(analysis_ids)
        + len(conclusion_ids)
        + len(caveat_ids)
    )
    reasoning_config = (quality_config or {}).get("reasoning", {})
    min_steps = int(reasoning_config.get("min_steps", 4))
    max_steps = int(reasoning_config.get("max_steps", 24))

    if step_count < min_steps:
        issues.append(
            reasoning_issue(
                f"Reasoning block has {step_count} linked step(s), below minimum {min_steps}"
            )
        )
    if step_count > max_steps:
        issues.append(
            QualityIssue(
                code="reasoning_too_long",
                severity="review",
                message=(
                    f"Reasoning block has {step_count} linked step(s), above "
                    f"maximum {max_steps}"
                ),
            )
        )

    if not evidence_ids:
        issues.append(reasoning_issue("No evidence IDs found"))
    if not analysis_ids:
        issues.append(reasoning_issue("No analysis IDs found"))
    if not conclusion_ids:
        issues.append(reasoning_issue("No conclusion IDs found"))
    if not caveat_ids:
        issues.append(reasoning_issue("No caveat IDs found"))

    for prefix, ids in (
        ("evidence", evidence_ids),
        ("analysis", analysis_ids),
        ("conclusion", conclusion_ids),
        ("caveat", caveat_ids),
    ):
        duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
        if duplicate_ids:
            issues.append(reasoning_issue(f"Duplicate {prefix} IDs found: {duplicate_ids}"))

    for evidence_number, evidence_text in evidence_matches:
        if evidence_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(reasoning_issue(f"E{evidence_number} has empty evidence"))

    for analysis_number, refs_text, analysis_text in analysis_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in evidence_set)
        if missing:
            issues.append(
                reasoning_issue(f"A{analysis_number} references missing evidence: {missing}")
            )
        if analysis_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(reasoning_issue(f"A{analysis_number} has empty analysis"))

    for conclusion_number, refs_text, confidence, conclusion_text in conclusion_matches:
        refs = set(REF_RE.findall(refs_text))
        has_evidence = bool(refs & evidence_set)
        has_analysis = bool(refs & analysis_set)
        missing = sorted(
            ref
            for ref in refs
            if ref.startswith(("E", "A"))
            and ref not in evidence_set
            and ref not in analysis_set
        )
        if missing:
            issues.append(
                reasoning_issue(f"C{conclusion_number} references missing IDs: {missing}")
            )
        if not has_evidence or not has_analysis:
            issues.append(
                reasoning_issue(
                    f"C{conclusion_number} must reference at least one evidence ID "
                    "and one analysis ID"
                )
            )
        if confidence.lower() not in {"high", "medium", "low"}:
            issues.append(reasoning_issue(f"C{conclusion_number} has invalid confidence"))
        if conclusion_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(reasoning_issue(f"C{conclusion_number} has empty conclusion"))

    for caveat_number, refs_text, caveat_text in caveat_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in conclusion_set)
        if missing:
            issues.append(
                reasoning_issue(
                    f"CV{caveat_number} references missing conclusion: {missing}"
                )
            )
        if caveat_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(reasoning_issue(f"CV{caveat_number} has empty caveat"))

    if not final_answer_text(response):
        issues.append(
            QualityIssue(
                code="reasoning_links_invalid",
                severity="reject",
                message="Response is missing final answer text after </reasoning>",
            )
        )

    return issues


def reasoning_issue(message: str) -> QualityIssue:
    return QualityIssue(
        code="reasoning_links_invalid",
        severity="reject",
        message=message,
    )


def validate_grounding(candidate: QualityCandidate) -> list[QualityIssue]:
    has_tag = bool(GENERAL_KNOWLEDGE_RE.search(candidate.response))
    if candidate.grounding == "source_only" and has_tag:
        return [
            QualityIssue(
                code="grounding_mismatch",
                severity="reject",
                message="grounding is source_only but response contains [GENERAL KNOWLEDGE]",
            )
        ]
    if candidate.grounding == "source_plus_general" and not has_tag:
        return [
            QualityIssue(
                code="grounding_mismatch",
                severity="reject",
                message="grounding is source_plus_general but response has no [GENERAL KNOWLEDGE] tags",
            )
        ]
    return []


def validate_source_grounding(
    candidate: QualityCandidate,
    source_doc: RawDocument,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    source_text = source_corpus_text(source_doc)

    invented = invented_indicators(candidate, source_doc)
    if invented:
        severity = "review" if candidate.grounding == "source_plus_general" else "reject"
        issues.append(
            QualityIssue(
                code="invented_indicator",
                severity=severity,
                message=f"Concrete indicators not present in source document: {invented}",
            )
        )

    source_lower = source_text.lower()
    response_lower = candidate.response.lower()
    broad_terms = [
        term
        for term in BROAD_CLAIM_TERMS
        if term in response_lower and term not in source_lower
    ]
    if broad_terms and candidate.grounding == "source_only":
        issues.append(
            QualityIssue(
                code="unsupported_claim",
                severity="review",
                message=(
                    "source_only response uses broad claim term(s) not visible "
                    f"in source: {sorted(set(broad_terms))}"
                ),
            )
        )
    elif broad_terms and candidate.grounding == "source_plus_general":
        untagged = [
            term for term in broad_terms if not term_near_general_knowledge_tag(term, candidate.response)
        ]
        if untagged:
            issues.append(
                QualityIssue(
                    code="unsupported_claim",
                    severity="review",
                    message=(
                        "source_plus_general response may contain untagged "
                        f"general claim term(s): {sorted(set(untagged))}"
                    ),
                )
            )

    source_only_tools = [
        tool
        for tool in candidate.tools_referenced
        if candidate.grounding == "source_only" and tool.lower() not in source_lower
    ]
    if source_only_tools:
        issues.append(
            QualityIssue(
                code="unsupported_claim",
                severity="review",
                message=(
                    "source_only tools_referenced includes tool name(s) absent "
                    f"from source: {sorted(set(source_only_tools))}"
                ),
            )
        )

    final_answer = final_answer_text(candidate.response)
    final_mitre = set(MITRE_ID_ANYWHERE_RE.findall(final_answer))
    reasoning_mitre = set(MITRE_ID_ANYWHERE_RE.findall(reasoning_block_text(candidate.response)))
    if final_mitre - reasoning_mitre:
        issues.append(
            QualityIssue(
                code="unsupported_claim",
                severity="review",
                message=(
                    "Final answer mentions MITRE ID(s) absent from reasoning block: "
                    f"{sorted(final_mitre - reasoning_mitre)}"
                ),
            )
        )

    if any(term in final_answer.lower() for term in OVERCLAIM_TERMS):
        issues.append(
            QualityIssue(
                code="unsupported_claim",
                severity="review",
                message="Final answer uses compromise/containment language that needs review",
            )
        )

    return issues


def review_heuristics(
    candidate: QualityCandidate,
    source_doc: RawDocument,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    response = candidate.response
    final_answer = final_answer_text(response)
    response_words = word_count(response)
    final_words = word_count(final_answer)

    if response_words < MIN_RESPONSE_WORDS or final_words < MIN_FINAL_ANSWER_WORDS:
        issues.append(
            QualityIssue(
                code="low_operational_value",
                severity="review",
                message="Response or final answer is short enough to warrant review",
            )
        )

    if response_words > MAX_RESPONSE_WORDS:
        issues.append(
            QualityIssue(
                code="low_operational_value",
                severity="review",
                message="Response is unusually long for one training pair",
            )
        )

    caveats = caveat_texts(response)
    if caveats and all(is_weak_caveat(caveat) for caveat in caveats):
        issues.append(
            QualityIssue(
                code="low_operational_value",
                severity="review",
                message="Caveat appears generic and should be spot-checked",
            )
        )

    if not has_source_specific_overlap(final_answer, source_doc):
        issues.append(
            QualityIssue(
                code="low_specificity",
                severity="review",
                message="Final answer has low lexical overlap with source details",
            )
        )

    if not has_operational_signal(candidate):
        issues.append(
            QualityIssue(
                code="low_operational_value",
                severity="review",
                message="Final answer has weak task-specific operational signal",
            )
        )

    return issues


def score_candidate(
    candidate: QualityCandidate,
    source_doc: RawDocument,
    issues: list[QualityIssue],
    quality_config: Mapping[str, Any],
) -> QualityScore:
    codes = {issue.code for issue in issues}
    hard_codes = {issue.code for issue in issues if issue.severity == "reject"}

    factual_accuracy = 5.0
    if "invented_indicator" in hard_codes:
        factual_accuracy = 1.0
    elif "grounding_mismatch" in hard_codes:
        factual_accuracy = 2.0
    elif "unsupported_claim" in codes:
        factual_accuracy -= 1.5

    reasoning_quality = 5.0
    if "reasoning_links_invalid" in hard_codes:
        reasoning_quality = 1.0
    elif "low_operational_value" in codes and "Caveat appears generic" in issue_messages(issues):
        reasoning_quality -= 0.75

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


def score_gate_issues(
    score: QualityScore,
    quality_config: Mapping[str, Any],
) -> list[QualityIssue]:
    scoring_config = quality_config.get("scoring", {})
    accept_threshold = float(scoring_config.get("threshold", DEFAULT_ACCEPT_THRESHOLD))
    review_threshold = float(scoring_config.get("review_threshold", DEFAULT_REVIEW_THRESHOLD))
    if score.total < review_threshold:
        return [
            QualityIssue(
                code="low_quality_score",
                severity="reject",
                message=f"Quality score {score.total:.2f} is below reject threshold {review_threshold:.2f}",
            )
        ]
    if score.total < accept_threshold:
        return [
            QualityIssue(
                code="low_quality_score",
                severity="review",
                message=f"Quality score {score.total:.2f} is below accept threshold {accept_threshold:.2f}",
            )
        ]
    return []


def term_near_general_knowledge_tag(term: str, text: str) -> bool:
    lowered = text.lower()
    for match in re.finditer(re.escape(term), lowered):
        start = max(match.start() - 140, 0)
        end = min(match.end() + 140, len(text))
        if GENERAL_KNOWLEDGE_RE.search(text[start:end]):
            return True
    return False


def normalized_mapping_id(value: str) -> str:
    return value.rstrip("?")


def invented_indicators(candidate: QualityCandidate, source_doc: RawDocument) -> list[str]:
    source_indicators = extract_concrete_indicators(source_corpus_text(source_doc))
    output_text = "\n".join(
        [
            candidate.instruction,
            candidate.response,
            " ".join(candidate.mitre_techniques),
            " ".join(candidate.atlas_techniques),
            " ".join(candidate.tools_referenced),
        ]
    )
    output_indicators = extract_concrete_indicators(output_text)
    return sorted(output_indicators - source_indicators)


def extract_concrete_indicators(text: str) -> set[str]:
    indicators: set[str] = set()
    indicators.update(value.upper() for value in CVE_RE.findall(text))
    indicators.update(value.lower() for value in HASH_RE.findall(text))
    indicators.update(IPV4_RE.findall(text))
    indicators.update(value.lower() for value in DOMAIN_RE.findall(text))
    indicators.update(normalize_indicator(value) for value in WINDOWS_PATH_RE.findall(text))
    indicators.update(normalize_indicator(value) for value in REGISTRY_PATH_RE.findall(text))
    indicators.update(normalize_indicator(value) for value in UNIX_PATH_RE.findall(text))
    indicators.update(f"event_id:{value}" for value in EVENT_ID_RE.findall(text))
    return {value for value in indicators if value}


def normalize_indicator(value: str) -> str:
    return value.strip(".,;:()[]{}'\"`").rstrip("\\/").lower()


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value.strip().lower())


def word_count(value: str) -> int:
    return len(value.split())


def final_answer_text(response: str) -> str:
    closing = "</reasoning>"
    if closing not in response:
        return ""
    return response.split(closing, 1)[1].strip()


def reasoning_block_text(response: str) -> str:
    match = REASONING_BLOCK_RE.search(response)
    if not match:
        return ""
    return match.group(1)


def caveat_texts(response: str) -> list[str]:
    return [match.strip() for _, _, match in CAVEAT_RE.findall(response)]


def is_weak_caveat(caveat: str) -> bool:
    lowered = caveat.lower()
    if word_count(caveat) < 8:
        return True
    return any(term in lowered for term in GENERIC_CAVEAT_TERMS) and not any(
        marker in caveat for marker in ("`", "\\", "/", "Event ID", "CVE-", "T")
    )


def source_corpus_text(source_doc: RawDocument) -> str:
    return "\n".join(
        [
            source_doc.title,
            source_doc.source_url,
            source_doc.content_markdown,
            json.dumps(source_doc.metadata, sort_keys=True),
        ]
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


def issue_messages(issues: list[QualityIssue]) -> str:
    return "\n".join(issue.message for issue in issues)


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
