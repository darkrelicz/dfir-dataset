import datetime
import time
from pathlib import Path
from typing import Any

import requests
from mitreattack.stix20 import MitreAttackData

from collectors.base import BaseCollector
from collectors.schemas import RawDocument

class MitreAttackCollector(BaseCollector):
    SOURCE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    LICENSE = "MITRE Copyright"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.stix_url = config.get("stix_url", self.SOURCE_URL)
        self.cache_path = Path(config.get("cache_path", "data/raw/.cache/enterprise-attack.json"))
        self.include_deprecated = config.get("include_deprecated", False)
        self.include_revoked = config.get("include_revoked", False)
        
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.doc_count = 0
        self.duration = 0.0

    def _download_stix(self):
        if self.cache_path.exists():
            return
            
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(self.stix_url, timeout=60)
        resp.raise_for_status()
        
        with open(self.cache_path, "wb") as f:
            f.write(resp.content)

    def collect(self, output_dir: Path) -> int:
        start_time = time.time()
        try:
            self._download_stix()
        except Exception as e:
            self.errors.append(f"Failed to download MITRE STIX: {e}")
            self.duration = time.time() - start_time
            return 0

        try:
            mitre_data = MitreAttackData(str(self.cache_path))
        except Exception as e:
            self.errors.append(f"Failed to load MitreAttackData: {e}")
            self.duration = time.time() - start_time
            return 0

        docs = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        techniques = mitre_data.get_techniques(remove_revoked=not self.include_revoked, remove_deprecated=not self.include_deprecated)
        
        for technique in techniques:
            try:
                stix_id = technique.id
                mitre_id = ""
                for ext_ref in technique.external_references:
                    if ext_ref.source_name == "mitre-attack":
                        mitre_id = ext_ref.external_id
                        break
                        
                if not mitre_id:
                    self.warnings.append(f"No MITRE ID found for {technique.name}")
                    continue

                tactics = []
                if hasattr(technique, "kill_chain_phases"):
                    tactics = [phase.phase_name for phase in technique.kill_chain_phases if phase.kill_chain_name == "mitre-attack"]

                is_subtechnique = technique.get("x_mitre_is_subtechnique", False)
                parent_technique = ""
                if is_subtechnique:
                    parent_ref = mitre_data.get_parent_technique_of_subtechnique(stix_id)
                    if parent_ref and parent_ref[0].get("object"):
                        for ref in parent_ref[0].get("object").external_references:
                            if ref.source_name == "mitre-attack":
                                parent_technique = ref.external_id
                                break

                platforms = technique.get("x_mitre_platforms", [])
                data_sources = technique.get("x_mitre_data_sources", [])
                detection = technique.get("x_mitre_detection", "")
                
                procedures_raw = mitre_data.get_procedure_examples_by_technique(stix_id)
                procedures = []
                for p in procedures_raw:
                    group_or_software = mitre_data.get_object_by_stix_id(p.source_ref)
                    if group_or_software:
                        name = group_or_software.name
                        desc = p.description if hasattr(p, "description") else ""
                        procedures.append(f"**{name}**: {desc}")

                mitigations_raw = mitre_data.get_mitigations_mitigating_technique(stix_id)
                mitigations = []
                for m in mitigations_raw:
                    mit_obj = mitre_data.get_object_by_stix_id(m.source_ref)
                    if mit_obj:
                        name = mit_obj.name
                        desc = m.description if hasattr(m, "description") else ""
                        mitigations.append(f"**{name}**: {desc}")

                markdown_lines = [
                    f"# {mitre_id}: {technique.name}",
                    "",
                    f"**Tactics:** {', '.join(tactics)}",
                    f"**Platforms:** {', '.join(platforms)}",
                    "",
                    "## Description",
                    str(technique.description) if hasattr(technique, "description") else "",
                    ""
                ]

                if procedures:
                    markdown_lines.append("## Procedures")
                    for proc in procedures:
                        markdown_lines.append(f"- {proc}")
                    markdown_lines.append("")

                if detection:
                    markdown_lines.append("## Detection")
                    markdown_lines.append(str(detection))
                    markdown_lines.append("")

                if mitigations:
                    markdown_lines.append("## Mitigations")
                    for mit in mitigations:
                        markdown_lines.append(f"- {mit}")
                    markdown_lines.append("")

                content_markdown = self._to_markdown("\n".join(markdown_lines))

                doc = RawDocument(
                    doc_id=f"mitre-attack-{mitre_id}",
                    source="mitre_attack",
                    source_url=f"https://attack.mitre.org/techniques/{mitre_id.replace('.', '/')}",
                    title=str(technique.name),
                    date_collected=collected_at,
                    date_published=str(technique.created) if hasattr(technique, "created") else None,
                    content_type="technique_definition",
                    content_markdown=content_markdown,
                    metadata={
                        "mitre_id": mitre_id,
                        "tactic": tactics,
                        "platforms": platforms,
                        "data_sources": data_sources,
                        "detection": bool(detection),
                        "procedures": [p for p in procedures],
                        "mitigations": [m for m in mitigations],
                        "is_subtechnique": is_subtechnique,
                        "parent_technique": parent_technique
                    },
                    license=self.LICENSE,
                    word_count=self._count_words(content_markdown)
                )
                docs.append(doc)
            except Exception as e:
                self.warnings.append(f"Failed to process technique {getattr(technique, 'name', 'Unknown')}: {e}")

        self.doc_count = self._write_documents(docs, output_dir, "mitre_attack")
        self.duration = time.time() - start_time
        return self.doc_count

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}

    def manifest(self) -> dict[str, Any]:
        return {
            "collector": "MitreAttackCollector",
            "version": self.VERSION,
            "source_url": self.stix_url,
            "license": self.LICENSE,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_count": self.doc_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration
        }
