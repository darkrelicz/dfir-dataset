"""AF2: Hayabusa Rules Collector.

Clones the Yamato-Security/hayabusa-rules repository and parses YAML
detection rules. Nearly identical to Sigma format with minor field differences.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import github_blob_url
from utils.text import as_list, meets_order_threshold, to_markdown, count_words

logger = logging.getLogger(__name__)

class HayabusaRulesCollector(BaseCollector):

    LEVEL_ORDER = ["informational", "low", "medium", "high", "critical"]

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)
        self.min_rule_level = config.get("min_rule_level", "low")

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _meets_level_threshold(self, level: str) -> bool:
        """Check if rule level meets the minimum threshold."""
        return meets_order_threshold(level, self.min_rule_level, self.LEVEL_ORDER)

    def _text_to_yaml_str(self, text: Any) -> str:
        """Safely serialize text block to YAML string."""
        if text is None:
            return ""
        try:
            return yaml.safe_dump(
                text,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        except yaml.YAMLError:
            return str(text)

    def _source_url(self, rule_path: Path) -> str:
        """Build a GitHub URL for a Hayabusa source rule."""
        rel_path = rule_path.relative_to(self.clone_path)
        return github_blob_url(self.url, "main", rel_path)

    def _parse_rule_file(self, rule_path: Path) -> list[dict]:
        """Parse one Hayabusa file, including correlation files with multiple docs."""
        try:
            text = rule_path.read_text(encoding="utf-8", errors="replace")
            parsed_docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {rule_path}: {e}")
            return []
        except Exception as e:
            self.warnings.append(f"Error reading {rule_path}: {e}")
            return []

        rules = []
        for doc_index, rule in enumerate(parsed_docs, start=1):
            if not rule:
                continue
            if not isinstance(rule, dict):
                self.warnings.append(
                    f"Skipping non-rule YAML document {doc_index} in {rule_path}"
                )
                continue
            if not rule.get("id"):
                self.warnings.append(
                    f"Skipping Hayabusa rule without id in document {doc_index}: "
                    f"{rule_path}"
                )
                continue
            rules.append(rule)
        return rules

    def _build_markdown(self, rule: dict) -> str:
        """Build markdown content from a Hayabusa rule dict."""
        title = rule.get("title", "Untitled Rule")
        description = rule.get("description", "No description provided.")
        status = rule.get("status", "unknown")
        level = rule.get("level", "unknown")
        author = rule.get("author", "Unknown")
        rule_date = rule.get("date", "")

        lines = [
            f"# {title}",
            "",
            f"**Status**: {status}",
            f"**Level**: {level}",
            f"**Author**: {author}",
            f"**Source**: Hayabusa Rules",
        ]
        if rule_date:
            lines.append(f"**Date**: {rule_date}")
        lines.append("")
        lines.append("## Description")
        lines.append(str(description))
        lines.append("")

        # Logsource
        logsource = rule.get("logsource", {})
        if logsource:
            lines.append("## Log Source")
            for key in ["product", "category", "service", "definition"]:
                val = logsource.get(key)
                if val:
                    lines.append(f"- **{key.capitalize()}**: {val}")
            lines.append("")

        # Detection logic
        detection = rule.get("detection", {})
        if detection:
            lines.append("## Detection Logic")
            lines.append("```yaml")
            lines.append(self._text_to_yaml_str(detection).rstrip())
            lines.append("```")
            lines.append("")

        # Details (Hayabusa-specific field for alert message format)
        details = rule.get("details", "")
        if details:
            lines.append("## Alert Details")
            lines.append(f"`{details}`")
            lines.append("")

        # Tags
        tags = as_list(rule.get("tags"))
        if tags:
            lines.append("## Tags")
            for tag in tags:
                lines.append(f"- `{tag}`")
            lines.append("")

        # False positives
        fps = as_list(rule.get("falsepositives"))
        if fps:
            lines.append("## False Positives")
            for fp in fps:
                lines.append(f"- {fp}")
            lines.append("")

        # Samples
        sample_message = rule.get("sample-message", "")
        if sample_message:
            lines.append("## Sample Message")
            lines.append("```yaml")
            lines.append(self._text_to_yaml_str(sample_message).rstrip())
            lines.append("```")
            lines.append("")

        sample_evtx = rule.get("sample-evtx", "")
        if sample_evtx:
            lines.append("## Sample EVTX")
            lines.append("```yaml")
            lines.append(self._text_to_yaml_str(sample_evtx).rstrip())
            lines.append("```")
            lines.append("")

        # References
        refs = as_list(rule.get("references"))
        if refs:
            lines.append("## References")
            for ref in refs:
                lines.append(f"- {ref}")
            lines.append("")


        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Hayabusa rules repo: {e}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        rule_files = sorted(self.clone_path.rglob("*.yml"))
        logger.info(f"Found {len(rule_files)} Hayabusa rule files")

        seen_doc_ids = set()
        for rule_path in rule_files:
            for rule in self._parse_rule_file(rule_path):
                try:
                    self._append_rule_document(rule, rule_path, seen_doc_ids, docs)
                except yaml.YAMLError as e:
                    self.warnings.append(f"YAML parse error in {rule_path}: {e}")
                except Exception as e:
                    self.warnings.append(f"Error processing {rule_path}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "hayabusa_rules")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} Hayabusa rules in {self.duration:.1f}s"
        )
        return self.doc_count

    def _append_rule_document(
        self,
        rule: dict,
        rule_path: Path,
        seen_doc_ids: set[str],
        docs: list[RawDocument],
    ) -> None:
        level = str(rule.get("level", "unknown")).lower()
        if not self._meets_level_threshold(level):
            return

        rule_id = str(rule["id"])
        doc_id = f"hayabusa-{rule_id}"
        if doc_id in seen_doc_ids:
            self.warnings.append(
                f"Skipping duplicate Hayabusa rule id {rule_id}: {rule_path}"
            )
            return
        seen_doc_ids.add(doc_id)

        title = rule.get("title", "Untitled Rule")
        tags = as_list(rule.get("tags"))

        logsource = rule.get("logsource", {}) or {}
        modified = rule.get("modified", "")

        markdown = self._build_markdown(rule)

        metadata: dict[str, Any] = {
            "rule_id": rule_id,
            "level": level,
            "status": rule.get("status", "unknown"),
            "logsource_product": logsource.get("product", ""),
            "logsource_category": logsource.get("category", ""),
            "logsource_service": logsource.get("service", ""),
            "tags": tags,
            "falsepositives": as_list(rule.get("falsepositives")),
            "references": as_list(rule.get("references")),
            "author": rule.get("author", ""),
            "modified": str(modified) if modified else "",
            "ruletype": rule.get("ruletype", ""),
            "details_format": rule.get("details", ""),
        }

        doc = RawDocument(
            doc_id=doc_id,
            source="hayabusa_rules",
            source_url=self._source_url(rule_path),
            title=title,
            date_collected=date.today(),
            date_published=rule.get("date"),
            content_type="hayabusa_rule",
            content_markdown=markdown,
            metadata=metadata,
            word_count=count_words(markdown),
        )
        docs.append(doc)

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
