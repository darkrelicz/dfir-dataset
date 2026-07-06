import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

from validation.taxonomy import get_taxonomy_refs_from_config

ATTACK_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")
ATLAS_ID_RE = re.compile(r"\bAML\.T\d{4}(?:\.\d{3})?\b")


@dataclass
class QualityReferences:
    """Local Phase 4 reference sets derived from raw corpus and config."""

    taxonomy_refs: set[str] = field(default_factory=set)
    attack_ids: set[str] = field(default_factory=set)
    atlas_ids: set[str] = field(default_factory=set)
    tool_allowlist: set[str] = field(default_factory=set)


def build_quality_references(quality_config: dict[str, Any], raw_dir: Path) -> QualityReferences:
    references = QualityReferences()
    references.taxonomy_refs = get_taxonomy_refs_from_config(quality_config)
    references.tool_allowlist = get_configured_tool_allowlist(quality_config)

    add_attack_ids_from_stix_cache(raw_dir, references)
    add_atlas_ids_from_stix_cache(raw_dir, references)

    return references


def add_attack_ids_from_stix_cache(raw_dir: Path, references: QualityReferences) -> None:
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

        references.attack_ids.add(attack_id)


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


def add_atlas_ids_from_stix_cache(raw_dir: Path, references: QualityReferences) -> None:
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
        techniques = matrix.get("techniques", [])
        if not isinstance(techniques, list):
            continue

        for technique in techniques:
            if not isinstance(technique, dict):
                continue
            atlas_id = str(technique.get("id") or "")
            if not ATLAS_ID_RE.fullmatch(atlas_id):
                continue
            references.atlas_ids.add(atlas_id)


def get_configured_tool_allowlist(quality_config: dict[str, Any]) -> set[str]:
    configured = quality_config.get("tools", {}).get("allowlist", [])
    return {
        normalize_tool_name(str(value))
        for value in configured
        if str(value).strip()
    }


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
