import json
import re
from pathlib import Path

from collectors.schemas import RawDocument
from synthesizers.io import raw_jsonl_paths
from synthesizers.schemas import (
    GeneratedPairIssue,
    GeneratedPairValidation,
    InstructionPair,
    PromptRecord,
    RawCorpusIssue,
    RawCorpusValidation,
    ReasoningLinkIssue,
    ReasoningLinkValidation,
)


REASONING_BLOCK_RE = re.compile(r"<reasoning>\s*(.*?)\s*</reasoning>", re.DOTALL)
EVIDENCE_RE = re.compile(r"^E(\d+):\s*(.*)$", re.MULTILINE)
ANALYSIS_RE = re.compile(r"^A(\d+)\s+\[uses\s+([^\]]+)\]:\s*(.*)$", re.MULTILINE)
CONCLUSION_RE = re.compile(r"^C(\d+)\s+\[uses\s+([^\]]+)\].*$", re.MULTILINE)
CAVEAT_RE = re.compile(r"^CV(\d+)\s+\[applies_to\s+([^\]]+)\]:", re.MULTILINE)
REF_RE = re.compile(r"\b(?:E|A|C|CV)\d+\b")
MITRE_ID_RE = re.compile(r"^T\d{4}(?:\.\d{3})?\??$")
ATLAS_ID_RE = re.compile(r"^AML\.T\d{4}(?:\.\d{3})?\??$")
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
PLACEHOLDER_TEXT = {
    "",
    "...",
    "[source-grounded evidence]",
    "[analysis of evidence]",
    "[conclusion]",
}


def validate_raw_corpus(raw_dir: Path) -> RawCorpusValidation:
    issues: list[RawCorpusIssue] = []
    source_counts: dict[str, int] = {}
    seen_doc_ids: dict[str, str] = {}
    document_count = 0
    paths = raw_jsonl_paths(raw_dir)

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                document_count += 1
                try:
                    doc = RawDocument.model_validate(json.loads(line))
                except Exception as exc:
                    issues.append(
                        RawCorpusIssue(
                            path=str(path),
                            line=line_number,
                            message=f"RawDocument validation failed: {exc}",
                        )
                    )
                    continue

                source_counts[doc.source] = source_counts.get(doc.source, 0) + 1
                location = f"{path}:{line_number}"
                if doc.doc_id in seen_doc_ids:
                    issues.append(
                        RawCorpusIssue(
                            path=str(path),
                            line=line_number,
                            message=(
                                f"Duplicate doc_id {doc.doc_id}; first seen at "
                                f"{seen_doc_ids[doc.doc_id]}"
                            ),
                        )
                    )
                else:
                    seen_doc_ids[doc.doc_id] = location

    return RawCorpusValidation(
        raw_dir=str(raw_dir),
        file_count=len(paths),
        document_count=document_count,
        unique_doc_ids=len(seen_doc_ids),
        source_counts=dict(sorted(source_counts.items())),
        issues=issues,
    )


def validate_reasoning_links(response: str) -> ReasoningLinkValidation:
    issues: list[ReasoningLinkIssue] = []
    match = REASONING_BLOCK_RE.search(response)
    if not match:
        return ReasoningLinkValidation(
            ok=False,
            evidence_ids=[],
            analysis_ids=[],
            conclusion_ids=[],
            caveat_ids=[],
            issues=[ReasoningLinkIssue(message="Missing <reasoning> block")],
        )

    block = match.group(1)
    evidence_matches = EVIDENCE_RE.findall(block)
    analysis_matches = ANALYSIS_RE.findall(block)
    conclusion_matches = CONCLUSION_RE.findall(block)
    caveat_matches = CAVEAT_RE.findall(block)
    evidence_ids = [f"E{number}" for number, _ in evidence_matches]
    analysis_ids = [f"A{number}" for number, _, _ in analysis_matches]
    conclusion_ids = [f"C{number}" for number, _ in conclusion_matches]
    caveat_ids = [f"CV{number}" for number, _ in caveat_matches]

    evidence_set = set(evidence_ids)
    analysis_set = set(analysis_ids)
    conclusion_set = set(conclusion_ids)

    if not evidence_ids:
        issues.append(ReasoningLinkIssue(message="No evidence IDs found"))
    if not analysis_ids:
        issues.append(ReasoningLinkIssue(message="No analysis IDs found"))
    if not conclusion_ids:
        issues.append(ReasoningLinkIssue(message="No conclusion IDs found"))

    for evidence_number, evidence_text in evidence_matches:
        if evidence_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(
                ReasoningLinkIssue(message=f"E{evidence_number} has empty evidence")
            )

    for analysis_number, refs_text, analysis_text in analysis_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in evidence_set)
        if missing:
            issues.append(
                ReasoningLinkIssue(
                    message=f"A{analysis_number} references missing evidence: {missing}"
                )
            )
        if analysis_text.strip().lower() in PLACEHOLDER_TEXT:
            issues.append(
                ReasoningLinkIssue(message=f"A{analysis_number} has empty analysis")
            )

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
                ReasoningLinkIssue(
                    message=f"C{conclusion_number} references missing IDs: {missing}"
                )
            )
        if not has_evidence or not has_analysis:
            issues.append(
                ReasoningLinkIssue(
                    message=(
                        f"C{conclusion_number} must reference at least one evidence "
                        "ID and one analysis ID"
                    )
                )
            )

    for caveat_number, refs_text in caveat_matches:
        refs = set(REF_RE.findall(refs_text))
        missing = sorted(ref for ref in refs if ref not in conclusion_set)
        if missing:
            issues.append(
                ReasoningLinkIssue(
                    message=f"CV{caveat_number} references missing conclusion: {missing}"
                )
            )

    return ReasoningLinkValidation(
        ok=not issues,
        evidence_ids=evidence_ids,
        analysis_ids=analysis_ids,
        conclusion_ids=conclusion_ids,
        caveat_ids=caveat_ids,
        issues=issues,
    )


