"""AF5: Velociraptor Artifact Exchange Collector.

Clones the Velocidex/velociraptor-docs repository and parses artifact
YAML files containing VQL queries and descriptions.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest, logger
from collectors.schemas import RawDocument


class VelociraptorArtifactsCollector(BaseCollector):

    SOURCE_URL = "https://github.com/Velocidex/velociraptor-docs.git"

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
        name_lower = artifact_name.lower()
        precond_lower = precondition.lower()
        combined = f"{name_lower} {precond_lower}"

        if "windows" in combined:
            return "Windows"
        elif "linux" in combined:
            return "Linux"
        elif "mac" in combined or "darwin" in combined:
            return "macOS"
        return "Cross-platform"

    def _build_markdown(self, artifact: dict) -> str:
        """Build markdown for a Velociraptor artifact definition."""
        name = artifact.get("name", "Unknown")
        description = artifact.get("description", "")
        author = artifact.get("author", "")
        artifact_type = artifact.get("type", "")
        precondition = artifact.get("precondition", "")
        parameters = artifact.get("parameters", []) or []
        sources = artifact.get("sources", []) or []
        reference = artifact.get("reference", []) or []

        os_platform = self._determine_os(name, str(precondition))

        lines = [
            f"# Velociraptor Artifact: {name}",
            "",
            f"**Platform**: {os_platform}",
        ]
        if artifact_type:
            lines.append(f"**Type**: {artifact_type}")
        if author:
            lines.append(f"**Author**: {author}")
        lines.append("")

        if description:
            lines.append("## Description")
            lines.append(str(description).strip())
            lines.append("")

        if precondition:
            lines.append("## Precondition")
            lines.append("```sql")
            lines.append(str(precondition).strip())
            lines.append("```")
            lines.append("")

        if parameters:
            lines.append("## Parameters")
            lines.append("| Name | Type | Default | Description |")
            lines.append("|---|---|---|---|")
            for param in parameters:
                if not isinstance(param, dict):
                    continue
                pname = param.get("name", "")
                ptype = param.get("type", "string")
                pdefault = str(param.get("default", "")).replace("\n", " ").replace("|", "\\|")[:50]
                pdesc = str(param.get("description", "")).replace("\n", " ").replace("|", "\\|")
                lines.append(f"| `{pname}` | {ptype} | `{pdefault}` | {pdesc} |")
            lines.append("")

        if sources:
            lines.append("## Sources")
            lines.append("")
            for i, source in enumerate(sources):
                if not isinstance(source, dict):
                    continue
                sname = source.get("name", f"Source {i + 1}")
                query = source.get("query", "")

                lines.append(f"### {sname}")
                if query:
                    lines.append("```sql")
                    lines.append(str(query).strip())
                    lines.append("```")
                lines.append("")

        if reference:
            lines.append("## References")
            if isinstance(reference, list):
                for ref in reference:
                    lines.append(f"- {ref}")
            else:
                lines.append(f"- {reference}")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Velociraptor docs repo: {e}")
            self.duration = time() - start_time
            return 0

        # Artifact exchange definitions are typically in content/exchange/artifacts/
        # or content/artifact_references/pages/
        search_dirs = [
            self.clone_path / "content" / "exchange" / "artifacts",
            self.clone_path / "content" / "artifact_references" / "pages",
            self.clone_path / "content" / "exchange",
        ]

        docs: list[RawDocument] = []
        seen_names: set[str] = set()

        # Also look for YAML files with artifact definitions anywhere
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for yaml_file in sorted(search_dir.rglob("*.yaml")):
                try:
                    text = yaml_file.read_text(encoding="utf-8", errors="replace")
                    for artifact in yaml.safe_load_all(text):
                        if not artifact or not isinstance(artifact, dict):
                            continue
                        if "name" not in artifact:
                            continue

                        name = artifact["name"]
                        if name in seen_names:
                            continue
                        seen_names.add(name)

                        markdown = self._build_markdown(artifact)
                        os_platform = self._determine_os(name, str(artifact.get("precondition", "")))

                        # Extract VQL query content
                        vql_queries = []
                        for src in artifact.get("sources", []) or []:
                            if isinstance(src, dict) and src.get("query"):
                                vql_queries.append(src["query"])

                        metadata: dict[str, Any] = {
                            "artifact_name": name,
                            "os_platform": os_platform,
                            "artifact_type": artifact.get("type", ""),
                            "author": artifact.get("author", ""),
                            "parameter_count": len(artifact.get("parameters", []) or []),
                            "source_count": len(artifact.get("sources", []) or []),
                            "has_vql": bool(vql_queries),
                        }

                        name_slug = name.lower().replace(".", "-").replace("/", "-")
                        doc = RawDocument(
                            doc_id=f"velociraptor-{name_slug}",
                            source="velociraptor_artifacts",
                            source_url=f"https://docs.velociraptor.app/artifact_references/pages/{name.replace('.', '/')}/",
                            title=f"Velociraptor: {name}",
                            date_collected=date.today(),
                            date_published=None,
                            content_type="vql_artifact",
                            content_markdown=markdown,
                            metadata=metadata,
                            word_count=self._count_words(markdown),
                        )
                        docs.append(doc)

                except yaml.YAMLError as e:
                    self.warnings.append(f"YAML parse error in {yaml_file}: {e}")
                except Exception as e:
                    self.warnings.append(f"Error processing {yaml_file}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "velociraptor_artifacts")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} Velociraptor artifacts in {self.duration:.1f}s")
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

