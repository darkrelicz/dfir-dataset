import datetime
import time
from pathlib import Path
from typing import Any

import git
import yaml

from collectors.base import BaseCollector
from collectors.schemas import RawDocument

class SigmaRulesCollector(BaseCollector):
    SOURCE_URL = "https://github.com/SigmaHQ/sigma.git"
    LICENSE = "Detection Rule License (DRL) 1.1"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.url = config.get("url", self.SOURCE_URL)
        self.clone_dir = Path(config["clone_dir"])
        self.rules_subdir = config.get("rules_subdir", "rules")
        self.min_rule_level = config.get("min_rule_level", "low")
        
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.doc_count = 0
        self.duration = 0.0

        self.levels = ["informational", "low", "medium", "high", "critical"]
        try:
            self.min_level_idx = self.levels.index(self.min_rule_level.lower())
        except ValueError:
            self.min_level_idx = 0

    def _clone_or_pull(self):
        if self.clone_dir.exists():
            repo = git.Repo(self.clone_dir)
            repo.remotes.origin.pull()
        else:
            self.clone_dir.parent.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(self.url, self.clone_dir, depth=1)

    def collect(self, output_dir: Path) -> int:
        start_time = time.time()
        try:
            self._clone_or_pull()
        except Exception as e:
            self.errors.append(f"Failed to clone/pull Sigma repo: {e}")
            self.duration = time.time() - start_time
            return 0

        rules_dir = self.clone_dir / self.rules_subdir
        if not rules_dir.exists():
            self.errors.append(f"Rules directory not found: {rules_dir}")
            self.duration = time.time() - start_time
            return 0

        docs = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for yml_path in rules_dir.rglob("*.yml"):
            try:
                with open(yml_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    rule = yaml.safe_load(content)
                    
                if not isinstance(rule, dict):
                    self.warnings.append(f"Invalid rule format in {yml_path.name}")
                    continue
                    
                level = rule.get("level", "informational").lower()
                try:
                    level_idx = self.levels.index(level)
                except ValueError:
                    level_idx = 0
                    
                if level_idx < self.min_level_idx:
                    continue
                    
                rule_id = rule.get("id", str(yml_path.relative_to(self.clone_dir)))
                
                attack_tags = []
                for tag in rule.get("tags", []):
                    if isinstance(tag, str) and tag.lower().startswith("attack.t"):
                        attack_tags.append(tag.lower().replace("attack.t", "T").upper())
                        
                markdown_lines = [
                    f"# {rule.get('title', 'Unknown Title')}",
                    "",
                    f"**ID:** {rule_id}",
                    f"**Level:** {level}",
                    f"**Status:** {rule.get('status', 'unknown')}",
                    "",
                    "## Rule YAML",
                    "```yaml",
                    content.strip(),
                    "```"
                ]
                
                content_markdown = self._to_markdown("\n".join(markdown_lines))
                
                date_published = str(rule.get("date", "")) or None
                
                doc = RawDocument(
                    doc_id=f"sigma-{rule_id}",
                    source="sigma_rules",
                    source_url=f"{self.url.replace('.git', '')}/blob/master/{yml_path.relative_to(self.clone_dir)}",
                    title=rule.get("title", yml_path.name),
                    date_collected=collected_at,
                    date_published=date_published,
                    content_type="sigma_rule",
                    content_markdown=content_markdown,
                    metadata={
                        "rule_id": rule_id,
                        "title": rule.get("title", ""),
                        "logsource": rule.get("logsource", {}),
                        "level": level,
                        "status": rule.get("status", "unknown"),
                        "attack_tags": attack_tags,
                        "author": rule.get("author", ""),
                        "falsepositives": rule.get("falsepositives", []),
                        "references": rule.get("references", []),
                    },
                    license=self.LICENSE,
                    word_count=self._count_words(content_markdown)
                )
                docs.append(doc)
            except Exception as e:
                self.warnings.append(f"Failed to parse {yml_path.name}: {e}")

        self.doc_count = self._write_documents(docs, output_dir, "sigma_rules")
        self.duration = time.time() - start_time
        return self.doc_count

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}

    def manifest(self) -> dict[str, Any]:
        return {
            "collector": "SigmaRulesCollector",
            "version": self.VERSION,
            "source_url": self.url,
            "license": self.LICENSE,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_count": self.doc_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration
        }