def valid_taxonomy_refs_from_quality_config(quality_config: dict) -> set[str]:
    refs: set[str] = set()
    for domain in quality_config.get("taxonomy", {}).get("domains", {}).values():
        refs.update(str(value) for value in domain.get("ids", []))
    return refs


def validate_generated_pairs(
    raw_output: str,
    source_doc: RawDocument,
    prompt_record: PromptRecord,
    valid_taxonomy_refs: set[str],
) -> GeneratedPairValidation:
    issues: list[GeneratedPairIssue] = []
    pairs: list[InstructionPair] = []

    try:
        decoded = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return GeneratedPairValidation(
            ok=False,
            issues=[
                GeneratedPairIssue(
                    source_doc_id=source_doc.doc_id,
                    message=f"Invalid JSON output: {exc}",
                )
            ],
        )

    if not isinstance(decoded, list):
        return GeneratedPairValidation(
            ok=False,
            issues=[
                GeneratedPairIssue(
                    source_doc_id=source_doc.doc_id,
                    message="Generated output must be a JSON array",
                )
            ],
        )

    if len(decoded) != prompt_record.pairs_requested:
        issues.append(
            GeneratedPairIssue(
                source_doc_id=source_doc.doc_id,
                message=(
                    f"Expected {prompt_record.pairs_requested} pair(s), "
                    f"got {len(decoded)}"
                ),
            )
        )

    for index, item in enumerate(decoded):
        try:
            pair = InstructionPair.model_validate(item)
        except Exception as exc:
            issues.append(
                GeneratedPairIssue(
                    source_doc_id=source_doc.doc_id,
                    pair_index=index,
                    message=f"InstructionPair schema validation failed: {exc}",
                )
            )
            continue

        pairs.append(pair)
        issues.extend(
            _validate_pair_against_source(
                pair,
                index,
                source_doc,
                prompt_record,
                valid_taxonomy_refs,
            )
        )

    return GeneratedPairValidation(ok=not issues, pairs=pairs, issues=issues)


def _validate_pair_against_source(
    pair: InstructionPair,
    index: int,
    source_doc: RawDocument,
    prompt_record: PromptRecord,
    valid_taxonomy_refs: set[str],
) -> list[GeneratedPairIssue]:
    issues: list[GeneratedPairIssue] = []
    source_doc_id = source_doc.doc_id

    def add(message: str) -> None:
        issues.append(
            GeneratedPairIssue(
                source_doc_id=source_doc_id,
                pair_index=index,
                message=message,
            )
        )

    if pair.source_doc_id != source_doc.doc_id:
        add(f"source_doc_id mismatch: {pair.source_doc_id} != {source_doc.doc_id}")
    if pair.source != source_doc.source:
        add(f"source mismatch: {pair.source} != {source_doc.source}")
    if pair.category != prompt_record.category:
        add(f"category mismatch: {pair.category} != {prompt_record.category}")
    if pair.difficulty != prompt_record.difficulty:
        add(f"difficulty mismatch: {pair.difficulty} != {prompt_record.difficulty}")

    reasoning = validate_reasoning_links(pair.response)
    for issue in reasoning.issues:
        add(issue.message)

    final_answer = _final_answer_text(pair.response)
    if not final_answer:
        add("Response is missing final answer text after </reasoning>")

    invalid_taxonomy = sorted(set(pair.taxonomy_refs) - valid_taxonomy_refs)
    if invalid_taxonomy:
        add(f"Invalid taxonomy_refs: {invalid_taxonomy}")

    invalid_mitre = [
        value for value in pair.mitre_techniques if not MITRE_ID_RE.match(value)
    ]
    if invalid_mitre:
        add(f"Invalid MITRE technique IDs: {invalid_mitre}")

    invalid_atlas = [
        value for value in pair.atlas_techniques if not ATLAS_ID_RE.match(value)
    ]
    if invalid_atlas:
        add(f"Invalid ATLAS technique IDs: {invalid_atlas}")

    invented_indicators = _invented_indicators(pair, source_doc)
    if invented_indicators:
        add(f"Concrete indicators not present in source document: {invented_indicators}")

    return issues


def _final_answer_text(response: str) -> str:
    closing = "</reasoning>"
    if closing not in response:
        return ""
    return response.split(closing, 1)[1].strip()


def _invented_indicators(pair: InstructionPair, source_doc: RawDocument) -> list[str]:
    source_text = "\n".join(
        [
            source_doc.title,
            source_doc.source_url,
            source_doc.content_markdown,
            json.dumps(source_doc.metadata, sort_keys=True),
        ]
    )
    output_text = "\n".join(
        [
            pair.instruction,
            pair.response,
            " ".join(pair.mitre_techniques),
            " ".join(pair.atlas_techniques),
            " ".join(pair.tools_referenced),
        ]
    )

    source_indicators = _extract_concrete_indicators(source_text)
    output_indicators = _extract_concrete_indicators(output_text)
    return sorted(output_indicators - source_indicators)


def _extract_concrete_indicators(text: str) -> set[str]:
    indicators: set[str] = set()
    indicators.update(value.upper() for value in CVE_RE.findall(text))
    indicators.update(value.lower() for value in HASH_RE.findall(text))
    indicators.update(IPV4_RE.findall(text))
    indicators.update(value.lower() for value in DOMAIN_RE.findall(text))
    return indicators
