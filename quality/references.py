import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any

import yaml

from collectors.schemas import RawDocument


ATTACK_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
ATLAS_ID_RE = re.compile(r"\bAML\.T\d{4}(?:\.\d{3})?\b")
TACTICS_RE = re.compile(r"^\*\*Tactics\*\*:\s*(.+)$", re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{2,80})\]\([^)]+\)")


@dataclass
class QualityReferences:
    """Local Phase 4 reference sets derived from raw corpus and config."""

    taxonomy_refs: set[str] = field(default_factory=set)
    attack_ids: set[str] = field(default_factory=set)
    attack_tactics_by_id: dict[str, set[str]] = field(default_factory=dict)
    attack_tactics: set[str] = field(default_factory=set)
    atlas_ids: set[str] = field(default_factory=set)
    atlas_tactics_by_id: dict[str, set[str]] = field(default_factory=dict)
    atlas_tactics: set[str] = field(default_factory=set)
    tool_allowlist: set[str] = field(default_factory=set)


def build_quality_references(
    raw_docs_by_id: dict[str, RawDocument],
    quality_config: dict[str, Any],
    raw_dir: Path | None = None,
) -> QualityReferences:
    references = QualityReferences()
    references.taxonomy_refs = valid_taxonomy_refs_from_quality_config(quality_config)
    references.tool_allowlist = configured_tool_allowlist(quality_config)

    if raw_dir is not None:
        add_attack_stix_references(raw_dir, references)
        add_atlas_yaml_references(raw_dir, references)

    for doc in raw_docs_by_id.values():
        if doc.source == "mitre_attack":
            add_attack_reference(doc, references)
            add_markdown_link_names(doc.content_markdown, references.tool_allowlist)
        elif doc.source == "mitre_atlas":
            add_atlas_reference(doc, references)

        if doc.source in {
            "volatility3_docs",
            "velociraptor_artifacts",
            "kape_files",
            "lolbas_gtfobins",
            "cybersec_skills",
            "atomic_red_team",
            "forensic_artifacts",
        }:
            add_toolish_doc_names(doc, references.tool_allowlist)

    return references


