import hashlib
from pathlib import Path
from string import Template
from typing import Any

from collectors.schemas import RawDocument
from synthesizers.schemas import Difficulty, PromptRecord
from synthesizers.source_profiles import (
    content_profile_for_type,
    content_template_path,
    profile_for_source,
    source_template_path,
)


PROMPT_ROOT = Path(__file__).resolve().parent / "prompts"
NO_CONTENT_TYPE_INSTRUCTIONS = "No additional content-type-specific instructions."


def stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def difficulty_for_doc(doc: RawDocument) -> Difficulty:
    bucket = stable_index(doc.doc_id, 10)
    if bucket <= 2:
        return "junior"
    if bucket <= 7:
        return "mid"
    return "senior"


class PromptBuilder:
    def __init__(
        self,
        synthesis_config: dict[str, Any],
        task_config: dict[str, Any],
        prompt_root: Path = PROMPT_ROOT,
    ) -> None:
        self.synthesis_config = synthesis_config
        self.task_config = task_config
        self.prompt_root = prompt_root
        self.base_template = self._read_template(prompt_root / "base.md")

    def build(self, doc: RawDocument) -> PromptRecord:
        profile = profile_for_source(doc.source)
        category = self._category_for_doc(doc)
        difficulty = difficulty_for_doc(doc)
        category_instructions = self._read_template(
            self.prompt_root / "categories" / self._category_template(category)
        )
        source_type_instructions = self._read_template(
            source_template_path(doc.source, self.prompt_root)
        )
        content_type_instructions = self._content_type_instructions(doc)
        pairs_requested = self._pairs_for_doc(doc)

        prompt = Template(self.base_template).safe_substitute(
            category_name=category,
            category_specific_instructions=category_instructions,
            source_type=profile.source_type,
            source_type_instructions=source_type_instructions,
            content_type=doc.content_type,
            content_type_instructions=content_type_instructions,
            document_content=self._document_content_for_prompt(doc),
            doc_id=doc.doc_id,
            source=doc.source,
            title=doc.title,
            difficulty=difficulty,
            pairs_requested=pairs_requested,
        )

        prompt_id = f"prompt-{doc.doc_id}-{category}-{difficulty}"
        return PromptRecord(
            prompt_id=prompt_id,
            source_doc_id=doc.doc_id,
            source=doc.source,
            source_type=profile.source_type,
            content_type=doc.content_type,
            category=category,
            difficulty=difficulty,
            pairs_requested=pairs_requested,
            prompt=prompt,
        )

    def _category_for_doc(self, doc: RawDocument) -> str:
        categories = profile_for_source(doc.source).categories
        return categories[stable_index(doc.doc_id, len(categories))]

    def _category_template(self, category: str) -> str:
        categories = self.task_config.get("categories", {})
        try:
            return str(categories[category]["prompt_template"])
        except KeyError as exc:
            raise KeyError(f"No category prompt template configured for {category}") from exc

    def _pairs_for_doc(self, doc: RawDocument) -> int:
        configured = int(
            self.synthesis_config["generation"]["pairs_per_document"][doc.source]
        )
        profile = profile_for_source(doc.source)
        content_profile = content_profile_for_type(doc.content_type)
        pairs = configured

        if doc.word_count < 250:
            return 1
        if profile.thin_source:
            pairs = min(pairs, 2)
        if content_profile.thin_source:
            pairs = min(pairs, 2)
        if content_profile.max_pairs is not None:
            pairs = min(pairs, content_profile.max_pairs)
        return pairs

    def _content_type_instructions(self, doc: RawDocument) -> str:
        path = content_template_path(doc.content_type, self.prompt_root)
        if path is None:
            return NO_CONTENT_TYPE_INSTRUCTIONS
        return self._read_template(path)

    def _document_content_for_prompt(self, doc: RawDocument) -> str:
        max_chars = int(
            self.synthesis_config.get("generation", {}).get("max_source_chars", 24000)
        )
        content = doc.content_markdown.strip()
        if len(content) <= max_chars:
            return content

        head_chars = max_chars * 2 // 3
        tail_chars = max_chars - head_chars
        return (
            content[:head_chars].rstrip()
            + "\n\n[TRUNCATED FOR PROMPT SIZE: middle of source document omitted]\n\n"
            + content[-tail_chars:].lstrip()
        )

    def _read_template(self, path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()
