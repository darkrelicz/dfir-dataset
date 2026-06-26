"""AF4: ForensicArtifacts Repository Collector.

Clones the ForensicArtifacts/artifacts repository and parses YAML artifact
definitions. One document per artifact definition.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time

from artifacts import errors, source_type
from artifacts.artifact import ArtifactDefinition
from artifacts.reader import YamlArtifactsReader

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import github_blob_url
from utils.text import to_markdown, count_words

logger = logging.getLogger(__name__)


class ForensicArtifactsCollector(BaseCollector):

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

    def _source_url(self, yaml_file: Path) -> str:
        """Build a GitHub URL for a ForensicArtifacts source file."""
        rel_path = yaml_file.relative_to(self.clone_path)
        return github_blob_url(self.url, "main", rel_path)

    def _build_markdown(self, artifact: ArtifactDefinition) -> str:
        """Build markdown for a single forensic artifact definition."""
        lines = [f"# Forensic Artifact: {artifact.name}", ""]

        if artifact.supported_os:
            lines.append(f"**Supported OS**: {', '.join(artifact.supported_os)}")
        lines.append("")

        if artifact.description:
            lines.extend(["## Description", str(artifact.description).strip(), ""])

        if artifact.sources:
            lines.extend(["## Sources", ""])
            for i, source in enumerate(artifact.sources, start=1):
                lines.append(f"### Source {i}: {source.type_indicator}")

                supported_os = getattr(source, "supported_os", [])
                if supported_os:
                    lines.append(f"**OS**: {', '.join(supported_os)}")

                if isinstance(
                    source,
                    (
                        source_type.DirectorySourceType,
                        source_type.FileSourceType,
                        source_type.PathSourceType,
                    ),
                ):
                    lines.append("**Paths**:")
                    lines.extend(
                        f"- `{artifact_path}`" for artifact_path in source.paths
                    )

                elif isinstance(source, source_type.WindowsRegistryKeySourceType):
                    lines.append("**Registry Keys**:")
                    lines.extend(f"- `{key}`" for key in source.keys)

                elif isinstance(source, source_type.WindowsRegistryValueSourceType):
                    lines.append("**Registry Values**:")
                    for pair in source.key_value_pairs:
                        lines.append(
                            f"- Key: `{pair['key']}`, Value: `{pair['value']}`"
                        )

                elif isinstance(source, source_type.WMIQuerySourceType):
                    if source.query:
                        lines.append(f"**WMI Query**: `{source.query}`")
                    if source.base_object:
                        lines.append(f"**Base Object**: `{source.base_object}`")

                elif isinstance(source, source_type.CommandSourceType):
                    args = " ".join(str(arg) for arg in source.args)
                    command = f"{source.cmd} {args}".strip()
                    lines.append(f"**Command**: `{command}`")

                elif isinstance(source, source_type.ArtifactGroupSourceType):
                    lines.append("**Referenced Artifacts**:")
                    lines.extend(f"- `{name}`" for name in source.names)

                lines.append("")

        if artifact.urls:
            lines.append("## References")
            lines.extend(f"- {url}" for url in artifact.urls)
            lines.append("")

        return to_markdown("\n".join(lines))

    def _extract_metadata(self, artifact: ArtifactDefinition) -> dict:
        """Extract the metadata used by downstream dataset processing."""
        paths = []
        registry_keys = []

        for source in artifact.sources:
            if isinstance(
                source,
                (
                    source_type.DirectorySourceType,
                    source_type.FileSourceType,
                    source_type.PathSourceType,
                ),
            ):
                paths.extend(source.paths)
            elif isinstance(source, source_type.WindowsRegistryKeySourceType):
                registry_keys.extend(source.keys)
            elif isinstance(source, source_type.WindowsRegistryValueSourceType):
                registry_keys.extend(pair["key"] for pair in source.key_value_pairs)

        return {
            "artifact_name": artifact.name,
            "supported_os": artifact.supported_os,
            "source_types": sorted(
                {source.type_indicator for source in artifact.sources}
            ),
            "source_count": len(artifact.sources),
            "file_paths": paths[:20],
            "registry_keys": registry_keys[:20],
        }

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone ForensicArtifacts repo: {e}")
            self.duration = time() - start_time
            return 0

        artifacts_dir = self.clone_path / "artifacts" / "data"
        if not artifacts_dir.exists():
            artifacts_dir = self.clone_path / "data"
        if not artifacts_dir.exists():
            self.errors.append(
                f"ForensicArtifacts YAML directory not found under {self.clone_path}"
            )
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []
        reader = YamlArtifactsReader()
        yaml_files = sorted(artifacts_dir.glob("*.yaml"))
        logger.info(f"Found {len(yaml_files)} ForensicArtifacts YAML files")

        for yaml_file in yaml_files:
            try:
                for artifact in reader.ReadFile(str(yaml_file)):
                    markdown = self._build_markdown(artifact)
                    doc = RawDocument(
                        doc_id=f"forensic-artifact-{artifact.name.lower()}",
                        source="forensic_artifacts",
                        source_url=self._source_url(yaml_file),
                        title=f"Forensic Artifact: {artifact.name}",
                        date_collected=date.today(),
                        date_published=None,
                        content_type="artifact_definition",
                        content_markdown=markdown,
                        metadata=self._extract_metadata(artifact),
                        word_count=count_words(markdown),
                    )
                    docs.append(doc)
            except errors.FormatError as e:
                self.warnings.append(
                    f"Invalid artifact definition in {yaml_file}: {e}"
                )
            except Exception as e:
                self.warnings.append(f"Error processing {yaml_file}: {e}")

        self.doc_count = self._write_documents(
            docs, self.output_dir, "forensic_artifacts"
        )
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} forensic artifact definitions "
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
