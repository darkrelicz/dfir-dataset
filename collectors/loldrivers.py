"""AF7: LOLDrivers Collector.

Clones the magicsword-io/LOLDrivers repository and parses YAML files
describing vulnerable and malicious Windows drivers.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest, logger
from collectors.schemas import RawDocument


class LOLDriversCollector(BaseCollector):

    SOURCE_URL = "https://github.com/magicsword-io/LOLDrivers.git"

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

    def _build_markdown(self, data: dict) -> str:
        """Build markdown for a LOLDrivers entry."""
        driver_id = data.get("Id", "")
        tags = data.get("Tags", []) or []
        author = data.get("Author", "")
        created = data.get("Created", "")
        category = data.get("Category", "")
        verified = data.get("Verified", "")
        mitre_id = data.get("MitreID", "")
        commands = data.get("Commands", {}) or {}
        resources = data.get("Resources", []) or []
        detection = data.get("Detection", []) or []
        acknowledgements = data.get("Acknowledgement", []) or []
        known_samples = data.get("KnownVulnerableSamples", []) or []

        driver_name = tags[0] if tags else driver_id

        lines = [
            f"# LOLDriver: {driver_name}",
            "",
            f"**Category**: {category}",
        ]
        if mitre_id:
            lines.append(f"**MITRE ATT&CK**: {mitre_id}")
        if verified:
            lines.append(f"**Verified**: {verified}")
        if author:
            lines.append(f"**Author**: {author}")
        lines.append("")

        # Commands / Abuse info
        if commands:
            lines.append("## Abuse Details")
            if isinstance(commands, dict):
                cmd_text = commands.get("Command", "")
                cmd_desc = commands.get("Description", "")
                usecase = commands.get("Usecase", "")
                privileges = commands.get("Privileges", "")
                operating_system = commands.get("OperatingSystem", "")

                if cmd_desc:
                    lines.append(f"**Description**: {cmd_desc}")
                if usecase:
                    lines.append(f"**Use Case**: {usecase}")
                if privileges:
                    lines.append(f"**Privileges**: {privileges}")
                if operating_system:
                    lines.append(f"**OS**: {operating_system}")
                if cmd_text:
                    lines.append("```")
                    lines.append(str(cmd_text).strip())
                    lines.append("```")
            lines.append("")

        # Known vulnerable samples
        if known_samples:
            lines.append("## Known Vulnerable Samples")
            lines.append("")
            for sample in known_samples[:10]:  # Cap at 10 for readability
                if not isinstance(sample, dict):
                    continue
                filename = sample.get("Filename", "Unknown")
                sha256 = sample.get("SHA256", "")
                sha1 = sample.get("SHA1", "")
                md5 = sample.get("MD5", "")
                publisher = sample.get("Publisher", "")
                company = sample.get("Company", "")
                desc = sample.get("Description", "")
                product = sample.get("Product", "")

                lines.append(f"### {filename}")
                if desc:
                    lines.append(f"- **Description**: {desc}")
                if publisher:
                    lines.append(f"- **Publisher**: {publisher}")
                if company:
                    lines.append(f"- **Company**: {company}")
                if product:
                    lines.append(f"- **Product**: {product}")
                if sha256:
                    lines.append(f"- **SHA256**: `{sha256}`")
                if sha1:
                    lines.append(f"- **SHA1**: `{sha1}`")
                if md5:
                    lines.append(f"- **MD5**: `{md5}`")
                lines.append("")

        if detection:
            lines.append("## Detection")
            for det in detection:
                if isinstance(det, dict):
                    det_type = det.get("type", "")
                    det_value = det.get("value", "")
                    lines.append(f"- **{det_type}**: {det_value}")
                else:
                    lines.append(f"- {det}")
            lines.append("")

        if resources:
            lines.append("## Resources")
            for res in resources:
                lines.append(f"- {res}")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone LOLDrivers repo: {e}")
            self.duration = time() - start_time
            return 0

        # LOLDrivers YAML files are in yaml/ directory
        yaml_dir = self.clone_path / "yaml"
        if not yaml_dir.exists():
            # Try alternate paths
            for alt in ["drivers", "loldrivers/content/drivers"]:
                alt_dir = self.clone_path / alt
                if alt_dir.exists():
                    yaml_dir = alt_dir
                    break

        if not yaml_dir.exists():
            self.errors.append(f"LOLDrivers yaml directory not found under {self.clone_path}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        for yml_file in sorted(yaml_dir.rglob("*.yaml")) + sorted(yaml_dir.rglob("*.yml")):
            try:
                text = yml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
                if not data or not isinstance(data, dict):
                    continue

                driver_id = data.get("Id", yml_file.stem)
                tags = data.get("Tags", []) or []
                category = data.get("Category", "unknown")
                driver_name = tags[0] if tags else driver_id

                markdown = self._build_markdown(data)

                # Extract hashes from samples
                hashes = []
                for sample in data.get("KnownVulnerableSamples", []) or []:
                    if isinstance(sample, dict):
                        for hash_type in ["SHA256", "SHA1", "MD5"]:
                            h = sample.get(hash_type, "")
                            if h:
                                hashes.append(f"{hash_type}:{h}")

                cves = data.get("CVE", []) or []

                metadata: dict[str, Any] = {
                    "driver_id": str(driver_id),
                    "driver_name": driver_name,
                    "category": category,
                    "tags": tags,
                    "cves": cves,
                    "mitre_id": data.get("MitreID", ""),
                    "verified": str(data.get("Verified", "")),
                    "sample_count": len(data.get("KnownVulnerableSamples", []) or []),
                    "hashes": hashes[:20],  # Cap for size
                }

                doc = RawDocument(
                    doc_id=f"loldriver-{str(driver_id).lower()[:50]}",
                    source="loldrivers",
                    source_url=f"https://www.loldrivers.io/drivers/{driver_id}/",
                    title=f"LOLDriver: {driver_name}",
                    date_collected=date.today(),
                    date_published=None,
                    content_type="abuse_database",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except yaml.YAMLError as e:
                self.warnings.append(f"YAML parse error in {yml_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {yml_file}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "loldrivers")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} LOLDrivers entries in {self.duration:.1f}s")
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

