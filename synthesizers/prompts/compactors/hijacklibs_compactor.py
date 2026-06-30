from collections.abc import Iterable

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    COMPACTED_SOURCE_NOTE,
    markdown_sections,
    section_body,
)


MAX_EXECUTABLES = 28
MAX_EXECUTABLE_HASHES = 4
MAX_RESOURCES = 8
MAX_SIGNATURE_DETAILS = 2


def compact_hijacklib_for_prompt(doc: RawDocument, content: str) -> str:
    metadata = doc.metadata
    dll_name = str(metadata.get("dll_name") or doc.title.removeprefix("HijackLibs: "))
    lines: list[str] = [f"# HijackLibs: {dll_name}", ""]

    append_metadata_line(lines, "DLL Name", dll_name)
    append_metadata_line(lines, "Vendor", metadata.get("vendor"))
    append_metadata_line(lines, "Hijack Types", metadata.get("hijack_types"))
    append_metadata_line(lines, "MITRE ATT&CK", metadata.get("mitre_attack_ids"))
    append_metadata_line(lines, "CVEs", metadata.get("cves"))
    executable_count = int(metadata.get("vulnerable_exe_count") or 0)
    if executable_count:
        lines.append(f"**Vulnerable executable count**: {executable_count}")
    lines.append("")

    expected_locations = list_values(metadata.get("expected_locations"))
    if expected_locations:
        lines.append("## Expected Locations")
        for location in expected_locations:
            lines.append(f"- `{location}`")
        lines.append("")

    executables = select_executables(metadata.get("vulnerable_executables") or [])
    if executables:
        lines.append("## Vulnerable Executables")
        lines.append(
            f"Selected {len(executables)} of {executable_count or len(executables)} "
            "executable block(s), prioritizing auto-elevated, privilege-escalation, "
            "conditional, variable-based, and hashed entries."
        )
        lines.append("")
        for executable in executables:
            lines.append(format_executable(executable))
            lines.append("")

    _, sections = markdown_sections(content)
    resources = list_items(section_body(sections, "Resources"))
    if resources:
        lines.append("## Resources")
        for resource in resources[:MAX_RESOURCES]:
            lines.append(f"- {resource}")
        omitted = len(resources) - MAX_RESOURCES
        if omitted > 0:
            lines.append(f"- [{omitted} additional resource(s) omitted]")
        lines.append("")

    lines.append(COMPACTED_SOURCE_NOTE)

    compacted = "\n".join(lines).strip()
    if len(compacted) >= len(content):
        return content
    return compacted


compact_for_prompt = compact_hijacklib_for_prompt


def append_metadata_line(lines: list[str], label: str, value: object) -> None:
    values = list_values(value)
    if values:
        lines.append(f"**{label}**: {', '.join(values)}")


def list_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def select_executables(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    if len(value) <= MAX_EXECUTABLES:
        return [item for item in value if isinstance(item, dict)]

    scored = [
        (executable_score(executable), index, executable)
        for index, executable in enumerate(value)
        if isinstance(executable, dict)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = scored[:MAX_EXECUTABLES]
    selected.sort(key=lambda item: item[1])
    return [executable for _, _, executable in selected]


def executable_score(executable: dict) -> int:
    score = 0
    if executable.get("auto_elevate"):
        score += 8
    if executable.get("privilege_escalation"):
        score += 8
    if executable.get("condition"):
        score += 4
    if executable.get("variable"):
        score += 4
    if executable.get("sha256_hashes"):
        score += 3
    if executable.get("expected_version_information"):
        score += 1
    if executable.get("expected_signature_information"):
        score += 1
    return score


def format_executable(executable: dict) -> str:
    path = executable.get("path") or "Unknown executable"
    lines = [f"### `{path}`"]
    if executable.get("type"):
        lines.append(f"- **Hijack Type**: {executable['type']}")
    if executable.get("condition"):
        lines.append(f"- **Condition**: {executable['condition']}")
    if executable.get("variable"):
        lines.append(f"- **Variable**: `{executable['variable']}`")

    sha256_hashes = list_values(executable.get("sha256_hashes"))
    if sha256_hashes:
        lines.append("- **SHA256**:")
        for hash_value in sha256_hashes[:MAX_EXECUTABLE_HASHES]:
            lines.append(f"  - `{hash_value}`")
        omitted = len(sha256_hashes) - MAX_EXECUTABLE_HASHES
        if omitted > 0:
            lines.append(f"  - [{omitted} additional hash value(s) omitted]")

    if executable.get("auto_elevate"):
        lines.append("- **Auto-Elevated**: Yes")
    if executable.get("privilege_escalation"):
        lines.append("- **Privilege Escalation**: Yes")

    append_detail_summary(
        lines,
        "Expected Version Information",
        executable.get("expected_version_information"),
    )
    append_detail_summary(
        lines,
        "Expected Signature Information",
        executable.get("expected_signature_information"),
    )
    return "\n".join(lines)


def append_detail_summary(lines: list[str], label: str, value: object) -> None:
    if not isinstance(value, list) or not value:
        return
    lines.append(f"- **{label}**:")
    for item in value[:MAX_SIGNATURE_DETAILS]:
        if isinstance(item, dict):
            parts = [
                f"{key}={item_value}"
                for key, item_value in item.items()
                if item_value not in ("", None, [])
            ]
            if parts:
                lines.append(f"  - {'; '.join(parts)}")
        elif item not in ("", None, []):
            lines.append(f"  - {item}")
    omitted = len(value) - MAX_SIGNATURE_DETAILS
    if omitted > 0:
        lines.append(f"  - [{omitted} additional detail item(s) omitted]")


def list_items(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line.removeprefix("- ").strip())
    return items
