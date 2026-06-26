"""C6: MITRE ATLAS Collector.

Clones the MITRE ATLAS data repository and collects ATLAS techniques,
mitigations, and case studies from the v6 distributable YAML files.
"""

import logging
import sys
import types
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import current_commit, github_blob_url
from utils.io import load_yaml
from utils.text import to_markdown, count_words

logger = logging.getLogger(__name__)

class MitreAtlasCollector(BaseCollector):
    """Collect MITRE ATLAS data from atlas-data."""

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _load_atlas_parser(self):
        """Load AtlasExport without importing atlas-data's API/database stack."""
        atlas_dir = self.clone_path / "atlas"
        if not atlas_dir.exists():
            raise FileNotFoundError(f"ATLAS parser package not found: {atlas_dir}")

        package = types.ModuleType("atlas")
        package.__path__ = [str(atlas_dir)]
        package.__package__ = "atlas"
        sys.modules["atlas"] = package

        from atlas.enums import AtlasRelationshipType
        from atlas.schemas import AtlasExport

        return AtlasExport, AtlasRelationshipType

    def _get_source_commit(self) -> str:
        """Return the cloned repository commit, falling back to main."""
        return current_commit(
            self.clone_path,
            "main",
            label="ATLAS source",
            on_error=self.warnings.append,
        )

    def _github_url(self, rel_path: str | Path, source_commit: str) -> str:
        """Build a GitHub source URL pinned to the collected commit."""
        return github_blob_url(self.url, source_commit, rel_path)
    
    def _select_latest_v6_yaml(self) -> Path | None:
        """Select the newest v6 ATLAS YAML from dist/manifest.yaml."""
        dist_dir = self.clone_path / "dist"
        manifest_path = dist_dir / "manifest.yaml"
        if not manifest_path.exists():
            self.errors.append(f"ATLAS manifest not found: {manifest_path}")
            return None

        try:
            manifest = load_yaml(manifest_path, default={})
        except Exception as e:
            self.errors.append(f"Failed to parse ATLAS manifest: {e}")
            return None

        if not isinstance(manifest, list):
            self.errors.append(f"ATLAS manifest has unexpected shape: {manifest_path}")
            return None

        for release in manifest:
            for version in release.get("versions", []) or []:
                rel_path = str(version.get("path", ""))
                if rel_path.startswith("v6/"):
                    return dist_dir / rel_path

        self.errors.append("Could not locate latest v6 ATLAS YAML in atlas-data/dist")
        return None

    def _enum_value(self, value: Any) -> Any:
        """Return enum values as strings for markdown and JSON metadata."""
        return getattr(value, "value", value)

    def _enum_values(self, values: Any) -> list[str]:
        """Return a list of enum/string values."""
        return [str(self._enum_value(value)) for value in values or []]

    def _description(self, value: Any) -> str:
        """Normalize multi-line descriptions without changing markdown links."""
        if value is None:
            return ""
        return str(value).strip()

    def _relation_description(self, value: Any) -> str:
        """Normalize relationship prose for bullet lists."""
        return " ".join(str(value or "").strip().split())

    def _object_label(self, objects: dict[str, Any], object_id: str) -> str:
        """Return a stable ATLAS label for an object ID."""
        obj = objects.get(object_id)
        if obj is None:
            return object_id
        return f"{object_id}: {obj.name}"

    def _object_link(
        self,
        objects: dict[str, Any],
        object_id: str,
        object_type: str,
    ) -> str:
        """Return a markdown link to an official ATLAS object page."""
        label = self._object_label(objects, object_id)
        if object_type == "technique":
            url = f"https://atlas.mitre.org/techniques/{object_id}"
        elif object_type == "mitigation":
            url = f"https://atlas.mitre.org/mitigations/{object_id}"
        elif object_type == "case-study":
            url = f"https://atlas.mitre.org/studies/{object_id}"
        else:
            return label
        return f"[{label}]({url})"

    def _reference_lines(self, refs: Any) -> list[str]:
        """Render ATLAS reference objects as markdown bullets."""
        return [f"- [{ref.title}]({ref.url})" for ref in refs]

    def _append_references(self, lines: list[str], refs: Any) -> None:
        """Append a References section if references exist."""
        ref_lines = self._reference_lines(refs)
        if not ref_lines:
            return

        lines.extend(["", "## References"])
        lines.extend(ref_lines)

    def _relationship_indexes(
        self, relationships: dict[str, dict], relationship_type: Any
    ) -> dict[str, Any]:
        """Build lookup indexes from AtlasExport relationship groups."""
        technique_tactics: dict[str, list[str]] = defaultdict(list)
        parent_by_technique: dict[str, str] = {}
        mitigations_by_technique: dict[str, list[Any]] = defaultdict(list)
        techniques_by_mitigation: dict[str, list[Any]] = defaultdict(list)
        cases_by_technique: dict[str, list[Any]] = defaultdict(list)
        techniques_by_case: dict[str, list[Any]] = defaultdict(list)

        for source_id, groups in relationships.items():
            source_id = str(source_id)

            for rel in groups.get(relationship_type.ACHIEVES, []):
                technique_tactics[source_id].append(str(rel.target))

            for rel in groups.get(relationship_type.SPECIALIZES, []):
                parent_by_technique[source_id] = str(rel.target)

            for rel in groups.get(relationship_type.MITIGATES, []):
                source = str(rel.source)
                target = str(rel.target)
                mitigations_by_technique[target].append(rel)
                techniques_by_mitigation[source].append(rel)

            for rel in groups.get(relationship_type.EMPLOYS, []):
                source = str(rel.source)
                target = str(rel.target)
                cases_by_technique[target].append(rel)
                techniques_by_case[source].append(rel)

        return {
            "technique_tactics": dict(technique_tactics),
            "parent_by_technique": parent_by_technique,
            "mitigations_by_technique": dict(mitigations_by_technique),
            "techniques_by_mitigation": dict(techniques_by_mitigation),
            "cases_by_technique": dict(cases_by_technique),
            "techniques_by_case": dict(techniques_by_case),
        }

    def _unique_ids(self, values: list[str]) -> list[str]:
        """Return unique IDs while preserving first-seen order."""
        seen = set()
        unique = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _common_metadata(
        self,
        obj: Any,
        atlas_data: Any,
        source_commit: str,
        source_file: str,
        source_file_url: str,
    ) -> dict[str, Any]:
        """Build common compact metadata for ATLAS documents."""
        return {
            "atlas_id": str(obj.id),
            "uuid": str(obj.uuid),
            "framework": "atlas",
            "collection_version": str(atlas_data.collection.version),
            "format_version": str(atlas_data.format_version),
            "modified": obj.modified_date.isoformat(),
            "source_commit": source_commit,
            "source_file": source_file,
            "source_file_url": source_file_url,
        }

    def _tactic_labels(
        self,
        tactic_ids: list[str],
        tactics: dict[str, Any],
    ) -> list[str]:
        """Return compact tactic labels."""
        return [
            self._object_label(tactics, tactic_id)
            for tactic_id in self._unique_ids(tactic_ids)
        ]

    def _attack_reference(self, obj: Any) -> dict[str, str] | None:
        """Extract ATT&CK overlap reference from an ATLAS object."""
        attack_ref = obj.attack_reference
        if not attack_ref:
            return None
        return {
            "attack_id": str(attack_ref.id),
            "url": str(attack_ref.url),
        }

    def _build_technique_doc(
        self,
        obj: Any,
        atlas_data: Any,
        indexes: dict[str, Any],
        tactics: dict[str, Any],
        mitigations: dict[str, Any],
        cases: dict[str, Any],
        source_commit: str,
        source_file: str,
        source_file_url: str,
    ) -> RawDocument:
        """Build a RawDocument for an ATLAS technique."""
        atlas_id = str(obj.id)
        name = obj.name
        tactic_ids = indexes["technique_tactics"].get(atlas_id, [])
        tactic_labels = self._tactic_labels(tactic_ids, tactics)
        platforms = self._enum_values(obj.platforms)
        maturity = str(self._enum_value(obj.maturity))
        parent_id = indexes["parent_by_technique"].get(atlas_id, "")
        attack_ref = self._attack_reference(obj)

        lines = [
            f"# {atlas_id}: {name}",
            "",
            "**Framework**: MITRE ATLAS",
        ]
        lines.append(f"**Tactics**: {', '.join(tactic_labels)}")
        lines.append(f"**Platforms**: {', '.join(platforms)}")
        lines.append(f"**Maturity**: {maturity}")
        if parent_id:
            lines.append(
                "**Parent Technique**: "
                f"{self._object_link(atlas_data.techniques, parent_id, 'technique')}"
            )

        lines.extend(["", "## Description", self._description(obj.description)])

        if attack_ref:
            lines.extend(["", "## ATT&CK Overlap"])
            if attack_ref["url"]:
                lines.append(f"- [{attack_ref['attack_id']}]({attack_ref['url']})")
            else:
                lines.append(f"- {attack_ref['attack_id']}")

        case_rels = indexes["cases_by_technique"].get(atlas_id, [])
        if case_rels:
            lines.extend(["", "## Related Case Studies"])
            for rel in sorted(case_rels, key=lambda r: str(r.source)):
                case_id = str(rel.source)
                description = self._relation_description(rel.description)
                line = f"- {self._object_link(cases, case_id, 'case-study')}"
                if description:
                    line = f"{line}: {description}"
                lines.append(line)

        mitigation_rels = indexes["mitigations_by_technique"].get(atlas_id, [])
        if mitigation_rels:
            lines.extend(["", "## Mitigations"])
            for rel in sorted(mitigation_rels, key=lambda r: str(r.source)):
                mitigation_id = str(rel.source)
                description = self._relation_description(rel.description)
                line = f"- {self._object_link(mitigations, mitigation_id, 'mitigation')}"
                if description:
                    line = f"{line}: {description}"
                lines.append(line)

        self._append_references(lines, obj.references)

        markdown = to_markdown("\n".join(lines))
        metadata = self._common_metadata(
            obj,
            atlas_data,
            source_commit,
            source_file,
            source_file_url,
        )
        metadata.update(
            {
                "tactics": tactic_labels,
                "platforms": platforms,
                "maturity": maturity,
                "attack_reference": attack_ref,
                "parent_technique_id": parent_id,
                "mitigation_ids": self._unique_ids(
                    [str(rel.source) for rel in mitigation_rels]
                ),
                "case_study_ids": self._unique_ids(
                    [str(rel.source) for rel in case_rels]
                ),
            }
        )

        return RawDocument(
            doc_id=f"atlas-{atlas_id}",
            source="mitre_atlas",
            source_url=f"https://atlas.mitre.org/techniques/{atlas_id}",
            title=name,
            date_collected=date.today(),
            date_published=obj.created_date,
            content_type="technique_definition",
            content_markdown=markdown,
            metadata=metadata,
            word_count=count_words(markdown),
        )

    def _build_mitigation_doc(
        self,
        obj: Any,
        atlas_data: Any,
        indexes: dict[str, Any],
        techniques: dict[str, Any],
        source_commit: str,
        source_file: str,
        source_file_url: str,
    ) -> RawDocument:
        """Build a RawDocument for an ATLAS mitigation."""
        atlas_id = str(obj.id)
        name = obj.name
        categories = self._enum_values(obj.categories)
        lifecycle_phases = self._enum_values(obj.lifecycle_phases)

        lines = [
            f"# {atlas_id}: {name}",
            "",
            "**Type**: ATLAS Mitigation",
        ]
        lines.append(f"**Categories**: {', '.join(categories)}")
        lines.append(f"**Life Cycle Phases**: {', '.join(lifecycle_phases)}")

        lines.extend(["", "## Description", self._description(obj.description)])

        technique_rels = indexes["techniques_by_mitigation"].get(atlas_id, [])
        if technique_rels:
            lines.extend(["", "## Related Techniques"])
            for rel in sorted(technique_rels, key=lambda r: str(r.target)):
                technique_id = str(rel.target)
                description = self._relation_description(rel.description)
                line = f"- {self._object_link(techniques, technique_id, 'technique')}"
                if description:
                    line = f"{line}: {description}"
                lines.append(line)

        self._append_references(lines, obj.references)

        markdown = to_markdown("\n".join(lines))
        metadata = self._common_metadata(
            obj,
            atlas_data,
            source_commit,
            source_file,
            source_file_url,
        )
        metadata.update(
            {
                "categories": categories,
                "lifecycle_phases": lifecycle_phases,
                "related_technique_ids": self._unique_ids(
                    [str(rel.target) for rel in technique_rels]
                ),
            }
        )

        return RawDocument(
            doc_id=f"atlas-mit-{atlas_id}",
            source="mitre_atlas",
            source_url=f"https://atlas.mitre.org/mitigations/{atlas_id}",
            title=f"ATLAS Mitigation: {name}",
            date_collected=date.today(),
            date_published=obj.created_date,
            content_type="mitigation",
            content_markdown=markdown,
            metadata=metadata,
            word_count=count_words(markdown),
        )

    def _build_case_doc(
        self,
        obj: Any,
        atlas_data: Any,
        indexes: dict[str, Any],
        techniques: dict[str, Any],
        tactics: dict[str, Any],
        source_commit: str,
        source_file: str,
        source_file_url: str,
    ) -> RawDocument:
        """Build a RawDocument for an ATLAS case study."""
        case_id = str(obj.id)
        name = obj.name
        case_type = str(self._enum_value(obj.type))
        actor = obj.actor
        target = obj.target
        event_date = obj.date.isoformat()
        date_granularity = str(self._enum_value(obj.date_granularity))

        lines = [
            f"# {case_id}: {name}",
            "",
            "**Type**: ATLAS Case Study",
        ]
        lines.append(f"**Case Type**: {case_type}")
        lines.append(f"**Actor**: {actor}")
        lines.append(f"**Target**: {target}")
        lines.append(f"**Event Date**: {event_date}")
        lines.append(f"**Date Granularity**: {date_granularity}")

        lines.extend(["", "## Description", self._description(obj.description)])

        technique_rels = indexes["techniques_by_case"].get(case_id, [])
        if technique_rels:
            lines.extend(["", "## Observed Procedure Steps"])
            for rel in sorted(technique_rels, key=lambda r: str(r.step_id or "")):
                step_id = str(rel.step_id or "Step")
                technique_id = str(rel.target)
                tactic_id = str(rel.tactic or "")
                description = self._description(rel.description)

                lines.append(
                    f"### {step_id}: "
                    f"{self._object_label(techniques, technique_id)}"
                )
                if tactic_id:
                    lines.append(f"**Tactic**: {self._object_label(tactics, tactic_id)}")
                if rel.leads_to:
                    lines.append(f"**Leads To**: {', '.join(rel.leads_to)}")
                if description:
                    lines.append(description)
                lines.append("")

            lines.append("## Related Techniques")
            for technique_id in self._unique_ids(
                [str(rel.target) for rel in technique_rels]
            ):
                lines.append(
                    f"- {self._object_link(techniques, technique_id, 'technique')}"
                )

        self._append_references(lines, obj.references)

        markdown = to_markdown("\n".join(lines))
        metadata = self._common_metadata(
            obj,
            atlas_data,
            source_commit,
            source_file,
            source_file_url,
        )
        metadata.update(
            {
                "case_type": case_type,
                "actor": actor,
                "target": target,
                "event_date": event_date,
                "date_granularity": date_granularity,
                "related_technique_ids": self._unique_ids(
                    [str(rel.target) for rel in technique_rels]
                ),
            }
        )

        return RawDocument(
            doc_id=f"atlas-case-{case_id}",
            source="mitre_atlas",
            source_url=f"https://atlas.mitre.org/studies/{case_id}",
            title=f"ATLAS Case Study: {name}",
            date_collected=date.today(),
            date_published=obj.date,
            content_type="case_study",
            content_markdown=markdown,
            metadata=metadata,
            word_count=count_words(markdown),
        )

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone MITRE ATLAS data repo: {e}")
            self.duration = time() - start_time
            return 0

        source_commit = self._get_source_commit()
        atlas_path = self._select_latest_v6_yaml()
        if atlas_path is None:
            self.duration = time() - start_time
            return 0

        try:
            raw = load_yaml(atlas_path, default={})
            AtlasExport, AtlasRelationshipType = self._load_atlas_parser()
            atlas_data = AtlasExport.model_validate(raw)
        except Exception as e:
            self.errors.append(f"Failed to parse ATLAS YAML with AtlasExport: {e}")
            self.duration = time() - start_time
            return 0

        indexes = self._relationship_indexes(
            atlas_data.relationships,
            AtlasRelationshipType,
        )

        source_file = atlas_path.relative_to(self.clone_path).as_posix()
        source_file_url = self._github_url(source_file, source_commit)

        docs: list[RawDocument] = []
        for technique_id in sorted(atlas_data.techniques):
            try:
                docs.append(
                    self._build_technique_doc(
                        obj=atlas_data.techniques[technique_id],
                        atlas_data=atlas_data,
                        indexes=indexes,
                        tactics=atlas_data.tactics,
                        mitigations=atlas_data.mitigations,
                        cases=atlas_data.case_studies,
                        source_commit=source_commit,
                        source_file=source_file,
                        source_file_url=source_file_url,
                    )
                )
            except Exception as e:
                self.warnings.append(
                    f"Failed to process ATLAS technique {technique_id}: {e}"
                )

        for mitigation_id in sorted(atlas_data.mitigations):
            try:
                docs.append(
                    self._build_mitigation_doc(
                        obj=atlas_data.mitigations[mitigation_id],
                        atlas_data=atlas_data,
                        indexes=indexes,
                        techniques=atlas_data.techniques,
                        source_commit=source_commit,
                        source_file=source_file,
                        source_file_url=source_file_url,
                    )
                )
            except Exception as e:
                self.warnings.append(
                    f"Failed to process ATLAS mitigation {mitigation_id}: {e}"
                )

        for case_id in sorted(atlas_data.case_studies):
            try:
                docs.append(
                    self._build_case_doc(
                        obj=atlas_data.case_studies[case_id],
                        atlas_data=atlas_data,
                        indexes=indexes,
                        techniques=atlas_data.techniques,
                        tactics=atlas_data.tactics,
                        source_commit=source_commit,
                        source_file=source_file,
                        source_file_url=source_file_url,
                    )
                )
            except Exception as e:
                self.warnings.append(
                    f"Failed to process ATLAS case study {case_id}: {e}"
                )

        if not docs:
            self.warnings.append("No MITRE ATLAS documents were collected.")

        self.doc_count = self._write_documents(docs, self.output_dir, "mitre_atlas")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} ATLAS documents in {self.duration:.1f}s"
        )
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=self.config["url"],
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=self.warnings,
            duration_seconds=self.duration,
        )