def add_attack_stix_references(
    raw_dir: Path,
    references: QualityReferences,
) -> None:
    stix_path = raw_dir / ".cache" / "enterprise-attack.json"
    if not stix_path.exists():
        return

    try:
        bundle = json.loads(stix_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    for obj in bundle.get("objects", []):
        if not isinstance(obj, dict):
            continue
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue

        attack_id = attack_id_from_stix_object(obj)
        if not attack_id:
            continue

        tactics = tactics_from_stix_object(obj)
        references.attack_ids.add(attack_id)
        references.attack_tactics_by_id.setdefault(attack_id, set()).update(tactics)
        references.attack_tactics.update(tactics)


def attack_id_from_stix_object(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if not isinstance(ref, dict):
            continue
        if ref.get("source_name") != "mitre-attack":
            continue
        external_id = str(ref.get("external_id") or "")
        if ATTACK_ID_RE.fullmatch(external_id):
            return external_id
    return ""


def tactics_from_stix_object(obj: dict[str, Any]) -> set[str]:
    tactics: set[str] = set()
    for phase in obj.get("kill_chain_phases", []) or []:
        if not isinstance(phase, dict):
            continue
        if phase.get("kill_chain_name") != "mitre-attack":
            continue
        phase_name = str(phase.get("phase_name") or "").strip()
        if phase_name:
            tactics.add(phase_name)
    return tactics


def add_atlas_yaml_references(
    raw_dir: Path,
    references: QualityReferences,
) -> None:
    atlas_path = raw_dir / ".repos" / "atlas-data" / "dist" / "ATLAS.yaml"
    if not atlas_path.exists():
        return

    try:
        atlas = yaml.safe_load(atlas_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return

    if not isinstance(atlas, dict):
        return
    matrices = atlas.get("matrices")
    if not isinstance(matrices, list):
        return

    for matrix in matrices:
        if not isinstance(matrix, dict):
            continue
        tactics_by_id = atlas_tactics_by_id(matrix)
        technique_tactics: dict[str, set[str]] = {}
        techniques = matrix.get("techniques", [])
        if not isinstance(techniques, list):
            continue

        for technique in techniques:
            if not isinstance(technique, dict):
                continue
            atlas_id = str(technique.get("id") or "")
            if not ATLAS_ID_RE.fullmatch(atlas_id):
                continue
            tactics = atlas_technique_tactics(technique, tactics_by_id)
            technique_tactics[atlas_id] = tactics

        for technique in techniques:
            if not isinstance(technique, dict):
                continue
            atlas_id = str(technique.get("id") or "")
            if not ATLAS_ID_RE.fullmatch(atlas_id):
                continue
            if technique_tactics.get(atlas_id):
                continue
            parent_id = str(technique.get("specializes") or parent_atlas_id(atlas_id))
            if parent_id:
                technique_tactics[atlas_id] = set(technique_tactics.get(parent_id, set()))

        for atlas_id, tactics in technique_tactics.items():
            references.atlas_ids.add(atlas_id)
            references.atlas_tactics_by_id.setdefault(atlas_id, set()).update(tactics)
            references.atlas_tactics.update(tactics)


def atlas_tactics_by_id(matrix: dict[str, Any]) -> dict[str, str]:
    tactics_by_id: dict[str, str] = {}
    tactics = matrix.get("tactics", [])
    if not isinstance(tactics, list):
        return tactics_by_id
    for tactic in tactics:
        if not isinstance(tactic, dict):
            continue
        tactic_id = str(tactic.get("id") or "")
        if not tactic_id:
            continue
        tactics_by_id[tactic_id] = str(tactic.get("name") or tactic_id)
    return tactics_by_id


def atlas_technique_tactics(
    technique: dict[str, Any],
    tactics_by_id: dict[str, str],
) -> set[str]:
    tactics: set[str] = set()
    for tactic_id in technique.get("tactics", []) or []:
        tactic = tactics_by_id.get(str(tactic_id), str(tactic_id))
        if tactic:
            tactics.add(tactic)
    return tactics


def parent_atlas_id(atlas_id: str) -> str:
    parts = atlas_id.split(".")
    if len(parts) <= 2:
        return ""
    return ".".join(parts[:2])


def add_attack_reference(doc: RawDocument, references: QualityReferences) -> None:
    ids = set(ATTACK_ID_RE.findall(doc.doc_id))
    ids.update(ATTACK_ID_RE.findall(doc.title))
    ids.update(match for match in ATTACK_ID_RE.findall(doc.content_markdown[:200]))
    tactics = tactics_from_markdown(doc.content_markdown)
    for attack_id in ids:
        references.attack_ids.add(attack_id)
        references.attack_tactics_by_id.setdefault(attack_id, set()).update(tactics)
    references.attack_tactics.update(tactics)


def add_atlas_reference(doc: RawDocument, references: QualityReferences) -> None:
    atlas_id = str(doc.metadata.get("atlas_id") or "")
    if not atlas_id:
        ids = ATLAS_ID_RE.findall(doc.doc_id + " " + doc.title)
        atlas_id = ids[0] if ids else ""
    if not atlas_id:
        return

    tactics = references.atlas_tactics_by_id.get(atlas_id, set())
    if not tactics:
        tactics = {
            normalize_atlas_tactic(str(value))
            for value in doc.metadata.get("tactics", [])
            if normalize_atlas_tactic(str(value))
        }
    references.atlas_ids.add(atlas_id)
    references.atlas_tactics_by_id.setdefault(atlas_id, set()).update(tactics)
    references.atlas_tactics.update(tactics)


def normalize_atlas_tactic(value: str) -> str:
    tactic = value.strip()
    if tactic.startswith("AML.TA") and ":" in tactic:
        return tactic.split(":", 1)[1].strip()
    return tactic


def tactics_from_markdown(markdown: str) -> set[str]:
    match = TACTICS_RE.search(markdown)
    if not match:
        return set()
    return {
        value.strip()
        for value in match.group(1).split(",")
        if value.strip()
    }


def configured_tool_allowlist(quality_config: dict[str, Any]) -> set[str]:
    configured = quality_config.get("tools", {}).get("allowlist", [])
    return {
        normalize_tool_name(str(value))
        for value in configured
        if str(value).strip()
    }


def add_toolish_doc_names(doc: RawDocument, allowlist: set[str]) -> None:
    names = {doc.title}
    if ":" in doc.title:
        names.add(doc.title.split(":", 1)[0])
        names.add(doc.title.split(":", 1)[1])
    if doc.source == "velociraptor_artifacts":
        names.add("Velociraptor")
    if doc.source == "volatility3_docs":
        names.update({"Volatility 3", "Volatility3", "vol.py"})
    if doc.source == "kape_files":
        names.add("KAPE")
    for name in names:
        add_tool_name(name, allowlist)


def add_markdown_link_names(markdown: str, allowlist: set[str]) -> None:
    for name in MARKDOWN_LINK_RE.findall(markdown):
        if looks_like_tool_name(name):
            add_tool_name(name, allowlist)


def add_tool_name(name: str, allowlist: set[str]) -> None:
    normalized = normalize_tool_name(name)
    if normalized:
        allowlist.add(normalized)


def normalize_tool_name(name: str) -> str:
    value = name.strip().strip("`'\"")
    if not value:
        return ""
    value = value.replace("\\", "/")
    value = PureWindowsPath(value).name if "/" in value else value
    lowered = re.sub(r"\s+", " ", value).strip().lower()
    if lowered.endswith(".exe"):
        lowered = lowered[:-4]
    return lowered


def looks_like_tool_name(name: str) -> bool:
    lowered = name.lower()
    if lowered.startswith(("http", "citation", "attack.", "aml.")):
        return False
    return any(
        marker in lowered
        for marker in (
            ".exe",
            "dump",
            "cmd",
            "mimikatz",
            "impacket",
            "powershell",
            "sysmon",
            "velociraptor",
            "volatility",
            "yara",
        )
    )


def valid_taxonomy_refs_from_quality_config(quality_config: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for domain in quality_config.get("taxonomy", {}).get("domains", {}).values():
        refs.update(str(value) for value in domain.get("ids", []))
    return refs
