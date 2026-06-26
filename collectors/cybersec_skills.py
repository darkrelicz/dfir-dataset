"""AF9: Anthropic Cybersecurity Skills Collector.

Clones the mukul975/Anthropic-Cybersecurity-Skills repository and parses
SKILL.md files with YAML frontmatter + Markdown body. Applies content-length
filter to exclude thin boilerplate templates.
"""
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import github_blob_url
from utils.markdown import parse_yaml_frontmatter
from utils.text import as_list, slugify, to_markdown, count_words

logger = logging.getLogger(__name__)


class CybersecSkillsCollector(BaseCollector):

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)
        self.min_body_tokens = config.get("min_body_tokens", 500)

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0
        self.filtered_count = 0

    def _count_body_tokens(self, body: str) -> int:
        return len(re.findall(r"\S+", body))

    def _extract_framework_mappings(
        self,
        frontmatter: dict,
    ) -> dict[str, Any]:
        return {
            "mitre_attack_ids": as_list(
                frontmatter.get("mitre_attack"),
                stringify=True,
            ),
            "mitre_atlas_ids": as_list(
                frontmatter.get("atlas_techniques"),
                stringify=True,
            ),
            "d3fend_techniques": as_list(
                frontmatter.get("d3fend_techniques"),
                stringify=True,
            ),
            "nist_csf": as_list(frontmatter.get("nist_csf"), stringify=True),
            "nist_ai_rmf": as_list(frontmatter.get("nist_ai_rmf"), stringify=True),
            "mitre_f3": frontmatter.get("mitre_f3") or {},
        }

    def _extract_heading_values(self, body: str, pattern: str) -> list[str]:
        values = []
        for match in re.finditer(pattern, body, re.IGNORECASE | re.MULTILINE):
            heading = match.group(0).lstrip("#").strip()
            values.append(re.sub(r"\s+", " ", heading))
        return values

    def _extract_tools_referenced(self, body: str) -> list[str]:
        tools: set[str] = set()
        shell_languages = {
            "bash",
            "cmd",
            "console",
            "powershell",
            "ps1",
            "sh",
            "shell",
            "terminal",
            "zsh",
        }
        ignored = {
            "cd",
            "cat",
            "class",
            "echo",
            "else",
            "except",
            "fi",
            "for",
            "from",
            "if",
            "import",
            "print",
            "return",
            "then",
            "try",
            "while",
            "with",
        }

        for language, code_block in re.findall(
            r"```([^\n`]*)\n(.*?)```",
            body,
            re.DOTALL,
        ):
            language_parts = language.strip().lower().split(maxsplit=1)
            language = language_parts[0] if language_parts else ""
            if language not in shell_languages:
                continue

            for line in code_block.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "//")):
                    continue

                line = re.sub(r"^(?:\$|>|PS>)\s*", "", line)
                line = re.sub(r"^(?:sudo|time|env)\s+", "", line)
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", line):
                    continue

                match = re.match(r"([A-Za-z][A-Za-z0-9_.+-]*)", line)
                if not match:
                    continue

                command = match.group(1).lower()
                if command not in ignored and not command.startswith("-"):
                    tools.add(command)

        return sorted(tools)

    def _build_markdown(self, frontmatter: dict, body: str) -> str:
        """Build enriched markdown from frontmatter and body."""
        name = frontmatter.get("name", "Unknown Skill")
        description = frontmatter.get("description", "")
        domain = frontmatter.get("domain", "")
        subdomain = frontmatter.get("subdomain", "")
        tags = frontmatter.get("tags", []) or []
        mappings = self._extract_framework_mappings(frontmatter)

        lines = [
            f"# {name}",
            "",
        ]
        if domain:
            lines.append(f"**Domain**: {domain}")
        if subdomain:
            lines.append(f"**Subdomain**: {subdomain}")
        if tags:
            lines.append(f"**Tags**: {', '.join(str(t) for t in tags)}")
        lines.append("")

        if description:
            lines.append("## Description")
            lines.append(str(description).strip())
            lines.append("")

        mapping_lines = []
        if mappings["mitre_attack_ids"]:
            mapping_lines.append(
                "- **MITRE ATT&CK**: "
                f"{', '.join(mappings['mitre_attack_ids'])}"
            )
        if mappings["mitre_atlas_ids"]:
            mapping_lines.append(
                "- **MITRE ATLAS**: "
                f"{', '.join(mappings['mitre_atlas_ids'])}"
            )
        if mappings["d3fend_techniques"]:
            mapping_lines.append(
                "- **D3FEND**: "
                f"{', '.join(mappings['d3fend_techniques'])}"
            )
        if mappings["nist_csf"]:
            mapping_lines.append(f"- **NIST CSF**: {', '.join(mappings['nist_csf'])}")
        if mappings["nist_ai_rmf"]:
            mapping_lines.append(
                f"- **NIST AI RMF**: {', '.join(mappings['nist_ai_rmf'])}"
            )

        if mapping_lines:
            lines.append("## Framework Mappings")
            lines.extend(mapping_lines)
            lines.append("")

        lines.append("## Skill Content")
        lines.append("")
        lines.append(body.strip())

        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Cybersecurity Skills repo: {e}")
            self.duration = time() - start_time
            return 0

        skills_dir = self.clone_path / "skills"
        if not skills_dir.exists():
            self.errors.append(f"Skills directory not found: {skills_dir}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []
        self.filtered_count = 0

        skill_files = sorted(skills_dir.rglob("SKILL.md"))
        logger.info(f"Found {len(skill_files)} SKILL.md files")

        for skill_file in skill_files:
            try:
                content = skill_file.read_text(encoding="utf-8", errors="replace")
                frontmatter, body = parse_yaml_frontmatter(content)

                if not frontmatter:
                    self.warnings.append(f"No frontmatter found in {skill_file}")
                    continue

                body_text = body.strip()
                body_tokens = self._count_body_tokens(body_text)
                if body_tokens < self.min_body_tokens:
                    self.filtered_count += 1
                    continue

                name = frontmatter.get("name", skill_file.parent.name)
                domain = frontmatter.get("domain", "")
                subdomain = frontmatter.get("subdomain", "")

                markdown = self._build_markdown(frontmatter, body)
                mappings = self._extract_framework_mappings(frontmatter)
                relative_path = skill_file.relative_to(self.clone_path).as_posix()
                name_slug = slugify(str(name), fallback="skill")

                metadata: dict[str, Any] = {
                    "skill_name": name,
                    "description": frontmatter.get("description", ""),
                    "domain": domain,
                    "subdomain": subdomain,
                    "tags": frontmatter.get("tags", []) or [],
                    "mitre_attack_ids": mappings["mitre_attack_ids"],
                    "mitre_atlas_ids": mappings["mitre_atlas_ids"],
                    "d3fend_techniques": mappings["d3fend_techniques"],
                    "nist_csf": mappings["nist_csf"],
                    "nist_ai_rmf": mappings["nist_ai_rmf"],
                    "mitre_f3": mappings["mitre_f3"],
                    "version": frontmatter.get("version", ""),
                    "author": frontmatter.get("author", ""),
                    "license": frontmatter.get("license", ""),
                    "body_chars": len(body_text),
                    "body_tokens": body_tokens,
                    "workflow_steps": self._extract_heading_values(
                        body,
                        r"^#{2,6}\s+Step\s+\d+\s*[:.\-\u2014]?\s*.+$",
                    ),
                    "scenarios": self._extract_heading_values(
                        body,
                        r"^#{2,6}\s+Scenario(?:\s+\d+)?\s*[:.\-\u2014]?\s*.+$",
                    ),
                    "tools_referenced": self._extract_tools_referenced(body),
                    "source_path": relative_path,
                }

                doc = RawDocument(
                    doc_id=f"cybersec-skill-{name_slug}",
                    source="cybersec_skills",
                    source_url=github_blob_url(self.url, "main", relative_path),
                    title=f"Skill: {name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="practitioner_workflow",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=count_words(markdown),
                )
                docs.append(doc)

            except Exception as e:
                self.warnings.append(f"Error processing {skill_file}: {e}")

        if self.filtered_count:
            logger.info(
                f"Filtered {self.filtered_count} skills below "
                f"{self.min_body_tokens} tokens"
            )

        self.doc_count = self._write_documents(docs, self.output_dir, "cybersec_skills")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} cybersecurity skills "
            f"in {self.duration:.1f}s"
        )
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        filter_warning = (
            f"Filtered {self.filtered_count} thin skills "
            f"(< {self.min_body_tokens} tokens)"
        )
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=self.config["url"],
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=[*self.warnings, filter_warning],
            duration_seconds=self.duration,
        )
