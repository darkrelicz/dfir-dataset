import re
from collections.abc import Iterable

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    limit_text,
    markdown_sections,
    prompt_section,
    section_body,
)


DESCRIPTION_CHAR_LIMIT = 1400
SECTION_CHAR_LIMIT = 1800
WORKFLOW_STEP_CHAR_LIMIT = 1300
MAX_CODE_BLOCK_CHARS = 700
MAX_CODE_BLOCK_LINES = 12
MAX_LIST_VALUES = 20
MAX_WORKFLOW_STEPS = 8

KEEP_SECTIONS = (
    "Overview",
    "When to Use",
    "Prerequisites",
    "Objectives",
    "MITRE ATT&CK Mapping",
    "Detection Logic",
    "Detection Rules",
    "Evidence Sources",
    "Validation",
    "Expected Results",
    "Key Concepts",
    "Tools & Systems",
    "Common Pitfalls",
    "Remediation",
)


def compact_cybersec_skill_for_prompt(doc: RawDocument, content: str) -> str:
    _, sections = markdown_sections(content)
    metadata = doc.metadata
    skill_name = str(metadata.get("skill_name") or doc.title).removeprefix("Skill: ")

    lines: list[str] = [f"# {skill_name}", ""]
    append_metadata_line(lines, "Domain", metadata.get("domain"))
    append_metadata_line(lines, "Subdomain", metadata.get("subdomain"))
    append_metadata_line(lines, "Tags", metadata.get("tags"))
    append_metadata_line(lines, "Tools referenced", metadata.get("tools_referenced"))
    append_metadata_line(lines, "MITRE ATT&CK", metadata.get("mitre_attack_ids"))
    append_metadata_line(lines, "MITRE ATLAS", metadata.get("mitre_atlas_ids"))
    append_metadata_line(lines, "D3FEND", metadata.get("d3fend_techniques"))
    append_metadata_line(lines, "NIST CSF", metadata.get("nist_csf"))
    source_path = metadata.get("source_path")
    if source_path:
        lines.append(f"**Source path**: {source_path}")
    lines.append("")

    description = section_body(sections, "Description") or str(
        metadata.get("description") or ""
    )
    if description:
        lines.extend(prompt_section("Description", description, DESCRIPTION_CHAR_LIMIT))

    framework_mappings = section_body(sections, "Framework Mappings")
    if framework_mappings:
        lines.extend(
            prompt_section("Framework Mappings", framework_mappings, SECTION_CHAR_LIMIT)
        )

    for heading in KEEP_SECTIONS:
        body = section_body(sections, heading)
        if body:
            lines.extend(prompt_section(heading, compact_code_blocks(body), SECTION_CHAR_LIMIT))

    workflow_body = section_body(sections, "Workflow")
    workflow_blocks = workflow_subsections(workflow_body)
    if workflow_blocks:
        selected_count = min(len(workflow_blocks), MAX_WORKFLOW_STEPS)
        lines.append("## Workflow")
        lines.append(
            f"Selected {selected_count} of {len(workflow_blocks)} workflow "
            "subsection(s), with large code blocks shortened."
        )
        lines.append("")
        for block in workflow_blocks[:MAX_WORKFLOW_STEPS]:
            lines.append(compact_workflow_block(block))
            lines.append("")
    else:
        workflow_steps = list_values(metadata.get("workflow_steps"))
        if workflow_steps:
            lines.append("## Workflow")
            for step in workflow_steps[:MAX_WORKFLOW_STEPS]:
                lines.append(f"- {step}")
            omitted = len(workflow_steps) - MAX_WORKFLOW_STEPS
            if omitted > 0:
                lines.append(f"- [{omitted} additional workflow step(s) omitted]")
            lines.append("")

    scenarios = list_values(metadata.get("scenarios"))
    if scenarios:
        lines.append("## Scenarios")
        for scenario in scenarios[:MAX_LIST_VALUES]:
            lines.append(f"- {scenario}")
        lines.append("")

    lines.append(
        "[Prompt compaction note: legal notices, long scripts/code blocks, "
        "references, and lower-priority workflow detail were shortened or omitted "
        "from this prompt. Full skill document remains in the raw corpus.]"
    )
    compacted = "\n".join(lines).strip()
    if len(compacted) >= len(content):
        return content
    return compacted


compact_for_prompt = compact_cybersec_skill_for_prompt


def append_metadata_line(lines: list[str], label: str, value: object) -> None:
    values = list_values(value)
    if not values:
        return
    suffix = ""
    if len(values) > MAX_LIST_VALUES:
        suffix = f" (+{len(values) - MAX_LIST_VALUES} more)"
    lines.append(f"**{label}**: {', '.join(values[:MAX_LIST_VALUES])}{suffix}")


def list_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def workflow_subsections(body: str) -> list[str]:
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


def compact_workflow_block(block: str) -> str:
    compacted = compact_code_blocks(block)
    return limit_text(compacted, WORKFLOW_STEP_CHAR_LIMIT)


def compact_code_blocks(text: str) -> str:
    lines: list[str] = []
    source_lines = text.splitlines()
    index = 0

    while index < len(source_lines):
        line = source_lines[index]
        if not line.startswith("```"):
            lines.append(line)
            index += 1
            continue

        fence = line
        language = fence.removeprefix("```").strip()
        code_lines: list[str] = []
        index += 1
        while index < len(source_lines) and not source_lines[index].startswith("```"):
            code_lines.append(source_lines[index])
            index += 1

        if index < len(source_lines):
            index += 1

        selected = trim_code_lines(code_lines)
        lines.append(fence)
        lines.extend(selected)
        omitted = len([code_line for code_line in code_lines if code_line.strip()]) - len(
            [code_line for code_line in selected if code_line.strip()]
        )
        if omitted > 0:
            label = f" {language}" if language else ""
            lines.append(f"# [{omitted} additional{label} code line(s) omitted]")
        lines.append("```")

    return "\n".join(lines).strip()


def trim_code_lines(code_lines: list[str]) -> list[str]:
    selected: list[str] = []
    used_chars = 0

    for line in code_lines:
        next_chars = used_chars + len(line) + 1
        if len(selected) >= MAX_CODE_BLOCK_LINES or next_chars > MAX_CODE_BLOCK_CHARS:
            break
        selected.append(line)
        used_chars = next_chars

    return selected
