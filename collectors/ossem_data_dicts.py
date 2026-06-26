"""AF8: OSSEM Data Dictionaries Collector.

Clones the OTRF/OSSEM-DD repository and parses YAML event dictionary
files containing field-level documentation for security events.
"""
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import github_blob_url
from utils.text import slugify, to_markdown, count_words

logger = logging.getLogger(__name__)


class OSSEMDataDictsCollector(BaseCollector):

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)
        self.include_paths = config.get("include_paths", [])
        self.exclude_paths = config.get(
            "exclude_paths",
            [
                "windows/etw-providers",
                "windows/osquery",
                "linux/osquery",
                "macos/osquery",
                "freebsd/osquery",
            ],
        )

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _path_matches(self, rel_path: str, prefixes: list[str]) -> bool:
        return any(
            rel_path == prefix.strip("/")
            or rel_path.startswith(f"{prefix.strip('/')}/")
            for prefix in prefixes
        )

    def _is_excluded(self, file_path: Path) -> bool:
        rel_path = file_path.relative_to(self.clone_path).as_posix()
        if self._path_matches(rel_path, self.include_paths):
            return False
        return self._path_matches(rel_path, self.exclude_paths)

    def _table_cell(self, value: Any) -> str:
        text = str(value or "").replace("\n", " ").replace("|", "\\|").strip()
        return text

    def _extract_fields(self, event_fields: list) -> list[dict[str, Any]]:
        fields = []
        for field in event_fields:
            if not isinstance(field, dict):
                continue

            field_name = field.get("name") or field.get("standard_name") or ""
            if not field_name:
                continue

            field_metadata: dict[str, Any] = {
                "name": str(field_name),
                "type": field.get("type", ""),
                "description": field.get("description", ""),
                "sample_value": field.get("sample_value", ""),
            }

            standard_name = field.get("standard_name")
            if standard_name and standard_name != "TBD":
                field_metadata["standard_name"] = standard_name

            standard_type = field.get("standard_type")
            if standard_type and standard_type != "TBD":
                field_metadata["standard_type"] = standard_type

            fields.append(field_metadata)
        return fields

    def _extract_references(self, references: list) -> list[dict[str, str]]:
        extracted: list[dict[str, str]] = []
        for reference in references:
            if isinstance(reference, dict):
                text = str(
                    reference.get("text")
                    or reference.get("name")
                    or reference.get("link")
                    or reference.get("url")
                    or ""
                ).strip()
                link = str(reference.get("link") or reference.get("url") or "").strip()
            else:
                text = str(reference).strip()
                link = ""

            if text or link:
                extracted.append({"text": text or link, "link": link})
        return extracted

    def _extract_event_samples(self, event_samples: Any) -> list[dict[str, str]]:
        if isinstance(event_samples, dict):
            event_samples = [event_samples]
        if not isinstance(event_samples, list):
            return []

        samples: list[dict[str, str]] = []
        for event_sample in event_samples:
            if not isinstance(event_sample, dict):
                continue

            sample = str(event_sample.get("sample", "")).strip()
            if not sample:
                continue

            sample_format = str(event_sample.get("format") or "sample").strip()
            if sample_format.lower() == "friedly view":
                sample_format = "friendly view"

            samples.append({"format": sample_format, "sample": sample})
        return samples

    def _version_key(self, value: Any) -> tuple[int, ...]:
        parts = re.findall(r"\d+", str(value or ""))
        return tuple(int(part) for part in parts) if parts else (0,)

    def _event_group_key(
        self,
        data: dict,
        source_path: str,
    ) -> tuple[str, str, str]:
        event_id = str(data.get("event_id", "")).strip()
        if not event_id:
            return ("source_path", source_path, "")

        return (
            str(data.get("platform", "")).strip(),
            str(data.get("log_source", "")).strip(),
            event_id,
        )

    def _candidate_score(
        self,
        data: dict,
        fields: list[dict[str, Any]],
        source_path: str,
    ) -> tuple[tuple[int, ...], int, int, str]:
        described_fields = sum(1 for field in fields if field.get("description"))
        return (
            self._version_key(data.get("event_version")),
            described_fields,
            len(fields),
            source_path,
        )

    def _build_markdown(
        self,
        data: dict,
        fields: list[dict[str, Any]],
        references: list[dict[str, str]],
        event_samples: list[dict[str, str]],
    ) -> str:
        """Build markdown for an OSSEM event dictionary entry."""
        event_name = data.get("name", "")
        description = data.get("description", "")
        event_id = data.get("event_id", "")
        event_version = data.get("event_version", "")
        platform = data.get("platform", "")
        log_source = data.get("log_source", "")
        tags = data.get("tags", []) or []

        lines = [
            f"# OSSEM: {event_name or event_id}",
            "",
            f"**Platform**: {platform}",
        ]
        if log_source:
            lines.append(f"**Log Source**: {log_source}")
        if event_id:
            lines.append(f"**Event ID**: {event_id}")
        if event_version:
            lines.append(f"**Event Version**: {event_version}")
        lines.append("")

        if description:
            lines.append("## Description")
            lines.append(str(description).strip())
            lines.append("")

        if fields:
            lines.append("## Event Fields")
            lines.append("")
            lines.append(
                "| Field Name | Standard Name | Type | Description | Sample Value |"
            )
            lines.append("|---|---|---|---|---|")

            for field in fields:
                name = self._table_cell(field.get("name"))
                standard_name = self._table_cell(field.get("standard_name"))
                standard_name = f"`{standard_name}`" if standard_name else "-"
                field_type = self._table_cell(field.get("type"))
                description = self._table_cell(field.get("description"))
                sample = self._table_cell(field.get("sample_value"))
                lines.append(
                    f"| `{name}` | {standard_name} | {field_type} | "
                    f"{description} | `{sample}` |"
                )
            lines.append("")

        if event_samples:
            lines.append("## Event Samples")
            lines.append("")
            for event_sample in event_samples:
                sample_format = event_sample["format"]
                display_format = (
                    "XML" if sample_format.lower() == "xml" else sample_format.title()
                )
                language = "xml" if sample_format.lower() == "xml" else "text"

                lines.append(f"### {display_format}")
                lines.append(f"```{language}")
                lines.append(event_sample["sample"])
                lines.append("```")
                lines.append("")

        if tags:
            lines.append("## Tags")
            for tag in tags:
                lines.append(f"- `{tag}`")
            lines.append("")

        if references:
            lines.append("## References")
            for ref in references:
                if ref.get("link"):
                    lines.append(f"- [{ref['text']}]({ref['link']})")
                else:
                    lines.append(f"- {ref['text']}")
            lines.append("")

        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone OSSEM-DD repo: {e}")
            self.duration = time() - start_time
            return 0

        candidates: dict[tuple[str, str, str], dict[str, Any]] = {}

        yml_files = sorted(self.clone_path.rglob("*.yml"))
        logger.info(f"Found {len(yml_files)} OSSEM-DD YAML files")

        for yml_file in yml_files:
            if self._is_excluded(yml_file):
                continue

            try:
                text = yml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
                if not data or not isinstance(data, dict):
                    continue

                event_fields = data.get("event_fields", [])
                if not event_fields:
                    continue

                fields = self._extract_fields(event_fields)
                if not fields:
                    continue

                references = self._extract_references(data.get("references", []) or [])
                event_samples = self._extract_event_samples(
                    data.get("event_sample", []) or []
                )
                relative_path = yml_file.relative_to(self.clone_path)
                source_path = relative_path.as_posix()
                group_key = self._event_group_key(data, source_path)
                score = self._candidate_score(data, fields, source_path)
                current = candidates.get(group_key)

                if current is None or score > current["score"]:
                    candidates[group_key] = {
                        "data": data,
                        "fields": fields,
                        "references": references,
                        "event_samples": event_samples,
                        "path": yml_file,
                        "relative_path": relative_path,
                        "source_path": source_path,
                        "score": score,
                    }

            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {yml_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {yml_file}: {e}")

        docs: list[RawDocument] = []
        for candidate in sorted(
            candidates.values(),
            key=lambda item: item["source_path"],
        ):
            data = candidate["data"]
            fields = candidate["fields"]
            references = candidate["references"]
            event_samples = candidate["event_samples"]
            yml_file = candidate["path"]
            relative_path = candidate["relative_path"]
            source_path = candidate["source_path"]
            display_id = slugify(str(relative_path.with_suffix("")), fallback="entry")
            event_id = str(data.get("event_id", ""))
            event_name = data.get("name", "") or yml_file.stem
            platform = data.get("platform", "")
            log_source = data.get("log_source", "")

            markdown = self._build_markdown(
                data,
                fields,
                references,
                event_samples,
            )

            metadata: dict[str, Any] = {
                "event_id": event_id,
                "event_name": event_name,
                "event_version": data.get("event_version", ""),
                "platform": platform,
                "log_source": log_source,
                "field_count": len(fields),
                "field_names": [field["name"] for field in fields],
                "fields": fields,
                "references": references,
                "source_path": source_path,
                "tags": data.get("tags", []) or [],
            }

            doc = RawDocument(
                doc_id=f"ossem-{display_id}",
                source="ossem_data_dicts",
                source_url=github_blob_url(self.url, "main", source_path),
                title=f"OSSEM: {event_name}",
                date_collected=date.today(),
                date_published=None,
                content_type="event_dictionary",
                content_markdown=markdown,
                metadata=metadata,
                word_count=count_words(markdown),
            )
            docs.append(doc)

        self.doc_count = self._write_documents(docs, self.output_dir, "ossem_data_dicts")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} OSSEM data dictionary entries "
            f"in {self.duration:.1f}s"
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
