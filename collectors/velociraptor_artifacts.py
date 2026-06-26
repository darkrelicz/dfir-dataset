"""AF5: Velociraptor Artifact Exchange Collector.

Clones the Velocidex/velociraptor-docs repository and parses generated
artifact reference Markdown pages containing VQL queries and descriptions.
"""
import re
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest, logger
from collectors.schemas import RawDocument
from utils.markdown import parse_yaml_frontmatter
from utils.text import as_list, slugify, to_markdown, count_words

ARTIFACT_BLOCK_RE = re.compile(
    r'<pre><code class="language-yaml">\n?(.*?)</code></pre>',
    re.DOTALL,
)


class VelociraptorArtifactsCollector(BaseCollector):

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

    def _determine_os(self, artifact_name: str, precondition: str = "") -> str:
        """Determine OS from artifact name or precondition."""
        combined = f"{artifact_name} {precondition}".lower()

        if "windows" in combined:
            return "Windows"
        if "linux" in combined:
            return "Linux"
        if "mac" in combined or "darwin" in combined:
            return "macOS"
        return "Cross-platform"

    def _parse_artifact_yaml(self, body: str) -> dict[str, Any]:
        """Parse the embedded artifact YAML block from a Markdown page."""
        match = ARTIFACT_BLOCK_RE.search(body)
        if not match:
            return {}

        artifact = yaml.safe_load(unescape(match.group(1))) or {}
        if not isinstance(artifact, dict):
            return {}
        return artifact

    def _normalize_body(self, body: str) -> str:
        """Convert the embedded HTML YAML block into fenced Markdown."""

        def replace(match: re.Match) -> str:
            code = unescape(match.group(1)).strip()
            return f"```yaml\n{code}\n```"

        return ARTIFACT_BLOCK_RE.sub(replace, body).strip()

    def _as_text(self, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value or "")

    def _names_from_items(self, items: list[Any], default_prefix: str) -> list[str]:
        names = []
        for index, item in enumerate(items, start=1):
            if isinstance(item, dict):
                names.append(str(item.get("name") or f"{default_prefix} {index}"))
            else:
                names.append(str(item))
        return names

    def _query_parts(self, artifact: dict[str, Any]) -> list[str]:
        sources = artifact.get("sources", []) or []
        query_parts = [
            artifact.get("precondition", ""),
            artifact.get("export", ""),
        ]

        for source in sources:
            if not isinstance(source, dict):
                continue
            query_parts.append(source.get("precondition", ""))
            for key in ("query", "queries"):
                value = source.get(key)
                if isinstance(value, list):
                    query_parts.extend(str(item) for item in value)
                elif value:
                    query_parts.append(str(value))

        return [str(part) for part in query_parts if part]

    def _has_vql(self, artifact: dict[str, Any]) -> bool:
        query_text = "\n".join(self._query_parts(artifact))
        return bool(re.search(r"\b(SELECT|LET)\b", query_text, re.I))

    def _content_type(
        self,
        artifact: dict[str, Any],
        tags: list[str],
        has_vql: bool,
    ) -> str:
        artifact_type = self._as_text(artifact.get("type")).upper()
        tag_set = {tag.lower() for tag in tags}

        if artifact_type == "NOTEBOOK" or "notebook" in tag_set:
            return "velociraptor_notebook"
        if artifact.get("reports"):
            return "velociraptor_report_template"
        if artifact_type in {"CLIENT_EVENT", "SERVER_EVENT"}:
            return "velociraptor_event_artifact"
        if artifact_type == "INTERNAL":
            return "velociraptor_internal_artifact"
        if artifact_type == "SERVER" or "server artifact" in tag_set:
            return "velociraptor_server_artifact"
        if artifact_type == "CLIENT" or "client artifact" in tag_set:
            return "velociraptor_client_artifact"
        if has_vql:
            return "velociraptor_vql_artifact"
        return "velociraptor_artifact"

    def _artifact_family(self, artifact_name: str) -> str:
        parts = artifact_name.split(".")
        return ".".join(parts[:2]) if len(parts) > 1 else artifact_name

    def _references(self, artifact: dict[str, Any]) -> list[str]:
        return [
            *as_list(artifact.get("reference"), stringify=True),
            *as_list(artifact.get("references"), stringify=True),
        ]

    def _build_markdown(
        self,
        artifact: dict[str, Any],
        body: str,
        md_file: Path,
        os_platform: str,
    ) -> str:
        """Build normalized markdown from a Velociraptor artifact page."""
        artifact_type = self._as_text(artifact.get("type"))
        author = self._as_text(artifact.get("author"))

        lines = [
            f"# Velociraptor Artifact: {artifact['name']}",
            "",
            f"**Platform**: {os_platform}",
            f"**Source File**: `{md_file.name}`",
        ]
        if artifact_type:
            lines.append(f"**Type**: {artifact_type}")
        if author:
            lines.append(f"**Author**: {author}")

        lines.extend(["", "## Artifact Reference", "", body])
        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Velociraptor docs repo: {e}")
            self.duration = time() - start_time
            return 0

        artifact_path = self.clone_path / "content" / "artifact_references" / "pages"
        md_files = sorted(artifact_path.rglob("*.md"))
        logger.info(f"Found {len(md_files)} Velociraptor artifact Markdown pages")

        docs: list[RawDocument] = []

        for md_file in md_files:
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                frontmatter, body = parse_yaml_frontmatter(text)
                artifact = self._parse_artifact_yaml(body)

                if not artifact.get("name"):
                    self.warnings.append(f"No embedded artifact YAML in {md_file}")
                    continue

                artifact_name = artifact["name"]
                normalized_body = self._normalize_body(body)
                os_platform = self._determine_os(
                    artifact_name,
                    artifact.get("precondition", ""),
                )
                markdown = self._build_markdown(
                    artifact,
                    normalized_body,
                    md_file,
                    os_platform,
                )

                page_path = (
                    md_file.relative_to(artifact_path)
                    .with_suffix("")
                    .as_posix()
                )
                source_url = (
                    "https://docs.velociraptor.app/artifact_references/pages/"
                    f"{page_path.lower()}/"
                )
                parameters = artifact.get("parameters", []) or []
                sources = artifact.get("sources", []) or []
                tags = frontmatter.get("tags", []) or []
                has_vql = self._has_vql(artifact)
                tool_names = self._names_from_items(
                    artifact.get("tools", []) or [],
                    "Tool",
                )

                metadata: dict[str, Any] = {
                    "artifact_name": artifact_name,
                    "artifact_family": self._artifact_family(artifact_name),
                    "os_platform": os_platform,
                    "artifact_type": self._as_text(artifact.get("type")),
                    "author": self._as_text(artifact.get("author")),
                    "tags": tags,
                    "parameter_count": len(parameters),
                    "parameter_names": self._names_from_items(parameters, "Parameter"),
                    "source_count": len(sources),
                    "source_names": self._names_from_items(sources, "Source"),
                    "has_vql": has_vql,
                    "required_permissions": as_list(
                        artifact.get("required_permissions"),
                        stringify=True,
                    ),
                    "implied_permissions": as_list(
                        artifact.get("implied_permissions"),
                        stringify=True,
                    ),
                    "references": self._references(artifact),
                    "tools": tool_names,
                    "relative_path": md_file.relative_to(self.clone_path).as_posix(),
                }

                doc = RawDocument(
                    doc_id=f"velociraptor-{slugify(page_path)}",
                    source="velociraptor_artifacts",
                    source_url=source_url,
                    title=f"Velociraptor: {artifact_name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type=self._content_type(artifact, tags, has_vql),
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=count_words(markdown),
                )
                docs.append(doc)

            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {md_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {md_file}: {e}")

        self.doc_count = self._write_documents(
            docs,
            self.output_dir,
            "velociraptor_artifacts",
        )
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} Velociraptor artifacts in "
            f"{self.duration:.1f}s"
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
