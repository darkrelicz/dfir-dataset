import json
import re
from pathlib import Path

from collectors.schemas import RawDocument
from synthesizers.io import raw_jsonl_paths
from synthesizers.schemas import (GeneratedPairIssue, GeneratedPairValidation,
                                  InstructionPair, PromptRecord,
                                  RawCorpusIssue, RawCorpusValidation,
                                  ReasoningLinkIssue, ReasoningLinkValidation)
from validation.grounding import grounding_mismatch_message
from validation.indicators import (BASIC_INDICATOR_OPTIONS,
                                   invented_indicators, source_document_text)
from validation.mappings import ATLAS_ID_RE, MITRE_ID_RE
from validation.reasoning import (final_answer_text,
                                  validate_reasoning_structure)

JSON_FENCE_RE = re.compile(
    r"\A\s*```[ \t]*(?:json)?[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)?```\s*\Z",
    re.DOTALL | re.IGNORECASE,
)


def validate_raw_corpus(raw_dir: Path) -> RawCorpusValidation:
    issues: list[RawCorpusIssue] = []
    source_counts: dict[str, int] = {}
    seen_doc_ids: dict[str, str] = {}
    document_count = 0
    paths = raw_jsonl_paths(raw_dir)
    if not paths:
        issues.append(
            RawCorpusIssue(
                path=str(raw_dir),
                message="No raw JSONL files found",
            )
        )

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

    if paths and document_count == 0:
        issues.append(
            RawCorpusIssue(
                path=str(raw_dir),
                message="No raw documents found",
            )
        )

    return RawCorpusValidation(
        raw_dir=str(raw_dir),
        file_count=len(paths),
        document_count=document_count,
        unique_doc_ids=len(seen_doc_ids),
        source_counts=dict(sorted(source_counts.items())),
        issues=issues,
    )


def validate_reasoning_links(response: str) -> ReasoningLinkValidation:
    issues = [
        ReasoningLinkIssue(message=issue.message)
        for issue in validate_reasoning_structure(response)
    ]
    return ReasoningLinkValidation(
        ok=not issues,
        issues=issues,
    )


def validate_generated_pairs(
    raw_output: str,
    source_doc: RawDocument,
    prompt_record: PromptRecord,
    valid_taxonomy_refs: set[str],
) -> GeneratedPairValidation:
    issues: list[GeneratedPairIssue] = []
    pairs: list[InstructionPair] = []

    try:
        decoded = json.loads(normalize_generated_json_output(raw_output))
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
            pair = InstructionPair.model_validate(
                _with_prompt_metadata(item, prompt_record)
            )
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


def normalize_generated_json_output(raw_output: str) -> str:
    output = raw_output.strip()
    match = JSON_FENCE_RE.match(output)
    if match:
        return match.group("body").strip()
    return output


def _with_prompt_metadata(item: object, prompt_record: PromptRecord) -> object:
    if not isinstance(item, dict):
        return item

    normalized = dict(item)
    normalized.update(
        {
            "category": prompt_record.category,
            "difficulty": prompt_record.difficulty,
            "source_doc_id": prompt_record.source_doc_id,
            "source": prompt_record.source,
            "taxonomy_refs": list(prompt_record.taxonomy_refs),
        }
    )
    return normalized


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

    final_answer = final_answer_text(pair.response)
    if not final_answer:
        add("Response is missing final answer text after </reasoning>")

    if not pair.taxonomy_refs:
        add("taxonomy_refs must include at least one taxonomy ID")

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

    grounding_issue = grounding_mismatch_message(pair.grounding, pair.response)
    if grounding_issue:
        add(grounding_issue)

    invented_indicators = _invented_indicators(pair, source_doc)
    if invented_indicators:
        add(
            "Concrete indicators not present in source document: "
            f"{invented_indicators}"
        )

    return issues


def _invented_indicators(pair: InstructionPair, source_doc: RawDocument) -> list[str]:
    source_text = source_document_text(
        source_doc.title,
        source_doc.source_url,
        source_doc.content_markdown,
        source_doc.metadata,
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
    return invented_indicators(output_text, source_text, BASIC_INDICATOR_OPTIONS)
