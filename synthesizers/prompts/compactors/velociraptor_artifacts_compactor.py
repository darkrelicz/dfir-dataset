import re
from collections.abc import Iterable

import yaml

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    COMPACTED_SOURCE_NOTE,
    limit_text,
)


YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
VQL_RE = re.compile(r"\b(?:LET|SELECT)\b", re.IGNORECASE)

DESCRIPTION_CHAR_LIMIT = 1800
PARAMETER_DESCRIPTION_CHAR_LIMIT = 260
PARAMETER_DEFAULT_CHAR_LIMIT = 220
REFERENCE_LIMIT = 12
STRUCTURED_DEFAULT_SCAN_LINES = 12


def compact_velociraptor_artifact_for_prompt(doc: RawDocument, content: str) -> str:
    artifact = parse_artifact_yaml(content)
    if not artifact:
        return content

    metadata = doc.metadata
    artifact_name = str(
        artifact.get("name") or metadata.get("artifact_name") or doc.title
    ).removeprefix("Velociraptor: ")

    lines: list[str] = [f"# Velociraptor Artifact: {artifact_name}", ""]
    append_metadata_line(lines, "Platform", metadata.get("os_platform"))
    append_metadata_line(lines, "Type", artifact.get("type") or metadata.get("artifact_type"))
    append_metadata_line(lines, "Content type", doc.content_type)
    append_metadata_line(lines, "Family", metadata.get("artifact_family"))
    append_metadata_line(lines, "Author", artifact.get("author") or metadata.get("author"))
    append_metadata_line(lines, "Tags", metadata.get("tags"))
    append_metadata_line(lines, "Required permissions", metadata.get("required_permissions"))
    append_metadata_line(lines, "Implied permissions", metadata.get("implied_permissions"))
    append_metadata_line(lines, "Tools", metadata.get("tools"))
    append_metadata_line(lines, "Source file", metadata.get("relative_path"))
    lines.append("")

    description = str(artifact.get("description") or "").strip()
    if description:
        lines.append("## Description")
        lines.append(limit_text(description, DESCRIPTION_CHAR_LIMIT))
        lines.append("")

    parameters = artifact.get("parameters") or []
    if parameters:
        lines.append("## Parameters")
        lines.extend(format_parameters(parameters))
        lines.append("")

    references = list_values(metadata.get("references")) or list_values(
        artifact.get("reference")
    )
    if references:
        lines.append("## References")
        for reference in references[:REFERENCE_LIMIT]:
            lines.append(f"- {reference}")
        omitted = len(references) - REFERENCE_LIMIT
        if omitted > 0:
            lines.append(f"- [{omitted} additional reference(s) omitted]")
        lines.append("")

    top_precondition = string_value(artifact.get("precondition"))
    if top_precondition:
        append_query_block(lines, "Artifact Precondition", top_precondition)

    export = string_value(artifact.get("export"))
    if export:
        append_query_block(lines, "Artifact Export", export)

    sources = artifact.get("sources") or []
    if sources:
        lines.append("## Sources")
        lines.append("")
        for index, source in enumerate(sources, start=1):
            if not isinstance(source, dict):
                continue
            source_name = str(source.get("name") or f"Source {index}")
            lines.append(f"### {source_name}")
            source_description = string_value(source.get("description"))
            if source_description:
                lines.append(limit_text(source_description, DESCRIPTION_CHAR_LIMIT))
                lines.append("")
            source_precondition = string_value(source.get("precondition"))
            if source_precondition:
                append_query_block(lines, f"{source_name} Precondition", source_precondition)
            append_source_queries(lines, source, source_name)

    reports = artifact.get("reports") or []
    if reports:
        lines.append("## Reports")
        lines.extend(format_reports(reports))
        lines.append("")

    lines.append(COMPACTED_SOURCE_NOTE)
    return "\n".join(lines).strip()


compact_for_prompt = compact_velociraptor_artifact_for_prompt
compact_for_prompt.skip_source_truncation = True


def parse_artifact_yaml(content: str) -> dict:
    match = YAML_BLOCK_RE.search(content)
    if not match:
        return {}
    try:
        artifact = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(artifact, dict):
        return {}
    return artifact


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


