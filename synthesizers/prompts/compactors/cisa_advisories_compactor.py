import re

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    limit_text,
    markdown_sections,
    prompt_section,
    section_body,
    single_line,
)


MAX_CVE_LIST = 40
MAX_RECOMMENDATIONS = 8
MAX_VULNERABILITIES = 12
SECTION_CHAR_LIMIT = 2400
VULNERABILITY_CHAR_LIMIT = 1200
VULNERABILITY_SCORE_RE = re.compile(r"\*\*CVSS Score\*\*:\s*([0-9.]+)")
KEEP_SECTIONS = {
    "Summary",
    "General Recommendations",
    "Critical infrastructure sectors",
    "Countries/areas deployed",
    "Company headquarters location",
}


def compact_cisa_advisory_for_prompt(doc: RawDocument, content: str) -> str:
    preamble, sections = markdown_sections(content)
    lines: list[str] = [f"# {doc.title}", ""]

    metadata = doc.metadata
    for label, key in (
        ("Advisory ID", "advisory_id"),
        ("Advisory type", "advisory_type"),
        ("Category", "category"),
        ("Publisher", "publisher"),
        ("Version", "version"),
    ):
        value = metadata.get(key)
        if value:
            lines.append(f"**{label}**: {value}")

    for line in preamble:
        if line.startswith("**Published**") or line.startswith("**Last Updated**"):
            lines.append(line)

    cves = [str(value) for value in metadata.get("cves", [])]
    cve_count = int(metadata.get("cve_count", len(cves)))
    if cve_count:
        lines.append(f"**CVE count**: {cve_count}")
        shown_cves = ", ".join(cves[:MAX_CVE_LIST])
        if shown_cves:
            suffix = (
                f" (+{cve_count - MAX_CVE_LIST} more)"
                if cve_count > MAX_CVE_LIST
                else ""
            )
            lines.append(f"**CVE IDs**: {shown_cves}{suffix}")
    lines.append("")

    recommendations: list[str] = []
    for heading, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        if heading == "Recommended Practices":
            compact = single_line(body)
            if compact and compact not in recommendations:
                recommendations.append(compact)
            continue
        if heading in KEEP_SECTIONS:
            lines.extend(prompt_section(heading, body, SECTION_CHAR_LIMIT))

    if recommendations:
        lines.append("## Recommended Practices")
        for recommendation in recommendations[:MAX_RECOMMENDATIONS]:
            lines.append(f"- {recommendation}")
        omitted = len(recommendations) - MAX_RECOMMENDATIONS
        if omitted > 0:
            lines.append(f"- [{omitted} additional repeated practice(s) omitted]")
        lines.append("")

    vulnerability_body = section_body(sections, "Vulnerabilities")
    vulnerability_blocks = cisa_vulnerability_blocks(vulnerability_body)
    if vulnerability_blocks:
        selected_count = min(len(vulnerability_blocks), MAX_VULNERABILITIES)
        lines.append("## Vulnerabilities")
        lines.append(
            f"Selected top {selected_count} of {len(vulnerability_blocks)} "
            "vulnerability block(s) by CVSS score."
        )
        lines.append("")
        for block in select_cisa_vulnerabilities(vulnerability_blocks):
            lines.append(compact_cisa_vulnerability_block(block))
            lines.append("")

    lines.append(
        "[Prompt compaction note: repetitive legal text, vendor boilerplate, "
        "references, and lower-priority vulnerability blocks were omitted from "
        "this prompt. Full advisory remains in the raw corpus.]"
    )
    return "\n".join(lines).strip()


compact_for_prompt = compact_cisa_advisory_for_prompt


def cisa_vulnerability_blocks(body: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("### "):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def select_cisa_vulnerabilities(blocks: list[str]) -> list[str]:
    scored_blocks = [
        (cisa_vulnerability_score(block), index, block)
        for index, block in enumerate(blocks)
    ]
    scored_blocks.sort(key=lambda item: (-item[0], item[1]))
    return [block for _, _, block in scored_blocks[:MAX_VULNERABILITIES]]


def cisa_vulnerability_score(block: str) -> float:
    match = VULNERABILITY_SCORE_RE.search(block)
    if not match:
        return 0.0
    try:
        return float(match.group(1))
    except ValueError:
        return 0.0


def compact_cisa_vulnerability_block(block: str) -> str:
    lines: list[str] = []
    remediation_count = 0
    in_remediations = False

    for line in block.splitlines():
        if line.startswith("### "):
            lines.append(line)
            continue
        if line.startswith("**Title**:"):
            lines.append(limit_text(line, 240))
            continue
        if line.startswith("**Summary**:"):
            lines.append(limit_text(line, 480))
            continue
        if line.startswith("- **CVSS Score**:") or line.startswith("- **Vector**:"):
            lines.append(line)
            continue
        if line.startswith("- **CWE**:"):
            lines.append(limit_text(line, 240))
            continue
        if line == "**Remediations**:":
            in_remediations = True
            remediation_count = 0
            lines.append(line)
            continue
        if in_remediations and line.startswith("- "):
            if remediation_count < 2:
                lines.append(limit_text(line, 240))
            remediation_count += 1
            continue
        if in_remediations and line.startswith("  - URL:"):
            if remediation_count <= 2:
                lines.append(line)
            continue
        in_remediations = False

    return limit_text("\n".join(lines), VULNERABILITY_CHAR_LIMIT)
