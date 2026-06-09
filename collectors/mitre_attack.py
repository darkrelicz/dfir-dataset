from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import requests
from mitreattack.stix20 import MitreAttackData

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument


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
        target_file_path = self.output_dir / self.cache_path

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
            mitre_data = MitreAttackData(str(self.output_dir / self.cache_path))
        except Exception as e:
            self.errors.append(f"Failed to load MitreAttackData: {e}")
            self.duration = time() - start_time
            return 0

        docs = []

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

                platforms = technique.get("x_mitre_platforms", [])

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

                # detections 
                detections_raw = mitre_data.get_detection_strategies_detecting_technique(stix_id)
                detections = []
                for d in detections_raw:
                    # print(f"\n{d}")
                    det_list = d.get("relationships")

                    if not det_list:
                        continue

                    for item in det_list:
                        detection_obj = mitre_data.get_object_by_stix_id(item["source_ref"])
                        if detection_obj:
                            print(f"\n{detection_obj}")
                            name = detection_obj.name

                            description = "test"
                            detections.append(f"**{name}**: {description}")

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

                metadata = {
                    "data_sources": technique.get("x_mitre_data_sources", []),
                    "parent_technique": parent_mitre_id,
                    "author": technique.get("x_mitre_contributors", [])
                }

                doc = RawDocument(
                    doc_id=f"mitre-attack-{mitre_id}",
                    source="mitre_attack",
                    source_url="",
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

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}


if __name__ == "__main__":
    import yaml

    with open("configs/collection.yaml", "r") as f:
        full_config = yaml.safe_load(f)

    mitre_config = full_config["sources"]["mitre_attack"]
    collector = MitreAttackCollector(config=mitre_config)

    collector.collect()
    print(collector.manifest())