"""AF9: Anthropic Cybersecurity Skills Collector.

Clones the mukul975/Anthropic-Cybersecurity-Skills repository and parses
SKILL.md files with YAML frontmatter + Markdown body. Applies content-length
filter to exclude thin boilerplate templates.
"""
import re
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest, logger
from collectors.schemas import RawDocument


class CybersecSkillsCollector(BaseCollector):

    SOURCE_URL = "https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git"

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.shallow_clone = config.get("shallow_clone", True)
        self.min_body_chars = config.get("min_body_chars", 2000)  # ~500 tokens

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0
        self.filtered_count = 0

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter and markdown body from a SKILL.md file.

        Returns:
            (frontmatter_dict, body_markdown)
        """
        # Match frontmatter between --- markers
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
        if not match:
            return {}, content

        frontmatter_str = match.group(1)
        body = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            if not isinstance(frontmatter, dict):
                frontmatter = {}
        except yaml.YAMLError:
            frontmatter = {}

        return frontmatter, body

    def _build_markdown(self, frontmatter: dict, body: str) -> str:
        """Build enriched markdown from frontmatter and body."""
        name = frontmatter.get("name", "Unknown Skill")
        description = frontmatter.get("description", "")
        domain = frontmatter.get("domain", "")
        subdomain = frontmatter.get("subdomain", "")
        version = frontmatter.get("version", "")
        tags = frontmatter.get("tags", []) or []

        # Framework mappings
        mitre_attack = frontmatter.get("mitre_attack", []) or []
        mitre_atlas = frontmatter.get("mitre_atlas", []) or []
        d3fend = frontmatter.get("d3fend", []) or []
        nist_csf = frontmatter.get("nist_csf", []) or []
        nist_ai_rmf = frontmatter.get("nist_ai_rmf", []) or []

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

        # Framework mappings section
        mappings = []
        if mitre_attack:
            mappings.append(f"- **MITRE ATT&CK**: {', '.join(str(t) for t in mitre_attack)}")
        if mitre_atlas:
            mappings.append(f"- **MITRE ATLAS**: {', '.join(str(t) for t in mitre_atlas)}")
        if d3fend:
            mappings.append(f"- **D3FEND**: {', '.join(str(t) for t in d3fend)}")
        if nist_csf:
            mappings.append(f"- **NIST CSF**: {', '.join(str(t) for t in nist_csf)}")
        if nist_ai_rmf:
            mappings.append(f"- **NIST AI RMF**: {', '.join(str(t) for t in nist_ai_rmf)}")

        if mappings:
            lines.append("## Framework Mappings")
            lines.extend(mappings)
            lines.append("")

        # Append the full body
        lines.append("## Skill Content")
        lines.append("")
        lines.append(body.strip())

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Cybersecurity Skills repo: {e}")
            self.duration = time() - start_time
            return 0

        # SKILL.md files are in skills/ directory, organized by domain/subdomain
        skills_dir = self.clone_path / "skills"
        if not skills_dir.exists():
            # Try alternate paths
            skills_dir = self.clone_path
            for alt in ["skills", "content/skills"]:
                alt_dir = self.clone_path / alt
                if alt_dir.exists():
                    skills_dir = alt_dir
                    break

        docs: list[RawDocument] = []
        self.filtered_count = 0

        skill_files = sorted(skills_dir.rglob("SKILL.md"))
        logger.info(f"Found {len(skill_files)} SKILL.md files")

        for skill_file in skill_files:
            try:
                content = skill_file.read_text(encoding="utf-8", errors="replace")
                frontmatter, body = self._parse_frontmatter(content)

                if not frontmatter:
                    self.warnings.append(f"No frontmatter found in {skill_file}")
                    continue

                # Content-length filter
                if len(body.strip()) < self.min_body_chars:
                    self.filtered_count += 1
                    continue

                name = frontmatter.get("name", skill_file.parent.name)
                domain = frontmatter.get("domain", "")
                subdomain = frontmatter.get("subdomain", "")

                markdown = self._build_markdown(frontmatter, body)

                # Extract framework IDs
                mitre_attack = frontmatter.get("mitre_attack", []) or []
                mitre_atlas = frontmatter.get("mitre_atlas", []) or []
                d3fend = frontmatter.get("d3fend", []) or []
                nist_csf = frontmatter.get("nist_csf", []) or []

                # Generate slug from skill name
                name_slug = str(name).lower().replace(" ", "-")
                name_slug = re.sub(r'[^a-z0-9-]', '', name_slug)[:60]

                metadata: dict[str, Any] = {
                    "skill_name": name,
                    "domain": domain,
                    "subdomain": subdomain,
                    "tags": frontmatter.get("tags", []) or [],
                    "mitre_attack_ids": [str(t) for t in mitre_attack],
                    "mitre_atlas_ids": [str(t) for t in mitre_atlas],
                    "d3fend_ids": [str(t) for t in d3fend],
                    "nist_csf": [str(t) for t in nist_csf],
                    "version": frontmatter.get("version", ""),
                    "body_chars": len(body.strip()),
                }

                doc = RawDocument(
                    doc_id=f"cybersec-skill-{name_slug}",
                    source="cybersec_skills",
                    source_url=f"https://github.com/mukul975/Anthropic-Cybersecurity-Skills/blob/main/{skill_file.relative_to(self.clone_path)}",
                    title=f"Skill: {name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="practitioner_workflow",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except Exception as e:
                self.warnings.append(f"Error processing {skill_file}: {e}")

        if self.filtered_count:
            logger.info(f"Filtered {self.filtered_count} skills below {self.min_body_chars} char threshold")

        self.doc_count = self._write_documents(docs, self.output_dir, "cybersec_skills")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} cybersecurity skills in {self.duration:.1f}s")
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=self.config["url"],
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=[*self.warnings, f"Filtered {self.filtered_count} thin skills (< {self.min_body_chars} chars)"],
            duration_seconds=self.duration,
        )

