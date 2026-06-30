"""Prompt-time source document compaction.

Raw Phase 2 documents stay complete. This layer creates shorter, deterministic
source views for Phase 3 prompts. Source-specific compactors live next to this
file and should follow the naming convention `<source>_compactor.py`.
"""

from collections.abc import Callable
from importlib import import_module

from collectors.schemas import RawDocument


COMPACTOR_PACKAGE = "synthesizers.prompts.compactors"
COMPACTED_SOURCE_NOTE = (
    "[Compacted source view: repeated or lower-priority blocks were omitted. "
    "Use only visible details as evidence.]"
)
Compactor = Callable[[RawDocument, str], str]


def compact_document_for_prompt(doc: RawDocument, max_chars: int) -> str:
    content = doc.content_markdown.strip()
    compactor = compactor_for_source(doc.source)
    if compactor is not None:
        content = compactor(doc, content)
        if getattr(compactor, "skip_source_truncation", False):
            return content
    return truncate_content_for_prompt(content, max_chars)


def compactor_for_source(source: str) -> Compactor | None:
    module_name = f"{COMPACTOR_PACKAGE}.{source}_compactor"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise
    return getattr(module, "compact_for_prompt")


def truncate_content_for_prompt(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content

    head_chars = max_chars * 2 // 3
    tail_chars = max_chars - head_chars
    return (
        content[:head_chars].rstrip()
        + "\n\n[TRUNCATED FOR PROMPT SIZE: middle of source document omitted]\n\n"
        + content[-tail_chars:].lstrip()
    )


def markdown_sections(content: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_heading is None:
                preamble = current_lines
            else:
                sections.append((current_heading, current_lines))
            current_heading = line.removeprefix("## ").strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_heading is None:
        preamble = current_lines
    else:
        sections.append((current_heading, current_lines))
    return preamble, sections


def section_body(sections: list[tuple[str, list[str]]], heading: str) -> str:
    bodies = ["\n".join(lines).strip() for name, lines in sections if name == heading]
    return "\n\n".join(body for body in bodies if body)


def prompt_section(heading: str, body: str, char_limit: int) -> list[str]:
    return [f"## {heading}", limit_text(body, char_limit), ""]


def limit_text(text: str, char_limit: int) -> str:
    text = text.strip()
    if len(text) <= char_limit:
        return text
    return text[:char_limit].rstrip() + "\n[truncated]"


def single_line(text: str) -> str:
    return " ".join(text.strip().split())
