"""C3: Atomic Red Team Collector.

Clones the redcanaryco/atomic-red-team repository and parses YAML test
definitions from the atomics/ directory. One document per atomic test.
"""
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import logging
import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.git import github_blob_url
from utils.text import to_markdown, count_words

logger = logging.getLogger(__name__)

class AtomicRedTeamCollector(BaseCollector):

    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_dir"])
        self.atomics_subdir = config.get("atomics_subdir", "atomics")
        self.shallow_clone = config.get("shallow_clone", True)
        self.platforms = config.get("platforms", ["windows", "linux", "macos"])

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _normalize_str(self, text: str) -> str:
        return text.replace("\n", " ").replace("|", "\\|")

    def _build_markdown(self, technique_id: str, display_name: str, idx: str, test: dict) -> str:
        """Build markdown content for a single atomic test."""
        test_name = test.get("name", f"{technique_id} - Test {idx}")
        description = test.get("description", "No description")
        platforms = test.get("supported_platforms", [])
        guid = test.get("auto_generated_guid", "")

        lines = [
            f"# {technique_id}: {test_name}",
            "",
            f"**Technique**: {display_name} ({technique_id})",
            f"**Platforms**: {', '.join(platforms)}",
            f"**GUID**: `{guid}`",
            "",
            "## Description", str(description), 
            "",
        ]

        # Input arguments
        input_args = test.get("input_arguments", {})
        if input_args:
            lines.append("## Input Arguments")
            lines.append("| Name | Description | Type | Default |")
            lines.append("|---|---|---|---|")
            for arg_name, arg_def in input_args.items():
                desc = self._normalize_str(str(arg_def.get("description", "")))
                arg_type = arg_def.get("type", "string")
                default = self._normalize_str(str(arg_def.get("default", "")))
                lines.append(f"| `{arg_name}` | {desc} | {arg_type} | `{default}` |")
            lines.append("")

        # Dependencies
        dependencies = test.get("dependencies", [])
        if dependencies:
            lines.append("## Dependencies")

            dependency_executor = test.get("dependency_executor_name", "")
            if dependency_executor:
                lines.append(f"**Dependency executor**: {dependency_executor}")

            for dep in dependencies:
                dep_desc = dep.get("description", "")
                lines.append("**Description**")
                lines.append(f"- {dep_desc}")
                prereq_cmd = dep.get("prereq_command", "")
                if prereq_cmd:
                    lines.append(f"  - Check: `{prereq_cmd.strip()}`")
                get_prereq = dep.get("get_prereq_command", "")
                if get_prereq:
                    lines.append(f"  - Install: `{get_prereq.strip()}`")
            lines.append("")

        # Executor
        executor = test.get("executor", {})
        if executor:
            lines.append("## Executor")
            exec_name = executor.get("name", "unknown")
            lines.append(f"**Type**: {exec_name}")
            elevation = executor.get("elevation_required", False)
            lines.append(f"**Elevation Required**: {elevation}")
            lines.append("")

            command = executor.get("command", "")
            if command:
                lines.append("### Command")
                lines.append(f"```{exec_name}")
                lines.append(str(command).strip())
                lines.append("```")
                lines.append("")

            cleanup = executor.get("cleanup_command", "")
            if cleanup:
                lines.append("### Cleanup Command")
                lines.append(f"```{exec_name}")
                lines.append(str(cleanup).strip())
                lines.append("```")
                lines.append("")

        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone Atomic Red Team repo: {e}")
            self.duration = time() - start_time
            return 0

        atomics_dir = self.clone_path / self.atomics_subdir
        if not atomics_dir.exists():
            self.errors.append(f"Atomics directory not found: {atomics_dir}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        # Each technique dir (T1059, T1059.001, etc.) has a YAML file
        technique_dirs = sorted(atomics_dir.iterdir())
        for technique_dir in technique_dirs:
            if not technique_dir.is_dir() or not technique_dir.name.startswith("T"):
                continue

            yaml_file = technique_dir / f"{technique_dir.name}.yaml"
            if not yaml_file.exists():
                continue

            try:
                text = yaml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {yaml_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {yaml_file}: {e}")
            
            if not data or not isinstance(data, dict):
                continue

            technique_id = data.get("attack_technique", technique_dir.name)
            display_name = data.get("display_name", technique_id)
            atomic_tests = data.get("atomic_tests", [])

            for idx, test in enumerate(atomic_tests):
                try:
                    platforms = test.get("supported_platforms", [])
                    guid = test.get("auto_generated_guid")
                    test_name = test.get("name", f"{technique_id} - Test {idx}")
                    markdown = self._build_markdown(str(technique_id), str(display_name), str(idx), test)

                    executor = test.get("executor", {})

                    metadata: dict[str, Any] = {
                        "technique_id": technique_id,
                        "display_name": display_name,
                        "test_guid": guid,
                        "test_index": idx,
                        "supported_platforms": platforms,
                        "executor_type": executor.get("name", "unknown"),
                        "elevation_required": executor.get("elevation_required", False),
                        "has_cleanup": bool(executor.get("cleanup_command")),
                        "has_dependencies": bool(test.get("dependencies")),
                    }

                    doc = RawDocument(
                        doc_id=f"atomic-rt-{guid}",
                        source="atomic_red_team",
                        source_url=github_blob_url(
                            self.url,
                            "master",
                            f"atomics/{technique_id}/{technique_id}.yaml",
                        ),
                        title=f"{technique_id}: {test_name}",
                        date_collected=date.today(),
                        date_published=None,
                        content_type="atomic_test",
                        content_markdown=markdown,
                        metadata=metadata,
                        word_count=count_words(markdown),
                    )
                    docs.append(doc)

                except Exception as e:
                    self.warnings.append(
                        f"Failed to process test {idx} in {technique_id}: {e}"
                    )

        self.doc_count = self._write_documents(docs, self.output_dir, "atomic_red_team")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} Atomic Red Team tests in {self.duration:.1f}s")
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
