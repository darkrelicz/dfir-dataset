"""C2: SigmaHQ Rules Collector.

Clones the SigmaHQ/sigma repository and parses all YAML detection rules
under the rules/ directory. Handles structural variations across rule types
(process_creation, registry, network, etc.) with safe field extraction.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import logging
import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class SigmaRulesCollector(BaseCollector):

    LEVEL_ORDER = ["informational", "low", "medium", "high", "critical"]

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.rules_subdir = config.get("rules_subdir", "rules")
        self.shallow_clone = config.get("shallow_clone", True)
        self.min_rule_level = config.get("min_rule_level", "low")

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _meets_level_threshold(self, level: str) -> bool:
        """Check if rule level meets the minimum threshold."""
        min_idx = self.LEVEL_ORDER.index(self.min_rule_level) if self.min_rule_level in self.LEVEL_ORDER else 0
        rule_idx = self.LEVEL_ORDER.index(level) if level in self.LEVEL_ORDER else -1
        return rule_idx >= min_idx

    def _extract_attack_tags(self, tags: list) -> list[str]:
        """Extract MITRE ATT&CK technique IDs from Sigma tags."""
        attack_ids = []
        for tag in tags:
            tag_str = str(tag).lower()
            # Tags like 'attack.t1059.001', 'attack.t1059'
            if tag_str.startswith("attack.t") and not tag_str.startswith("attack.the"):
                technique = tag_str.replace("attack.", "").upper()
                attack_ids.append(technique)
        return attack_ids

    def _extract_tactic_tags(self, tags: list) -> list[str]:
        """Extract MITRE ATT&CK tactic names from Sigma tags."""
        tactics = []
        known_tactics = {
            "reconnaissance", "resource_development", "initial_access", "execution",
            "persistence", "privilege_escalation", "stealth", "defense_impairment",
            "credential_access", "discovery", "lateral_movement", "collection", 
            "command_and_control", "exfiltration", "impact"
        }
        for tag in tags:
            tag_str = str(tag).lower()
            if tag_str.startswith("attack."):
                tactic_name = tag_str.replace("attack.", "").replace("-", "_")
                if tactic_name in known_tactics:
                    tactics.append(tactic_name)
        return tactics

    def _detection_to_yaml_str(self, detection: Any) -> str:
        """Safely serialize detection block to YAML string."""
        if detection is None:
            return ""
        try:
            return yaml.dump(detection, default_flow_style=False, allow_unicode=True)
        except Exception:
            return str(detection)

    def _build_markdown(self, rule: dict, rule_path: Path) -> str:
        """Build markdown content from a Sigma rule dict, handling structural variations."""
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
            f"**Date**: {rule_date}",
            "",
            "## Description",
            str(description),
            "",
        ]

        logsource = rule.get("logsource", {})
        if logsource:
            lines.append("## Log Source")
            for key in ["product", "category", "service", "definition"]:
                val = logsource.get(key)
                if val:
                    lines.append(f"- **{key.capitalize()}**: {val}")
            lines.append("")

        # Detection — the core logic block, structure varies significantly
        detection = rule.get("detection", {})
        if detection:
            lines.append("## Detection Logic")
            lines.append("```yaml")
            lines.append(self._detection_to_yaml_str(detection).rstrip())
            lines.append("```")
            lines.append("")

        tags = rule.get("tags", [])
        if tags:
            lines.append("## Tags")
            for tag in tags:
                lines.append(f"- `{tag}`")
            lines.append("")

        fps = rule.get("falsepositives", [])
        if fps:
            lines.append("## False Positives")
            for fp in fps:
                lines.append(f"- {fp}")
            lines.append("")

        refs = rule.get("references", [])
        if refs:
            lines.append("## References")
            for ref in refs:
                lines.append(f"- {ref}")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def _parse_rule_file(self, rule_path: Path) -> dict:
        """Parse a single Sigma YAML file."""
        rule = {}
        try:
            text = rule_path.read_text(encoding="utf-8", errors="replace")
            rule = yaml.safe_load(text)
        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {rule_path}: {e}")
        except Exception as e:
            self.warnings.append(f"Error reading {rule_path}: {e}")
        return rule

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone SigmaHQ repo: {e}")
            self.duration = time() - start_time
            return 0

        rules_dir = self.clone_path / self.rules_subdir
        if not rules_dir.exists():
            self.errors.append(f"Rules directory not found: {rules_dir}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []
        rule_files = list(rules_dir.rglob("*.yml"))
        logger.info(f"Found {len(rule_files)} Sigma rule files")

        for rule_path in rule_files:
            rule = self._parse_rule_file(rule_path)
            try:
                level = str(rule.get("level", "unknown")).lower()
                if not self._meets_level_threshold(level):
                    continue

                rule_id = rule.get("id", rule_path.stem)
                title = rule.get("title", "Untitled Rule")

                tags = rule.get("tags", []) or []
                attack_ids = self._extract_attack_tags(tags)
                tactics = self._extract_tactic_tags(tags)

                logsource = rule.get("logsource", {}) or {}
                markdown = self._build_markdown(rule, rule_path)
                date_published = rule.get("date") 
                
                metadata: dict[str, Any] = {
                    "rule_id": str(rule_id),
                    "level": level,
                    "status": rule.get("status", "unknown"),
                    "logsource_product": logsource.get("product", ""),
                    "logsource_category": logsource.get("category", ""),
                    "logsource_service": logsource.get("service", ""),
                    "mitre_attack_ids": attack_ids,
                    "mitre_attack_tactics": tactics,
                    "falsepositives": rule.get("falsepositives", []) or [],
                    "author": rule.get("author", ""),
                }

                doc = RawDocument(
                    doc_id=f"sigma-{rule_id}",
                    source="sigma_rules",
                    source_url=f"https://github.com/SigmaHQ/sigma/blob/master/{rule_path.relative_to(self.clone_path)}",
                    title=title,
                    date_collected=date.today(),
                    date_published=date_published,
                    content_type="sigma_rule",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except Exception as e:
                self.warnings.append(f"Failed to process rule in {rule_path}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "sigma_rules")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} Sigma rules in {self.duration:.1f}s")
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

    def validate(self) -> dict[str, Any]:
        return {}