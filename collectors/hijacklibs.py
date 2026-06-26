"""AF6: HijackLibs Collector.

Clones the wietze/HijackLibs repository and parses YAML files describing
DLL hijacking opportunities.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.text import as_list, slugify, to_markdown, count_words

logger = logging.getLogger(__name__)

class HijackLibsCollector(BaseCollector):

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

    def _append_detail_map(self, lines: list[str], title: str, value: Any) -> None:
        items = as_list(value)
        if not items:
            return

        lines.append(f"- **{title}**:")
        for item in items:
            if isinstance(item, dict):
                for key, item_value in item.items():
                    if item_value not in ("", None, []):
                        lines.append(f"  - **{key}**: {item_value}")
            else:
                lines.append(f"  - {item}")

    def _build_markdown(self, data: dict, file_path: Path) -> str:
        """Build markdown for a HijackLibs entry."""
        name = data.get("Name", file_path.stem)
        author = data.get("Author", "")
        vendor = data.get("Vendor", "")
        expected_locations = data.get("ExpectedLocations", []) or []
        vulnerable_executables = data.get("VulnerableExecutables", []) or []
        cves = as_list(data.get("CVE"))
        resources = data.get("Resources", []) or []

        lines = [
            f"# HijackLibs: {name}",
            "",
            f"**DLL Name**: {name}",
        ]
        if vendor:
            lines.append(f"**Vendor**: {vendor}")
        if author:
            lines.append(f"**Author**: {author}")
        lines.append("")

        if expected_locations:
            lines.append("## Expected Locations")
            for loc in expected_locations:
                lines.append(f"- `{loc}`")
            lines.append("")

        if vulnerable_executables:
            lines.append("## Vulnerable Executables")
            lines.append("")
            for vuln_exe in vulnerable_executables:
                if not isinstance(vuln_exe, dict):
                    continue
                exe_path = vuln_exe.get("Path", "")
                hijack_type = vuln_exe.get("Type", "")
                auto_elevate = vuln_exe.get("AutoElevate", False)
                privilege_escalation = vuln_exe.get("PrivilegeEscalation", False)
                condition = vuln_exe.get("Condition", "")
                variable = vuln_exe.get("Variable", "")
                sha256_hashes = as_list(vuln_exe.get("SHA256"))
                expected_version = vuln_exe.get("ExpectedVersionInformation")
                expected_signature = vuln_exe.get("ExpectedSignatureInformation")

                lines.append(f"### `{exe_path}`")
                if hijack_type:
                    lines.append(f"- **Hijack Type**: {hijack_type}")
                if condition:
                    lines.append(f"- **Condition**: {condition}")
                if variable:
                    lines.append(f"- **Variable**: `{variable}`")
                if sha256_hashes:
                    lines.append("- **SHA256**:")
                    lines.extend(f"  - `{sha256}`" for sha256 in sha256_hashes)
                if auto_elevate:
                    lines.append(f"- **Auto-Elevated**: Yes")
                if privilege_escalation:
                    lines.append(f"- **Privilege Escalation**: Yes")
                self._append_detail_map(
                    lines,
                    "Expected Version Information",
                    expected_version,
                )
                self._append_detail_map(
                    lines,
                    "Expected Signature Information",
                    expected_signature,
                )
                lines.append("")

        if cves:
            lines.append("## CVEs")
            for cve in cves:
                lines.append(f"- `{cve}`")
            lines.append("")

        if resources:
            lines.append("## Resources")
            for res in resources:
                lines.append(f"- {res}")
            lines.append("")

        return to_markdown("\n".join(lines))

    def _extract_metadata(self, data: dict) -> dict[str, Any]:
        """Extract retrieval metadata from a HijackLibs YAML entry."""
        vuln_exes = data.get("VulnerableExecutables", []) or []
        hijack_types = set()
        exe_paths = []
        executable_metadata = []

        for ve in vuln_exes:
            if not isinstance(ve, dict):
                continue

            hijack_type = ve.get("Type", "")
            exe_path = ve.get("Path", "")
            condition = ve.get("Condition", "")
            variable = ve.get("Variable", "")
            ve_sha256_hashes = as_list(ve.get("SHA256"))
            ve_auto_elevate = bool(ve.get("AutoElevate", False))
            ve_privilege_escalation = bool(ve.get("PrivilegeEscalation", False))
            ve_expected_version = ve.get("ExpectedVersionInformation") or []
            ve_expected_signature = ve.get("ExpectedSignatureInformation") or []
            executable = {
                "path": exe_path,
                "type": hijack_type,
                "sha256_hashes": ve_sha256_hashes,
                "auto_elevate": ve_auto_elevate,
                "privilege_escalation": ve_privilege_escalation,
            }

            if hijack_type:
                hijack_types.add(hijack_type)
            if exe_path:
                exe_paths.append(exe_path)
            if condition:
                executable["condition"] = condition
            if variable:
                executable["variable"] = variable
            if ve_expected_version:
                executable["expected_version_information"] = ve_expected_version
            if ve_expected_signature:
                executable["expected_signature_information"] = ve_expected_signature
            executable_metadata.append(executable)

        return {
            "dll_name": data.get("Name", ""),
            "vendor": data.get("Vendor", ""),
            "hijack_types": sorted(hijack_types),
            "vulnerable_exe_count": len(vuln_exes),
            "executable_paths": exe_paths,
            "expected_locations": data.get("ExpectedLocations", []) or [],
            "mitre_attack_ids": ["T1574"],
            "cves": as_list(data.get("CVE")),
            "vulnerable_executables": executable_metadata,
        }

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone HijackLibs repo: {e}")
            self.duration = time() - start_time
            return 0

        yml_dir = self.clone_path / "yml"
        if not yml_dir.exists():
            self.errors.append(f"HijackLibs yml directory not found: {yml_dir}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        for yml_file in sorted(yml_dir.rglob("*.yml")):
            try:
                text = yml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
                if not data or not isinstance(data, dict):
                    continue

                name = data.get("Name", yml_file.stem)

                markdown = self._build_markdown(data, yml_file)
                metadata = self._extract_metadata(data)
                rel_file = yml_file.relative_to(yml_dir)
                rel_stem = rel_file.with_suffix("").as_posix()
                rel_path = rel_file.with_suffix(".html").as_posix()

                doc = RawDocument(
                    doc_id=f"hijacklib-{slugify(rel_stem)}",
                    source="hijacklibs",
                    source_url=f"https://hijacklibs.net/entries/{rel_path}",
                    title=f"HijackLibs: {name}",
                    date_collected=date.today(),
                    date_published=data.get("Created"),
                    content_type="abuse_database",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=count_words(markdown),
                )
                docs.append(doc)

            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {yml_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {yml_file}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "hijacklibs")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} HijackLibs entries "
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
