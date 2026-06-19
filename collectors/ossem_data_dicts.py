"""AF8: OSSEM Data Dictionaries Collector.

Clones the OTRF/OSSEM-DD repository and parses YAML event dictionary
files containing field-level documentation for security events.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest, logger
from collectors.schemas import RawDocument


class OSSEMDataDictsCollector(BaseCollector):

    SOURCE_URL = "https://github.com/OTRF/OSSEM-DD.git"

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

    def _determine_platform(self, file_path: Path) -> str:
        """Determine platform from file path."""
        path_str = str(file_path).lower()
        if "/windows/" in path_str or "\\windows\\" in path_str:
            return "Windows"
        elif "/linux/" in path_str or "\\linux\\" in path_str:
            return "Linux"
        elif "/macos/" in path_str or "\\macos\\" in path_str:
            return "macOS"
        elif "/zeek/" in path_str or "\\zeek\\" in path_str:
            return "Zeek"
        return "Cross-platform"

    def _determine_log_source(self, file_path: Path) -> str:
        """Determine log source from file path."""
        parts = file_path.parts
        # Look for directory names like 'security', 'sysmon', 'system'
        known_sources = {"security", "sysmon", "system", "powershell", "application",
                         "wmi", "dns", "firewall", "defender", "applocker", "bits"}
        for part in parts:
            if part.lower() in known_sources:
                return part.capitalize()
        return ""

    def _build_markdown(self, data: dict, file_path: Path, platform: str) -> str:
        """Build markdown for an OSSEM event dictionary entry."""
        title = data.get("title", "")
        description = data.get("description", "")
        event_code = data.get("event_code", "")
        event_version = data.get("event_version", "")
        log_source = data.get("log_source", "") or self._determine_log_source(file_path)
        event_fields = data.get("event_fields", []) or []
        references = data.get("references", []) or []
        tags = data.get("tags", []) or []

        display_title = title or f"Event {event_code}" if event_code else file_path.stem

        lines = [
            f"# OSSEM: {display_title}",
            "",
            f"**Platform**: {platform}",
        ]
        if log_source:
            lines.append(f"**Log Source**: {log_source}")
        if event_code:
            lines.append(f"**Event Code**: {event_code}")
        if event_version:
            lines.append(f"**Event Version**: {event_version}")
        lines.append("")

        if description:
            lines.append("## Description")
            lines.append(str(description).strip())
            lines.append("")

        if event_fields:
            lines.append("## Event Fields")
            lines.append("")
            lines.append("| Field Name | Type | Description | Sample Value |")
            lines.append("|---|---|---|---|")

            for field in event_fields:
                if not isinstance(field, dict):
                    continue
                fname = field.get("standard_name", field.get("name", ""))
                ftype = field.get("type", "")
                fdesc = str(field.get("description", "")).replace("\n", " ").replace("|", "\\|")
                fsample = str(field.get("sample_value", "")).replace("\n", " ").replace("|", "\\|")[:50]

                lines.append(f"| `{fname}` | {ftype} | {fdesc} | `{fsample}` |")
            lines.append("")

        if tags:
            lines.append("## Tags")
            for tag in tags:
                lines.append(f"- `{tag}`")
            lines.append("")

        if references:
            lines.append("## References")
            for ref in references:
                if isinstance(ref, dict):
                    lines.append(f"- [{ref.get('name', 'Link')}]({ref.get('url', '')})")
                else:
                    lines.append(f"- {ref}")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone OSSEM-DD repo: {e}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        # OSSEM-DD uses .yml files organized by platform/source
        yml_files = sorted(self.clone_path.rglob("*.yml"))
        logger.info(f"Found {len(yml_files)} OSSEM-DD YAML files")

        for yml_file in yml_files:
            # Skip non-dictionary files
            if any(skip in str(yml_file) for skip in [".github", "scripts", "templates"]):
                continue

            try:
                text = yml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
                if not data or not isinstance(data, dict):
                    continue

                # Must have event_fields or be a meaningful dictionary entry
                event_fields = data.get("event_fields", [])
                if not event_fields:
                    continue

                platform = data.get("platform", "") or self._determine_platform(yml_file)
                event_code = data.get("event_code", "")
                title = data.get("title", "")
                log_source = data.get("log_source", "") or self._determine_log_source(yml_file)

                markdown = self._build_markdown(data, yml_file, platform)

                # Extract field names for metadata
                field_names = []
                for field in event_fields:
                    if isinstance(field, dict):
                        fname = field.get("standard_name", field.get("name", ""))
                        if fname:
                            field_names.append(fname)

                display_id = f"{platform.lower()}-{log_source.lower()}-{event_code}" if event_code else yml_file.stem
                display_id = display_id.replace(" ", "-").lower()

                metadata: dict[str, Any] = {
                    "event_code": str(event_code),
                    "platform": platform,
                    "log_source": log_source,
                    "field_count": len(event_fields),
                    "field_names": field_names[:30],  # Cap for size
                    "tags": data.get("tags", []) or [],
                }

                doc = RawDocument(
                    doc_id=f"ossem-{display_id}",
                    source="ossem_data_dicts",
                    source_url=f"https://github.com/OTRF/OSSEM-DD/blob/main/{yml_file.relative_to(self.clone_path)}",
                    title=title or f"OSSEM: Event {event_code} ({platform})",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="event_dictionary",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {yml_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {yml_file}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "ossem_data_dicts")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} OSSEM data dictionary entries in {self.duration:.1f}s")
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

