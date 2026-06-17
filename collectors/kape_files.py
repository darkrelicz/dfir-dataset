"""AF1: KAPE Targets & Modules Collector.

Clones the EricZimmerman/KapeFiles repository and parses .tkape (target)
and .mkape (module) YAML files. One document per target/module definition.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any
from urllib.parse import quote

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class KapeFilesCollector(BaseCollector):

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

    def _source_url(self, file_path: Path) -> str:
        """Build a GitHub URL for a KapeFiles source file."""
        base_url = self.url[:-4] if self.url.endswith(".git") else self.url
        rel_path = file_path.relative_to(self.clone_path).as_posix()
        return f"{base_url}/blob/master/{quote(rel_path, safe='/')}"

    def _parse_tkape(self, file_path: Path) -> list[RawDocument]:
        """Parse a .tkape (target) file."""
        docs = []
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            data = yaml.safe_load(text)
            if not data or not isinstance(data, dict):
                return docs

            description = data.get("Description", "")
            author = data.get("Author", "Unknown")
            version = data.get("Version", "")
            guid = data.get("Id", file_path.stem)

            targets = data.get("Targets", []) or []

            lines = [
                f"# KAPE Target: {file_path.stem}",
                "",
                f"**Description**: {description}",
                f"**Author**: {author}",
                f"**Version**: {version}",
                "",
            ]

            if targets:
                lines.append("## Target Definitions")
                lines.append("")
                for target in targets:
                    if not isinstance(target, dict):
                        continue
                    tname = target.get("Name", "Unnamed")
                    category = target.get("Category", "")
                    path = target.get("Path", "")
                    file_mask = target.get("FileMask", "")
                    recursive = target.get("Recursive", False)
                    comment = target.get("Comment", "")
                    save_as = target.get("SaveAsFileName", "")

                    lines.append(f"### {tname}")
                    lines.append(f"- **Category**: {category}")
                    lines.append(f"- **Path**: `{path}`")
                    if file_mask:
                        lines.append(f"- **File Mask**: `{file_mask}`")
                    if recursive:
                        lines.append(f"- **Recursive**: {recursive}")
                    if comment:
                        lines.append(f"- **Comment**: {comment}")
                    if save_as:
                        lines.append(f"- **Save As**: `{save_as}`")
                    lines.append("")

            markdown = self._to_markdown("\n".join(lines))

            # Extract all paths for metadata
            artifact_paths = []
            categories = set()
            for target in targets:
                if isinstance(target, dict):
                    p = target.get("Path", "")
                    if p:
                        artifact_paths.append(p)
                    c = target.get("Category", "")
                    if c:
                        categories.add(c)

            metadata: dict[str, Any] = {
                "kape_type": "target",
                "guid": str(guid),
                "author": author,
                "version": str(version),
                "artifact_paths": artifact_paths,
                "categories": sorted(categories),
                "target_count": len(targets),
            }

            doc = RawDocument(
                doc_id=f"kape-target-{file_path.stem.lower()}",
                source="kape_files",
                source_url=self._source_url(file_path),
                title=f"KAPE Target: {file_path.stem}",
                date_collected=date.today(),
                date_published=None,
                content_type="artifact_definition",
                content_markdown=markdown,
                metadata=metadata,
                word_count=self._count_words(markdown),
            )
            docs.append(doc)

        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {file_path}: {e}")
        except Exception as e:
            self.warnings.append(f"Error processing {file_path}: {e}")

        return docs

    def _parse_mkape(self, file_path: Path) -> list[RawDocument]:
        """Parse a .mkape (module) file."""
        docs = []
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            data = yaml.safe_load(text)
            if not data or not isinstance(data, dict):
                return docs

            description = data.get("Description", "")
            category = data.get("Category", "")
            author = data.get("Author", "Unknown")
            version = data.get("Version", "")
            guid = data.get("Id", file_path.stem)
            binary_url = data.get("BinaryUrl", "")

            processors = data.get("Processors", []) or []

            lines = [
                f"# KAPE Module: {file_path.stem}",
                "",
                f"**Description**: {description}",
                f"**Category**: {category}",
                f"**Author**: {author}",
                f"**Version**: {version}",
            ]

            if binary_url:
                lines.append(f"**Binary URL**: {binary_url}")
            lines.append("")

            if processors:
                lines.append("## Processors")
                lines.append("")
                for proc in processors:
                    if not isinstance(proc, dict):
                        continue
                    executable = proc.get("Executable", "")
                    command_line = proc.get("CommandLine", "")
                    export_format = proc.get("ExportFormat", "")
                    export_file = proc.get("ExportFile", "")

                    lines.append(f"### Executable: {executable}")
                    if command_line:
                        lines.append(f"- **Command**: `{command_line}`")
                    if export_format:
                        lines.append(f"- **Export Format**: {export_format}")
                    if export_file:
                        lines.append(f"- **Export File**: {export_file}")
                    lines.append("")

            markdown = self._to_markdown("\n".join(lines))

            tools = []
            for proc in processors:
                if isinstance(proc, dict):
                    exe = proc.get("Executable", "")
                    if exe:
                        tools.append(exe)

            metadata: dict[str, Any] = {
                "kape_type": "module",
                "guid": str(guid),
                "category": category,
                "author": author,
                "version": str(version),
                "tools": tools,
                "processor_count": len(processors),
            }

            doc = RawDocument(
                doc_id=f"kape-module-{file_path.stem.lower()}",
                source="kape_files",
                source_url=self._source_url(file_path),
                title=f"KAPE Module: {file_path.stem}",
                date_collected=date.today(),
                date_published=None,
                content_type="tool_module",
                content_markdown=markdown,
                metadata=metadata,
                word_count=self._count_words(markdown),
            )
            docs.append(doc)

        except yaml.YAMLError as e:
            self.warnings.append(f"YAML parse error in {file_path}: {e}")
        except Exception as e:
            self.warnings.append(f"Error processing {file_path}: {e}")

        return docs

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone KapeFiles repo: {e}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        # Parse targets
        targets_dir = self.clone_path / "Targets"
        if targets_dir.exists():
            for tkape_file in sorted(targets_dir.rglob("*.tkape")):
                if "!Disabled" in tkape_file.relative_to(targets_dir).parts:
                    continue
                docs.extend(self._parse_tkape(tkape_file))

        # Parse modules
        modules_dir = self.clone_path / "Modules"
        if modules_dir.exists():
            for mkape_file in sorted(modules_dir.rglob("*.mkape")):
                if "!Disabled" in mkape_file.relative_to(modules_dir).parts:
                    continue
                docs.extend(self._parse_mkape(mkape_file))

        self.doc_count = self._write_documents(docs, self.output_dir, "kape_files")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} KAPE targets/modules in {self.duration:.1f}s")
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
