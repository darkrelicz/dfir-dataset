"""AF3: LOLBAS + GTFOBins Collector.

Two repositories, one collector class with a unified output schema.
- LOLBAS: YAML files describing Windows LOLBins in yml/ directory
- GTFOBins: YAML files describing Linux binaries in _gtfobins/ directory
"""
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from urllib.parse import quote

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class LOLBASGTFOBinsCollector(BaseCollector):
    MAX_MARKDOWN_FULL_PATHS = 20

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
        category = self.LOLBAS_URL_CATEGORIES.get(file_path.parent.name)
        if category is None:
            category = (
                "Libraries"
                if file_path.stem.lower().endswith(".dll")
                else "Binaries"
            )
        return (
            "https://lolbas-project.github.io/lolbas/"
            f"{category}/{quote(file_path.stem, safe='')}"
        )

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def _parse_lolbas_entry(self, file_path: Path) -> RawDocument | None:
        """Parse a single LOLBAS YAML entry."""
        try:
            data = yaml.safe_load(
                file_path.read_text(encoding="utf-8", errors="replace")
            )
            if not data:
                return None

            name = data.get("Name", file_path.stem)
            commands = data.get("Commands", []) or []
            detections = data.get("Detection", []) or []
            resources = data.get("Resources", []) or []
            aliases = [
                str(item.get("Alias") if isinstance(item, dict) else item)
                for item in data.get("Aliases", []) or []
            ]
            full_paths = [
                str(item.get("Path") if isinstance(item, dict) else item)
                for item in data.get("Full_Path", []) or []
            ]

            lines = [
                f"# LOLBAS: {name}",
                "",
                "**Platform**: Windows",
                f"**Description**: {data.get('Description', '')}",
            ]
            if data.get("Author"):
                lines.append(f"**Author**: {data['Author']}")
            if aliases:
                lines.append(f"**Aliases**: {', '.join(aliases)}")
            lines.append("")

            if full_paths:
                lines.append("## Full Paths")
                for path in full_paths[:self.MAX_MARKDOWN_FULL_PATHS]:
                    lines.append(f"- `{path}`")
                omitted = len(full_paths) - self.MAX_MARKDOWN_FULL_PATHS
                if omitted > 0:
                    lines.append(
                        f"- ... {omitted} additional paths omitted; "
                        "see metadata.full_paths"
                    )
                lines.append("")

            mitre_ids = []
            categories = []
            command_tags = []

            lines.extend(["## Abuse Functions", ""])
            for cmd in commands:
                category = cmd.get("Category", "")
                command = cmd.get("Command", "")
                description = cmd.get("Description", "")
                tags = []
                for tag in cmd.get("Tags", []) or []:
                    if isinstance(tag, dict):
                        tags.extend(f"{key}: {value}" for key, value in tag.items())
                    else:
                        tags.append(str(tag))

                categories.append(category)
                command_tags.extend(tags)
                if cmd.get("MitreID"):
                    mitre_ids.append(str(cmd["MitreID"]))

                language = "powershell" if "powershell" in command.lower() else "cmd"
                lines.append(f"### {category}: {description}")
                if command:
                    lines.extend([f"```{language}", command.strip(), "```"])
                if cmd.get("Usecase"):
                    lines.append(f"- **Use Case**: {cmd['Usecase']}")
                if cmd.get("Privileges"):
                    lines.append(f"- **Privileges**: {cmd['Privileges']}")
                if cmd.get("MitreID"):
                    lines.append(f"- **MITRE ATT&CK**: {cmd['MitreID']}")
                if cmd.get("OperatingSystem"):
                    lines.append(f"- **OS**: {cmd['OperatingSystem']}")
                if tags:
                    lines.append(f"- **Tags**: {', '.join(tags)}")
                lines.append("")

            if detections:
                lines.append("## Detection")
                for detection in detections:
                    if isinstance(detection, dict):
                        for key, value in detection.items():
                            lines.append(f"- **{key}**: {value}")
                    else:
                        lines.append(f"- {detection}")
                lines.append("")

            if resources:
                lines.append("## Resources")
                for resource in resources:
                    link = (
                        resource.get("Link", resource)
                        if isinstance(resource, dict)
                        else resource
                    )
                    lines.append(f"- {link}")
                lines.append("")

            detection_types = []
            for detection in detections:
                if isinstance(detection, dict):
                    detection_types.extend(detection.keys())

            markdown = self._to_markdown("\n".join(lines))
            created = data.get("Created", "")

            return RawDocument(
                doc_id=f"lolbas-{self._slug(name)}",
                source="lolbas_gtfobins",
                source_url=self._lolbas_source_url(file_path),
                title=f"LOLBAS: {name}",
                date_collected=date.today(),
                date_published=created,
                content_type="lolbas_windows_lolbin",
                content_markdown=markdown,
                metadata={
                    "binary_name": name,
                    "platform": "windows",
                    "lolbas_type": "lolbas",
                    "lolbas_category": file_path.parent.name,
                    "author": str(data.get("Author", "")),
                    "created": str(created) if created else "",
                    "aliases": aliases,
                    "categories": sorted(self._unique(categories)),
                    "mitre_attack_ids": self._unique(mitre_ids),
                    "command_tags": self._unique(command_tags),
                    "command_count": len(commands),
                    "full_paths": full_paths,
                    "detection_types": self._unique(
                        [str(item) for item in detection_types]
                    ),
                    "detections": detections,
                    "resources": resources,
                    "code_samples": data.get("Code_Sample", []) or [],
                    "acknowledgements": data.get("Acknowledgement", []) or [],
                },
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
            data = yaml.safe_load(
                file_path.read_text(encoding="utf-8", errors="replace")
            )
            if not data:
                return None

            binary_name = file_path.stem
            functions = data.get("functions", {}) or {}
            alias_target = data.get("alias", "")
            source_url = f"https://gtfobins.github.io/gtfobins/{quote(binary_name, safe='')}/"

            if alias_target and not functions:
                markdown = self._to_markdown(
                    "\n".join(
                        [
                            f"# GTFOBins Alias: {binary_name}",
                            "",
                            "**Platform**: Linux",
                            f"**Alias Target**: {alias_target}",
                            "",
                            f"`{binary_name}` is an alias of `{alias_target}` "
                            "in GTFOBins.",
                        ]
                    )
                )
                return RawDocument(
                    doc_id=f"gtfobins-{self._slug(binary_name)}",
                    source="lolbas_gtfobins",
                    source_url=source_url,
                    title=f"GTFOBins Alias: {binary_name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="gtfobins_linux_alias",
                    content_markdown=markdown,
                    metadata={
                        "binary_name": binary_name,
                        "platform": "linux",
                        "lolbas_type": "gtfobins",
                        "alias_target": str(alias_target),
                        "functions": [],
                        "function_count": 0,
                        "entry_count": 0,
                    },
                    word_count=self._count_words(markdown),
                )

            if not functions:
                return None

            lines = [f"# GTFOBins: {binary_name}", "", "**Platform**: Linux"]
            if data.get("comment"):
                lines.append(f"**Note**: {data['comment']}")
            lines.append("")

            contexts = []
            inherited_from = []
            senders = []
            receivers = []
            listeners = []
            connectors = []
            versions = []
            comments = []
            has_tty = False
            binary_false_count = 0
            entry_count = 0

            for func_name, entries in functions.items():
                lines.extend([f"## {func_name}", ""])
                for entry in entries or []:
                    entry_count += 1
                    entry_contexts = entry.get("contexts", {}) or {}
                    contexts.extend(entry_contexts.keys())

                    if entry.get("comment"):
                        comments.append(str(entry["comment"]))
                        lines.extend([str(entry["comment"]), ""])
                    if entry.get("code"):
                        lines.extend(["```bash", str(entry["code"]).strip(), "```"])
                    if entry.get("from"):
                        inherited_from.append(str(entry["from"]))
                        lines.append(f"- **Inherits From**: {entry['from']}")
                    if "binary" in entry:
                        lines.append(f"- **Requires Binary**: {entry['binary']}")
                        if entry["binary"] is False:
                            binary_false_count += 1
                    if entry.get("version"):
                        versions.append(str(entry["version"]))
                        lines.append(f"- **Version**: {entry['version']}")
                    if entry.get("tty"):
                        has_tty = True
                        lines.append("- **TTY Required**: true")

                    for label, key, bucket in [
                        ("Sender", "sender", senders),
                        ("Receiver", "receiver", receivers),
                        ("Listener", "listener", listeners),
                        ("Connector", "connector", connectors),
                    ]:
                        value = entry.get(key)
                        if value:
                            name = (
                                "custom-code" if isinstance(value, dict) else str(value)
                            )
                            bucket.append(name)
                            lines.append(f"- **{label}**: {name}")

                    if entry_contexts:
                        lines.append(f"- **Contexts**: {', '.join(entry_contexts)}")
                        for context_name, context_data in entry_contexts.items():
                            if not context_data:
                                continue
                            lines.append(f"#### {context_name} context")
                            if context_data.get("code"):
                                lines.extend(
                                    [
                                        "```bash",
                                        str(context_data["code"]).strip(),
                                        "```",
                                    ]
                                )
                            if context_data.get("list"):
                                values = ", ".join(
                                    str(item) for item in context_data["list"]
                                )
                                lines.append(f"- **Values**: {values}")
                            if "shell" in context_data:
                                lines.append(
                                    f"- **Spawns Shell**: {context_data['shell']}"
                                )
                            if context_data.get("comment"):
                                lines.append(f"- **Note**: {context_data['comment']}")
                    lines.append("")

            markdown = self._to_markdown("\n".join(lines))
            function_names = sorted(functions.keys())

            return RawDocument(
                doc_id=f"gtfobins-{self._slug(binary_name)}",
                source="lolbas_gtfobins",
                source_url=source_url,
                title=f"GTFOBins: {binary_name}",
                date_collected=date.today(),
                date_published=None,
                content_type="gtfobins_linux_abuse_function",
                content_markdown=markdown,
                metadata={
                    "binary_name": binary_name,
                    "platform": "linux",
                    "lolbas_type": "gtfobins",
                    "functions": function_names,
                    "function_count": len(function_names),
                    "alias_target": str(alias_target or ""),
                    "entry_count": entry_count,
                    "contexts": self._unique([str(item) for item in contexts]),
                    "inherited_from": self._unique(inherited_from),
                    "senders": self._unique(senders),
                    "receivers": self._unique(receivers),
                    "listeners": self._unique(listeners),
                    "connectors": self._unique(connectors),
                    "versions": self._unique(versions),
                    "has_tty": has_tty,
                    "binary_false_count": binary_false_count,
                    "top_level_comment": str(data.get("comment", "")),
                },
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

        try:
            self._clone_repo(
                self.lolbas_url,
                self.lolbas_clone_path,
                shallow=self.shallow_clone,
            )
            for yml_file in sorted((self.lolbas_clone_path / "yml").rglob("*.yml")):
                doc = self._parse_lolbas_entry(yml_file)
                if doc:
                    docs.append(doc)
                    lolbas_count += 1
            logger.info(f"Parsed {lolbas_count} LOLBAS entries")
        except Exception as e:
            self.errors.append(f"Failed to clone/parse LOLBAS repo: {e}")

        try:
            self._clone_repo(
                self.gtfobins_url,
                self.gtfobins_clone_path,
                shallow=self.shallow_clone,
            )
            for bin_file in sorted((self.gtfobins_clone_path / "_gtfobins").iterdir()):
                if bin_file.is_file() and not bin_file.name.startswith("."):
                    doc = self._parse_gtfobins_entry(bin_file)
                    if doc:
                        docs.append(doc)
                        gtfobins_count += 1
            logger.info(f"Parsed {gtfobins_count} GTFOBins entries")
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
