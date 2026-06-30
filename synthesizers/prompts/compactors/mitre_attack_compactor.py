import re

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    COMPACTED_SOURCE_NOTE,
    limit_text,
    markdown_sections,
    prompt_section,
    section_body,
)


DESCRIPTION_CHAR_LIMIT = 4200
DETECTION_CHAR_LIMIT = 1400
MAX_DETECTIONS = 5
MAX_MITIGATIONS = 8
MAX_PROCEDURES = 18
MITIGATION_CHAR_LIMIT = 520
PROCEDURE_CHAR_LIMIT = 520

CONCRETE_DETAIL_RE = re.compile(
    r"(`|<code>|\\[A-Za-z0-9_$.-]+\\|/[A-Za-z0-9_.-]+|"
    r"\b(?:powershell|cmd|schtasks|reg(?:\.exe)?|rundll32|wmic|curl|wget|ssh|scp|"
    r"certutil|vssadmin|bcdedit|net(?:\.exe)?|wevtutil|systemctl|launchctl)\b)",
    re.IGNORECASE,
)


def compact_mitre_attack_for_prompt(doc: RawDocument, content: str) -> str:
    preamble, sections = markdown_sections(content)
    lines: list[str] = [f"# {attack_id_from_doc(doc)}: {doc.title}", ""]

    for line in preamble:
        if line.startswith("**Tactics**:") or line.startswith("**Platforms**:"):
            lines.append(line)

    parent_technique = doc.metadata.get("parent_technique")
    if parent_technique:
        lines.append(f"**Parent technique**: {parent_technique}")
    lines.append("")

    description = section_body(sections, "Description")
    if description:
        lines.extend(prompt_section("Description", description, DESCRIPTION_CHAR_LIMIT))

    procedures = section_body(sections, "Procedures")
    procedure_lines = select_procedure_lines(procedures)
    if procedure_lines:
        total_procedures = count_list_items(procedures)
        lines.append("## Procedures")
        lines.append(
            f"Selected {len(procedure_lines)} of {total_procedures} "
            "procedure example(s), prioritizing concrete commands/artifacts."
        )
        for procedure in procedure_lines:
            lines.append(f"- {limit_text(procedure, PROCEDURE_CHAR_LIMIT)}")
        lines.append("")

    mitigations = select_list_lines(section_body(sections, "Mitigations"), MAX_MITIGATIONS)
    if mitigations:
        lines.append("## Mitigations")
        for mitigation in mitigations:
            lines.append(f"- {limit_text(mitigation, MITIGATION_CHAR_LIMIT)}")
        lines.append("")

    detections = select_list_lines(section_body(sections, "Detections"), MAX_DETECTIONS)
    if detections:
        lines.append("## Detections")
        for detection in detections:
            lines.append(f"- {limit_text(detection, DETECTION_CHAR_LIMIT)}")
        lines.append("")

    lines.append(COMPACTED_SOURCE_NOTE)
    compacted = "\n".join(lines).strip()
    if len(compacted) >= len(content):
        return content
    return compacted


compact_for_prompt = compact_mitre_attack_for_prompt


def attack_id_from_doc(doc: RawDocument) -> str:
    if doc.doc_id.startswith("mitre-attack-"):
        return doc.doc_id.removeprefix("mitre-attack-")
    return doc.doc_id


def select_procedure_lines(body: str) -> list[str]:
    procedures = select_list_lines(body, max_items=10_000)
    if len(procedures) <= MAX_PROCEDURES:
        return procedures

    scored = [
        (procedure_score(procedure), index, procedure)
        for index, procedure in enumerate(procedures)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_indexes = sorted(index for _, index, _ in scored[:MAX_PROCEDURES])
    return [procedures[index] for index in selected_indexes]


def procedure_score(procedure: str) -> int:
    score = 0
    if CONCRETE_DETAIL_RE.search(procedure):
        score += 4
    if " can " in procedure or " has " in procedure or " used " in procedure:
        score += 1
    if len(procedure) > 220:
        score += 1
    return score


def select_list_lines(body: str, max_items: int) -> list[str]:
    items: list[str] = []
    current: list[str] = []

    for line in body.splitlines():
        if line.startswith("- "):
            if current:
                items.append(" ".join(part.strip() for part in current).strip())
            current = [line.removeprefix("- ").strip()]
            continue
        if current and line.strip():
            current.append(line.strip())

    if current:
        items.append(" ".join(part.strip() for part in current).strip())

    return items[:max_items]


def count_list_items(body: str) -> int:
    return sum(1 for line in body.splitlines() if line.startswith("- "))
