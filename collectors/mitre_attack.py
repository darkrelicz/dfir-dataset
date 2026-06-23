import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time

import requests
from charset_normalizer.api import logger
from mitreattack.stix20 import MitreAttackData

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class MitreAttackCollector(BaseCollector):
    def __init__(self, config: dict):
        self.config = config
        self.file = config["file"]
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.cache_path = Path(config["cache_path"])
        self.include_revoked_deprecated = config.get("include_revoked_deprecated", False)

        self.errors = []
        self.warnings = []
        self.duration = 0.0
        self.doc_count = 0

    def _download_stix_data(self):
        target_file_path = self.cache_path

        if target_file_path.exists():
            return

        target_file_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(self.url, timeout=60)
        resp.raise_for_status()

        with open(target_file_path, "wb") as f:
            f.write(resp.content)

    def collect(self) -> int:
        start_time = time()

        try:
            self._download_stix_data()
        except Exception as e:
            self.errors.append(f"Failed to download MITRE ATT&CK STIX Data: {e}")
            self.duration = time() - start_time
            return 0

        try:
            mitre_data = MitreAttackData(str(self.cache_path))
        except Exception as e:
            self.errors.append(f"Failed to load MitreAttackData: {e}")
            self.duration = time() - start_time
            return 0

        logger.info(f"Loaded enterprise-attack.json to {self.cache_path}")
        docs: list[RawDocument] = []

        techniques = mitre_data.get_techniques(remove_revoked_deprecated=not self.include_revoked_deprecated)
        for technique in techniques:
            try:
                stix_id = technique["id"]
                technique_name = technique.get("name", "Unknown")

                mitre_id = ""
                for ext_ref in technique["external_references"]:
                    if ext_ref["source_name"] == "mitre-attack":
                        mitre_id = ext_ref["external_id"]
                        break

                if not mitre_id:
                    self.warnings.append(f"No MITRE ID found for {technique_name}")

                tactics = []
                if technique["kill_chain_phases"]:
                    tactics = [
                        phase["phase_name"]
                        for phase in technique["kill_chain_phases"]
                        if phase["kill_chain_name"] == "mitre-attack"
                    ]

                is_subtechnique = technique["x_mitre_is_subtechnique"]
                parent_ref = []
                parent_mitre_id = ""
                if is_subtechnique:
                    parent_ref = mitre_data.get_parent_technique_of_subtechnique(stix_id)

                if parent_ref and parent_ref[0]["object"]:
                    parent_object = parent_ref[0]["object"]
                    for parent_ext_ref in parent_object["external_references"]:
                        if parent_ext_ref["source_name"] == "mitre-attack":
                            parent_mitre_id = parent_ext_ref["external_id"]
                            break

                procedures_raw = mitre_data.get_procedure_examples_by_technique(stix_id)
                procedures = []
                for p in procedures_raw:
                    group_or_software = mitre_data.get_object_by_stix_id(p["source_ref"])
                    if group_or_software:
                        name = group_or_software.name
                        description = p.get("description")
                        procedures.append(f"**{name}**: {description}")
                    
                mitigations_raw = mitre_data.get_mitigations_mitigating_technique(stix_id)
                mitigations = []
                for m in mitigations_raw:
                    mit_list = m.get("relationships")
                    
                    if not mit_list:
                        continue
                    
                    for item in mit_list:
                        mitigation_obj = mitre_data.get_object_by_stix_id(item["source_ref"])
                        if mitigation_obj:
                            name = mitigation_obj.name
                            description = item["description"]
                            mitigations.append(f"**{name}**: {description}")

                detections_raw = mitre_data.get_detection_strategies_detecting_technique(stix_id)
                detections = []
                for d in detections_raw:
                    strategy_obj = d.get("object")
                    if not strategy_obj:
                        continue
                    
                    strategy_name = getattr(strategy_obj, "name", "Unknown Strategy")
                    
                    analytic_refs = getattr(strategy_obj, "x_mitre_analytic_refs", [])
                    analytic_descriptions = []
                    
                    for ref in analytic_refs:
                        analytic_obj = mitre_data.get_object_by_stix_id(ref)
                        if analytic_obj and hasattr(analytic_obj, "description") and analytic_obj.description:
                            analytic_descriptions.append(analytic_obj.description)
                    
                    description = " ".join(analytic_descriptions) if analytic_descriptions else "No description available."
                    
                    detections.append(f"**{strategy_name}**: {description}")

                platforms = technique.get("x_mitre_platforms", [])

                markdown_lines = [
                    f"# {mitre_id}: {technique_name}",
                    "",
                    f"**Tactics**: {', '.join(tactics)}",
                    f"**Platforms**: {', '.join(platforms)}",
                    "",
                    "## Description",
                    str(technique["description"]),
                    ""
                ]

                if procedures:
                    markdown_lines.append("## Procedures")
                    for procedure in procedures:
                        markdown_lines.append(f"- {procedure}")
                    markdown_lines.append("")

                if mitigations:
                    markdown_lines.append("## Mitigations")
                    for mitigation in mitigations:
                        markdown_lines.append(f"- {mitigation}")
                    markdown_lines.append("")

                if detections:
                    markdown_lines.append("## Detections")
                    for detection in detections:
                        markdown_lines.append(f"- {detection}")
                    markdown_lines.append("")

                markdown_doc = self._to_markdown("\n".join(markdown_lines))

                data_sources_raw = technique.get("external_references", [])
                data_sources = []
                for ds in data_sources_raw:
                    name = ds.get("source_name", "unknown source")
                    url = ds.get("url", "Unknown URL")
                    data_sources.append((name, url))

                metadata = {
                    "data_sources": data_sources,
                    "parent_technique": parent_mitre_id,
                    "contributors": technique.get("x_mitre_contributors", [])
                }

                doc = RawDocument(
                    doc_id=f"mitre-attack-{mitre_id}",
                    source="mitre_attack",
                    source_url=f"https://attack.mitre.org/techniques/{mitre_id.replace('.', '/')}",
                    title=technique_name,
                    date_collected=date.today(),
                    date_published=technique["created"],
                    content_type="technique_definition",
                    content_markdown=markdown_doc,
                    metadata=metadata,
                    word_count=self._count_words(markdown_doc),
                )
                docs.append(doc)

            except Exception as e:
                self.warnings.append(
                    f"Failed to process technique {technique.get('name', 'Unknown')}: {e}"
                )

        if not docs:
            self.warnings.append("No MITRE ATT&CK documents were collected; nothing was written.")

        self.doc_count = self._write_documents(docs, self.output_dir, "mitre_attack")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} MITRE ATT&CK rules in {self.duration:.1f}s")
        return self.doc_count

    def manifest(self):
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
