import re
from dataclasses import dataclass
from typing import Literal

REASONING_START_RE = re.compile(r"^\s*<reasoning>\s*$", re.MULTILINE)
REASONING_END_RE = re.compile(r"^\s*</reasoning>\s*$", re.MULTILINE)
REASONING_BLOCK_RE = re.compile(r"<reasoning>\s*(.*?)\s*</reasoning>", re.DOTALL)
EVIDENCE_RE = re.compile(r"^E(\d+):\s*(.*)$", re.MULTILINE)
ANALYSIS_RE = re.compile(r"^A(\d+)\s+\[uses\s+([^\]]+)\]:\s*(.*)$", re.MULTILINE)
CONCLUSION_RE = re.compile(r"^C(\d+)\s+\[uses\s+([^\]]+)\].*$", re.MULTILINE)
CONCLUSION_WITH_CONFIDENCE_RE = re.compile(
    r"^C(\d+)\s+\[uses\s+([^\]]+)\]\s+Confidence:\s+"
    r"(high|medium|low)\.\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
CAVEAT_RE = re.compile(r"^CV(\d+)\s+\[applies_to\s+([^\]]+)\]:\s*(.*)$", re.MULTILINE)
ID_LINE_RE = re.compile(r"^(?:E\d+:|A\d+\s+\[uses|C\d+\s+\[uses|CV\d+\s+\[applies_to)")
REF_RE = re.compile(r"\b(?:E|A|C|CV)\d+\b")

PLACEHOLDER_TEXT = {
    "",
    "...",
    "[source-grounded evidence]",
    "[analysis of evidence]",
    "[conclusion]",
}


@dataclass(frozen=True)
class ReasoningIssue:
    message: str
    code: str = "reasoning_links_invalid"
    severity: Literal["reject", "review"] = "reject"


@dataclass(frozen=True)
class ReasoningValidationOptions:
    require_start_on_own_line: bool = False
    require_tags_on_own_line: bool = False
    require_known_line_format: bool = False
    require_conclusion_confidence: bool = False
    require_final_answer: bool = False
    min_steps: int | None = None
    max_steps: int | None = None


def validate_reasoning_structure(
    response: str,
    options: ReasoningValidationOptions | None = None,
) -> list[ReasoningIssue]:
    options = options or ReasoningValidationOptions()
    issues: list[ReasoningIssue] = []
    match = REASONING_BLOCK_RE.search(response)
    if not match:
        return [ReasoningIssue(message="Missing <reasoning> block")]

    if options.require_start_on_own_line:
        nonempty_lines = [line.strip() for line in response.splitlines() if line.strip()]
        if not nonempty_lines or nonempty_lines[0] != "<reasoning>":
            issues.append(
                ReasoningIssue(
                    message="Response must begin with <reasoning> on its own line"
                )
            )

    if options.require_tags_on_own_line and (
        not REASONING_START_RE.search(response) or not REASONING_END_RE.search(response)
    ):
        issues.append(
            ReasoningIssue(
                message="<reasoning> and </reasoning> must each be on their own line"
            )
        )

    block = match.group(1)
    if options.require_known_line_format:
        for line in block.splitlines():
            stripped = line.strip()
            if stripped and not ID_LINE_RE.match(stripped):
                issues.append(
                    ReasoningIssue(
                        message=f"Unexpected line inside reasoning block: {stripped[:80]}"
                    )
                )

    evidence_matches = EVIDENCE_RE.findall(block)
    analysis_matches = ANALYSIS_RE.findall(block)
    conclusion_matches = CONCLUSION_RE.findall(block)
    confidence_matches = CONCLUSION_WITH_CONFIDENCE_RE.findall(block)
    caveat_matches = CAVEAT_RE.findall(block)

    if options.require_conclusion_confidence:
        conclusion_ids_with_confidence = {f"C{number}" for number, *_ in confidence_matches}
        for conclusion_number, _ in conclusion_matches:
            conclusion_id = f"C{conclusion_number}"
            if conclusion_id not in conclusion_ids_with_confidence:
                issues.append(
                    ReasoningIssue(
                        message=(
                            f"{conclusion_id} is missing required "
                            "Confidence: high|medium|low. text"
                        )
                    )
                )

    evidence_ids = [f"E{number}" for number, _ in evidence_matches]
    analysis_ids = [f"A{number}" for number, _, _ in analysis_matches]
    conclusion_ids = [f"C{number}" for number, _ in conclusion_matches]
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

    if options.min_steps is not None and step_count < options.min_steps:
        issues.append(
            ReasoningIssue(
                message=(
                    f"Reasoning block has {step_count} linked step(s), "
                    f"below minimum {options.min_steps}"
                )
            )
        )
    if options.max_steps is not None and step_count > options.max_steps:
        issues.append(
            ReasoningIssue(
                code="reasoning_too_long",
                severity="review",
                message=(
                    f"Reasoning block has {step_count} linked step(s), "
                    f"above maximum {options.max_steps}"
                ),
            )
        )

    if not evidence_ids:
        issues.append(ReasoningIssue(message="No evidence IDs found"))
    if not analysis_ids:
        issues.append(ReasoningIssue(message="No analysis IDs found"))
    if not conclusion_ids:
        issues.append(ReasoningIssue(message="No conclusion IDs found"))
    if not caveat_ids:
        issues.append(ReasoningIssue(message="No caveat IDs found"))

    for prefix, ids in (
        ("evidence", evidence_ids),
        ("analysis", analysis_ids),
        ("conclusion", conclusion_ids),
        ("caveat", caveat_ids),
    ):
        duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
        if duplicate_ids:
            issues.append(
                ReasoningIssue(
                    message=f"Duplicate {prefix} IDs found: {duplicate_ids}"
                )
            )

    for evidence_number, evidence_text in evidence_matches:
        if evidence_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(ReasoningIssue(message=f"E{evidence_number} has empty evidence"))

    for analysis_number, refs_text, analysis_text in analysis_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in evidence_set)
        if missing:
            issues.append(
                ReasoningIssue(
                    message=f"A{analysis_number} references missing evidence: {missing}"
                )
            )
        if analysis_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(ReasoningIssue(message=f"A{analysis_number} has empty analysis"))

    for conclusion_number, refs_text in conclusion_matches:
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
                ReasoningIssue(
                    message=f"C{conclusion_number} references missing IDs: {missing}"
                )
            )
        if not has_evidence or not has_analysis:
            issues.append(
                ReasoningIssue(
                    message=(
                        f"C{conclusion_number} must reference at least one evidence "
                        "ID and one analysis ID"
                    )
                )
            )

    for conclusion_number, _, confidence, conclusion_text in confidence_matches:
        if confidence.lower() not in {"high", "medium", "low"}:
            issues.append(
                ReasoningIssue(message=f"C{conclusion_number} has invalid confidence")
            )
        if conclusion_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(
                ReasoningIssue(message=f"C{conclusion_number} has empty conclusion")
            )

    for caveat_number, refs_text, caveat_text in caveat_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in conclusion_set)
        if missing:
            issues.append(
                ReasoningIssue(
                    message=f"CV{caveat_number} references missing conclusion: {missing}"
                )
            )
        if caveat_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(ReasoningIssue(message=f"CV{caveat_number} has empty caveat"))

    if options.require_final_answer and not final_answer_text(response):
        issues.append(
            ReasoningIssue(message="Response is missing final answer text after </reasoning>")
        )

    return issues


def final_answer_text(response: str) -> str:
    closing = "</reasoning>"
    if closing not in response:
        return ""
    return response.split(closing, 1)[1].strip()


def caveat_texts(response: str) -> list[str]:
    return [match.strip() for _, _, match in CAVEAT_RE.findall(response)]
