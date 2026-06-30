import json
from pathlib import Path
from string import Template
from typing import Any

from collectors.schemas import RawDocument
from synthesizers.prompt_policy import load_prompt_policy
from synthesizers.prompts.compactors.prompt_compactors import compact_document_for_prompt
from synthesizers.schemas import Difficulty, PromptRecord
from synthesizers.source_profiles import content_profile_for_type, profile_for_source

PROMPT_ROOT = Path(__file__).resolve().parent / "prompts"
NO_CONTENT_TYPE_INSTRUCTIONS = "No additional content-type-specific instructions."

SOURCE_TAXONOMY_REFS: dict[str, tuple[str, ...]] = {
    "cybersec_skills": ("S1", "TI1"),
    "forensic_artifacts": ("W4", "L4"),
    "kape_files": ("W4", "W6"),
    "mitre_atlas": ("A1", "A2"),
    "ossem_data_dicts": ("W8", "S1"),
    "sigma_rules": ("S3", "W8"),
    "hayabusa_rules": ("S3", "W8"),
    "volatility3_docs": ("W7",),
    "lolbas_gtfobins": ("AF3",),
    "hijacklibs": ("AF3",),
    "loldrivers": ("AF3",),
    "cisa_advisories": ("TI1", "N4"),
    "cisa_kev": ("TI1",),
    "velociraptor_artifacts": ("S1",),
}

CONTENT_TYPE_TAXONOMY_REFS: dict[str, tuple[str, ...]] = {
    "atomic_test": ("W1", "L1"),
    "case_study": ("TI1",),
    "event_dictionary": ("W8", "S1"),
    "hayabusa_rule": ("S3", "W8"),
    "lolbas_windows_lolbin": ("AF3", "W1"),
    "sigma_rule": ("S3", "W8"),
    "gtfobins_linux_abuse_function": ("AF3", "L1"),
    "gtfobins_linux_alias": ("AF3", "L1"),
    "tool_module": ("W7",),
    "tool_plugin": ("W7",),
    "velociraptor_client_artifact": ("S1",),
    "velociraptor_event_artifact": ("S1",),
    "velociraptor_internal_artifact": ("S1",),
    "velociraptor_notebook": ("S1",),
    "velociraptor_report_template": ("S1",),
    "velociraptor_server_artifact": ("S1",),
    "vulnerability_catalog": ("TI1",),
}

CATEGORY_TAXONOMY_REFS: dict[str, tuple[str, ...]] = {
    "detection_engineering": ("S3",),
}

TACTIC_TAXONOMY_REFS: dict[str, tuple[str, ...]] = {
    "collection": ("W4", "L4"),
    "command-and-control": ("N4", "N3"),
    "credential-access": ("W3", "L3"),
    "defense-impairment": ("AF1", "AF3"),
    "defense-evasion": ("AF3", "W8"),
    "discovery": ("W1", "L1"),
    "execution": ("W1", "L1"),
    "exfiltration": ("N5", "W5", "L5"),
    "impact": ("AF2",),
    "initial-access": ("W3", "N3"),
    "lateral-movement": ("W3", "W9"),
    "persistence": ("W2", "L2"),
    "privilege-escalation": ("W2", "L2"),
    "reconnaissance": ("TI1",),
    "resource-development": ("TI1", "SC1"),
    "stealth": ("AF3", "AF1"),
}

PLATFORM_TAXONOMY_REFS: dict[str, tuple[str, ...]] = {
    "containers": ("L8",),
    "esxi": ("V1",),
    "iaas": ("C1", "C4"),
    "linux": ("L6",),
    "macos": ("L6",),
    "network devices": ("N1",),
    "pre": ("TI1",),
    "saas": ("C6",),
    "windows": ("W8",),
}


class PromptBuilder:
    def __init__(
        self,
        synthesis_config: dict[str, Any],
        task_config: dict[str, Any],
        prompt_root: Path = PROMPT_ROOT,
    ) -> None:
        self.synthesis_config = synthesis_config
        self.prompt_root = prompt_root
        self.policy = load_prompt_policy(task_config, prompt_root)
        self.base_template = self._read_template(prompt_root / "base.md")

    def build(
        self,
        doc: RawDocument,
        category: str,
        difficulty: Difficulty,
    ) -> PromptRecord:
        if not category:
            raise ValueError("PromptBuilder.build requires category")
        if not difficulty:
            raise ValueError("PromptBuilder.build requires difficulty")

        profile = profile_for_source(doc.source)
        category_instructions = self._read_template(
            self.prompt_root
            / "categories"
            / self.policy.category_template(category)
        )
        source_type_instructions = self._read_template(
            self.prompt_root / "source_types" / profile.prompt_template
        )
        content_type_instructions = self._content_type_instructions(doc)
        pairs_requested = self.pairs_for_doc(doc)
        taxonomy_refs = self._taxonomy_refs_for_prompt(doc, category)

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
            taxonomy_refs=json.dumps(list(taxonomy_refs)),
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
            taxonomy_refs=list(taxonomy_refs),
            prompt=prompt,
        )

    def categories_for_doc(self, doc: RawDocument) -> tuple[str, ...]:
        return profile_for_source(doc.source).categories

    def pairs_for_doc(self, doc: RawDocument) -> int:
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
        profile = content_profile_for_type(doc.content_type)
        if not profile.prompt_template:
            return NO_CONTENT_TYPE_INSTRUCTIONS
        path = self.prompt_root / "content_types" / profile.prompt_template
        return self._read_template(path)

    def _document_content_for_prompt(self, doc: RawDocument) -> str:
        max_chars = int(
            self.synthesis_config.get("generation", {}).get("max_source_chars", 24000)
        )
        return compact_document_for_prompt(
            doc,
            max_chars=max_chars,
        )

    def _taxonomy_refs_for_prompt(
        self,
        doc: RawDocument,
        category: str,
    ) -> tuple[str, ...]:
        refs: list[str] = []

        def add(candidates: tuple[str, ...]) -> None:
            for candidate in candidates:
                if candidate not in refs:
                    refs.append(candidate)

        for tactic in self._mitre_tactics(doc):
            add(TACTIC_TAXONOMY_REFS.get(tactic, ()))
        add(CONTENT_TYPE_TAXONOMY_REFS.get(doc.content_type, ()))
        add(SOURCE_TAXONOMY_REFS.get(doc.source, ()))
        add(CATEGORY_TAXONOMY_REFS.get(category, ()))
        if not refs:
            for platform in self._mitre_platforms(doc):
                add(PLATFORM_TAXONOMY_REFS.get(platform, ()))
        if not refs:
            add(("S1",))
        return tuple(refs[:3])

    def _mitre_tactics(self, doc: RawDocument) -> tuple[str, ...]:
        for line in doc.content_markdown.lower().splitlines():
            if not line.startswith("**tactics**:"):
                continue
            raw_tactics = line.split(":", 1)[1]
            return tuple(value.strip() for value in raw_tactics.split(","))
        return ()

    def _mitre_platforms(self, doc: RawDocument) -> tuple[str, ...]:
        for line in doc.content_markdown.lower().splitlines():
            if not line.startswith("**platforms**:"):
                continue
            raw_platforms = line.split(":", 1)[1]
            return tuple(value.strip() for value in raw_platforms.split(","))
        return ()

    def _read_template(self, path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()
