"""AF3: LOLBAS + GTFOBins Collector.

Two repositories, one collector class with a unified output schema.
- LOLBAS: YAML files describing Windows LOLBins in yml/ directory
- GTFOBins: YAML files describing Linux binaries in _gtfobins/ directory
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any
from urllib.parse import quote

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class LOLBASGTFOBinsCollector(BaseCollector):

    LOLBAS_URL_CATEGORIES = {
        "OSBinaries": "Binaries",
        "OSLibraries": "Libraries",
        "OSScripts": "Scripts",
        "OtherMSBinaries": "OtherMSBinaries",
        "HonorableMentions": "HonorableMentions",
    }

    def __init__(self, config: dict):
        self.config = config
        self.lolbas_url = config["lolbas_url"]
        self.gtfobins_url = config["gtfobins_url"]
        self.output_dir = Path(config["output_dir"])
        self.lolbas_clone_path = Path(config["lolbas_clone_path"])
        self.gtfobins_clone_path = Path(config["gtfobins_clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _lolbas_source_url(self, file_path: Path) -> str:
        """Build the rendered LOLBAS site URL for a YAML entry."""
        category = self.LOLBAS_URL_CATEGORIES.get(file_path.parent.name)
        if category is None:
            name = file_path.stem
            category = "Libraries" if name.lower().endswith(".dll") else "Binaries"
        return (
            "https://lolbas-project.github.io/lolbas/"
            f"{category}/{quote(file_path.stem, safe='')}"
        )

    def _ordered_unique(self, values: list[str]) -> list[str]:
        """Deduplicate strings while preserving first-seen order."""
        seen = set()
        unique = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _extract_lolbas_paths(self, full_path: list) -> list[str]:
        """Extract path strings from LOLBAS Full_Path entries."""
        paths = []
        for item in full_path:
            if isinstance(item, dict):
                path = item.get("Path", "")
            else:
                path = item
            if path:
                paths.append(str(path))
        return paths

    def _parse_lolbas_entry(self, file_path: Path) -> RawDocument | None:
        """Parse a single LOLBAS YAML entry."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            data = yaml.safe_load(text)
            if not data or not isinstance(data, dict):
                return None

            name = data.get("Name", file_path.stem)
            description = data.get("Description", "")
            created = data.get("Created", "")

            commands = data.get("Commands", []) or []
            full_path = data.get("Full_Path", []) or []
            code_sample = data.get("Code_Sample", []) or []
            detection_list = data.get("Detection", []) or []
            resources = data.get("Resources", []) or []
            acknowledgements = data.get("Acknowledgement", []) or []

            lines = [
                f"# LOLBAS: {name}",
                "",
                f"**Platform**: Windows",
                f"**Description**: {description}",
            ]

            if full_path:
                lines.append("## Full Paths")
                for fp in full_path:
                    if isinstance(fp, dict):
                        lines.append(f"- `{fp.get('Path', '')}`")
                    else:
                        lines.append(f"- `{fp}`")
                lines.append("")

            if commands:
                lines.append("## Abuse Functions")
                lines.append("")
                for cmd in commands:
                    if not isinstance(cmd, dict):
                        continue
                    cmd_desc = cmd.get("Description", "")
                    command = cmd.get("Command", "")
                    usecase = cmd.get("Usecase", "")
                    category = cmd.get("Category", "")
                    privileges = cmd.get("Privileges", "")
                    mitre_id = cmd.get("MitreID", "")
                    operating_system = cmd.get("OperatingSystem", "")

                    lines.append(f"### {category}: {cmd_desc[:80]}")
                    if command:
                        lines.append(f"```\n{command}\n```")
                    if usecase:
                        lines.append(f"- **Use Case**: {usecase}")
                    if privileges:
                        lines.append(f"- **Privileges**: {privileges}")
                    if mitre_id:
                        lines.append(f"- **MITRE ATT&CK**: {mitre_id}")
                    if operating_system:
                        lines.append(f"- **OS**: {operating_system}")
                    lines.append("")

            if detection_list:
                lines.append("## Detection")
                for det in detection_list:
                    if isinstance(det, dict):
                        for key, val in det.items():
                            lines.append(f"- **{key}**: {val}")
                    else:
                        lines.append(f"- {det}")
                lines.append("")

            if resources:
                lines.append("## Resources")
                for res in resources:
                    if isinstance(res, dict):
                        lines.append(f"- {res.get('Link', res.get('URL', str(res)))}")
                    else:
                        lines.append(f"- {res}")
                lines.append("")

            markdown = self._to_markdown("\n".join(lines))

            # Extract MITRE IDs from commands
            mitre_ids = []
            categories = set()
            for cmd in commands:
                if isinstance(cmd, dict):
                    mid = cmd.get("MitreID", "")
                    if mid:
                        mitre_ids.append(str(mid))
                    cat = cmd.get("Category", "")
                    if cat:
                        categories.add(cat)
            mitre_ids = self._ordered_unique(mitre_ids)

            metadata: dict[str, Any] = {
                "binary_name": name,
                "platform": "windows",
                "lolbas_type": "lolbas",
                "lolbas_category": file_path.parent.name,
                "categories": sorted(categories),
                "mitre_attack_ids": mitre_ids,
                "command_count": len(commands),
                "full_paths": self._extract_lolbas_paths(full_path),
                "detections": detection_list,
                "resources": resources,
                "code_samples": code_sample,
                "acknowledgements": acknowledgements,
            }

            return RawDocument(
                doc_id=f"lolbas-{name.lower().replace('.', '-')}",
                source="lolbas_gtfobins",
                source_url=self._lolbas_source_url(file_path),
                title=f"LOLBAS: {name}",
                date_collected=date.today(),
                date_published=created,
                content_type="abuse_database",
                content_markdown=markdown,
                metadata=metadata,
                word_count=self._count_words(markdown),
            )

        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {file_path}: {e}")
        except Exception as e:
            self.warnings.append(f"Error processing LOLBAS {file_path}: {e}")
        return None

    def _parse_gtfobins_entry(self, file_path: Path) -> RawDocument | None:
        """Parse a single GTFOBins YAML entry."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            data = yaml.safe_load(text)
            if not data or not isinstance(data, dict):
                return None

            binary_name = file_path.stem
            functions = data.get("functions", {}) or {}

            if not functions:
                return None

            lines = [
                f"# GTFOBins: {binary_name}",
                "",
                f"**Platform**: Linux",
                "",
            ]

            for func_name, func_entries in functions.items():
                lines.append(f"## {func_name}")
                lines.append("")
                if not isinstance(func_entries, list):
                    continue
                for entry in func_entries:
                    if not isinstance(entry, dict):
                        continue
                    description = entry.get("description", "")
                    code = entry.get("code", "")

                    if description:
                        lines.append(description)
                    if code:
                        lines.append("```")
                        lines.append(str(code).strip())
                        lines.append("```")
                    lines.append("")

            markdown = self._to_markdown("\n".join(lines))

            function_names = sorted(functions.keys())

            metadata: dict[str, Any] = {
                "binary_name": binary_name,
                "platform": "linux",
                "lolbas_type": "gtfobins",
                "functions": function_names,
                "function_count": len(function_names),
            }

            return RawDocument(
                doc_id=f"gtfobins-{binary_name.lower()}",
                source="lolbas_gtfobins",
                source_url=f"https://gtfobins.github.io/gtfobins/{binary_name}/",
                title=f"GTFOBins: {binary_name}",
                date_collected=date.today(),
                date_published=None,
                content_type="abuse_database",
                content_markdown=markdown,
                metadata=metadata,
                word_count=self._count_words(markdown),
            )

        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {file_path}: {e}")
        except Exception as e:
            self.warnings.append(f"Error processing GTFOBins {file_path}: {e}")
        return None

    def collect(self) -> int:
        start_time = time()
        docs: list[RawDocument] = []
        lolbas_count = 0
        gtfobins_count = 0

        # Clone and parse LOLBAS
        try:
            self._clone_repo(
                self.lolbas_url,
                self.lolbas_clone_path,
                shallow=self.shallow_clone,
            )
            lolbas_yml_dir = self.lolbas_clone_path / "yml"
            if lolbas_yml_dir.exists():
                for yml_file in sorted(lolbas_yml_dir.rglob("*.yml")):
                    doc = self._parse_lolbas_entry(yml_file)
                    if doc:
                        docs.append(doc)
                        lolbas_count += 1
                logger.info(f"Parsed {lolbas_count} LOLBAS entries")
            else:
                self.warnings.append(
                    f"LOLBAS yml directory not found: {lolbas_yml_dir}"
                )
        except Exception as e:
            self.errors.append(f"Failed to clone/parse LOLBAS repo: {e}")

        # Clone and parse GTFOBins
        try:
            self._clone_repo(
                self.gtfobins_url,
                self.gtfobins_clone_path,
                shallow=self.shallow_clone,
            )
            gtfobins_dir = self.gtfobins_clone_path / "_gtfobins"
            if gtfobins_dir.exists():
                for bin_file in sorted(gtfobins_dir.iterdir()):
                    if bin_file.is_file() and not bin_file.name.startswith("."):
                        doc = self._parse_gtfobins_entry(bin_file)
                        if doc:
                            docs.append(doc)
                            gtfobins_count += 1
                logger.info(f"Parsed {gtfobins_count} GTFOBins entries")
            else:
                self.warnings.append(f"GTFOBins directory not found: {gtfobins_dir}")
        except Exception as e:
            self.errors.append(f"Failed to clone/parse GTFOBins repo: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "lolbas_gtfobins")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} LOLBAS/GTFOBins entries "
            f"in {self.duration:.1f}s"
        )
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=f"{self.lolbas_url} + {self.gtfobins_url}",
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=self.warnings,
            duration_seconds=self.duration,
        )