def string_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def format_parameters(parameters: list[object]) -> list[str]:
    lines: list[str] = []
    for index, parameter in enumerate(parameters, start=1):
        if not isinstance(parameter, dict):
            lines.append(f"- {parameter}")
            continue

        name = str(parameter.get("name") or f"Parameter {index}")
        pieces = [f"- **{name}**"]
        parameter_type = string_value(parameter.get("type"))
        if parameter_type:
            pieces.append(f"type={parameter_type}")
        description = string_value(parameter.get("description"))
        if description:
            pieces.append(
                "description="
                + limit_text(description, PARAMETER_DESCRIPTION_CHAR_LIMIT)
            )
        default = string_value(parameter.get("default"))
        default_block = parameter_default_block(default) if default else None
        if default:
            if default_block:
                block_label, _ = default_block
                pieces.append(f"default: see full {block_label} block below")
            else:
                pieces.append(
                    "default="
                    + limit_text(default, PARAMETER_DEFAULT_CHAR_LIMIT).replace(
                        "\n", " "
                    )
                )
        choices = parameter.get("choices")
        if choices:
            pieces.append(f"choices={', '.join(list_values(choices))}")
        lines.append("; ".join(pieces))

        if default and default_block:
            _, language = default_block
            append_fenced_block(lines, f"Parameter Default: {name}", default, language)
    return lines


def append_source_queries(
    lines: list[str],
    source: dict,
    source_name: str,
) -> None:
    query = source.get("query")
    if query:
        append_query_block(lines, f"{source_name} Query", string_value(query))

    queries = source.get("queries")
    if isinstance(queries, list):
        for index, query_item in enumerate(queries, start=1):
            append_query_block(
                lines,
                f"{source_name} Query {index}",
                string_value(query_item),
            )
    elif queries:
        append_query_block(lines, f"{source_name} Queries", string_value(queries))


def append_query_block(lines: list[str], heading: str, body: str) -> None:
    append_fenced_block(lines, heading, body, "vql")


def append_fenced_block(
    lines: list[str],
    heading: str,
    body: str,
    language: str,
) -> None:
    lines.append(f"## {heading}")
    lines.append(f"```{language}")
    lines.append(body.rstrip())
    lines.append("```")
    lines.append("")


def is_vql_like(text: str) -> bool:
    return bool(VQL_RE.search(text))


def parameter_default_block(text: str) -> tuple[str, str] | None:
    if is_vql_like(text):
        return "VQL", "vql"
    if is_structured_default(text):
        return "structured default", structured_default_language(text)
    return None


def is_structured_default(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) <= PARAMETER_DEFAULT_CHAR_LIMIT:
        return False

    lines = structured_lines(stripped)
    if not lines:
        return False
    if stripped.startswith(("[", "{")):
        return True
    if "%{" in stripped:
        return True
    if "HKEY_" in stripped and (
        "," in stripped or "*" in stripped or "\n" in stripped
    ):
        return True
    if stripped.count("|") >= 4:
        return True
    if looks_like_yara(lines):
        return True
    if any(
        line.startswith(("Glob", "KeyGlob", "remappings:"))
        for line in lines[:STRUCTURED_DEFAULT_SCAN_LINES]
    ):
        return True
    if csv_row_count(lines[:STRUCTURED_DEFAULT_SCAN_LINES]) >= 2:
        return True
    if yamlish_line_count(lines[:STRUCTURED_DEFAULT_SCAN_LINES]) >= 2:
        return True
    return path_glob_line_count(lines[:STRUCTURED_DEFAULT_SCAN_LINES]) >= 2


def structured_default_language(text: str) -> str:
    lines = structured_lines(text)
    stripped = text.lstrip()
    if looks_like_yara(lines):
        return "yara"
    if stripped.startswith(("[", "{")):
        return "json"
    if csv_row_count(lines[:STRUCTURED_DEFAULT_SCAN_LINES]) >= 2:
        return "csv"
    if yamlish_line_count(lines[:STRUCTURED_DEFAULT_SCAN_LINES]) >= 2:
        return "yaml"
    return "text"


def structured_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def looks_like_yara(lines: list[str]) -> bool:
    return any(
        line.startswith("rule ")
        for line in lines[:STRUCTURED_DEFAULT_SCAN_LINES]
    )


def csv_row_count(lines: list[str]) -> int:
    return sum(
        1
        for line in lines
        if "," in line and not line.startswith(("http://", "https://"))
    )


def yamlish_line_count(lines: list[str]) -> int:
    return sum(
        1
        for line in lines
        if line.startswith("- ") or (":" in line and not line.startswith(("http", "%{")))
    )


def path_glob_line_count(lines: list[str]) -> int:
    markers = ("/*", "/**", ":/", ":\\", "*.")
    return sum(1 for line in lines if any(marker in line for marker in markers))


def format_reports(reports: list[object]) -> list[str]:
    lines: list[str] = []
    for index, report in enumerate(reports, start=1):
        if not isinstance(report, dict):
            lines.append(f"- {limit_text(str(report), DESCRIPTION_CHAR_LIMIT)}")
            continue
        name = report.get("name") or f"Report {index}"
        lines.append(f"- **{name}**")
        template = string_value(report.get("template"))
        if template:
            lines.append("  - Template summary: " + limit_text(template, 500))
    return lines
