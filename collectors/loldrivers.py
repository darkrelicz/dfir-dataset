"""AF7: LOLDrivers Collector.

Clones the magicsword-io/LOLDrivers repository and parses YAML files
describing vulnerable and malicious Windows drivers.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import yaml

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument
from utils.text import as_list, to_markdown, count_words

logger = logging.getLogger(__name__)


class LOLDriversCollector(BaseCollector):

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

    def _extract_cves(self, data: dict) -> list[str]:
        cves = []
        for key in ("CVE", "CVEs"):
            for cve in as_list(data.get(key)):
                cve = str(cve).strip()
                if cve:
                    cves.append(cve)
        return list(dict.fromkeys(cves))

    def _sample_name(self, sample: dict, tags: list[str]) -> str:
        for key in ("Filename", "OriginalFilename", "InternalName"):
            value = sample.get(key)
            if value:
                return str(value)
        if tags:
            return str(tags[0])
        for key in ("SHA256", "SHA1", "MD5"):
            value = sample.get(key)
            if value:
                return str(value)[:12]
        return "Unknown"

    def _hash_map(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {
            str(key).lower(): str(hash_value)
            for key, hash_value in value.items()
            if hash_value not in (None, "", [])
        }

    def _extract_sample_metadata(
        self,
        samples: list,
        tags: list[str],
    ) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
        sample_metadata: list[dict[str, Any]] = []
        hashes: list[str] = []
        vendors: set[str] = set()
        products: set[str] = set()

        for sample in samples:
            if not isinstance(sample, dict):
                continue

            sample_hashes: dict[str, str] = {}
            for hash_type in ("SHA256", "SHA1", "MD5"):
                hash_value = sample.get(hash_type)
                if hash_value:
                    hash_value = str(hash_value)
                    sample_hashes[hash_type.lower()] = hash_value
                    hashes.append(f"{hash_type}:{hash_value}")

            metadata: dict[str, Any] = {"filename": self._sample_name(sample, tags)}
            for source_key, metadata_key in (
                ("OriginalFilename", "original_filename"),
                ("InternalName", "internal_name"),
                ("Description", "description"),
                ("Publisher", "publisher"),
                ("Company", "company"),
                ("Product", "product"),
                ("ProductVersion", "product_version"),
                ("FileVersion", "file_version"),
                ("MachineType", "machine_type"),
                ("CreationTimestamp", "creation_timestamp"),
                ("Imphash", "imphash"),
                ("LoadsDespiteHVCI", "loads_despite_hvci"),
            ):
                value = sample.get(source_key)
                if value not in (None, "", []):
                    metadata[metadata_key] = value

            if sample_hashes:
                metadata["hashes"] = sample_hashes

            authentihash = self._hash_map(sample.get("Authentihash"))
            if authentihash:
                metadata["authentihash"] = authentihash

            rich_pe_hash = self._hash_map(sample.get("RichPEHeaderHash"))
            if rich_pe_hash:
                metadata["rich_pe_header_hash"] = rich_pe_hash

            for vendor_key in ("Publisher", "Company"):
                vendor = sample.get(vendor_key)
                if vendor:
                    vendors.add(str(vendor))
            if sample.get("Product"):
                products.add(str(sample["Product"]))

            sample_metadata.append(metadata)

        return (
            sample_metadata,
            list(dict.fromkeys(hashes)),
            sorted(vendors),
            sorted(products),
        )

    def _extract_detections(self, detections: list) -> list[dict[str, str]]:
        detection_metadata: list[dict[str, str]] = []
        for detection in detections:
            if not isinstance(detection, dict):
                continue
            detection_type = str(detection.get("type", "")).strip()
            detection_value = str(detection.get("value", "")).strip()
            if detection_type and detection_value:
                detection_metadata.append(
                    {
                        "type": detection_type,
                        "value": detection_value,
                    }
                )
        return detection_metadata

    def _parse_created(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _build_markdown(self, data: dict) -> str:
        """Build markdown for a LOLDrivers entry."""
        driver_id = data.get("Id", "")
        tags = data.get("Tags", []) or []
        author = data.get("Author", "")
        created = data.get("Created", "")
        category = data.get("Category", "")
        verified = data.get("Verified", "")
        mitre_id = data.get("MitreID", "")
        cves = self._extract_cves(data)
        commands = data.get("Commands", {}) or {}
        resources = data.get("Resources", []) or []
        detections = self._extract_detections(data.get("Detection", []) or [])
        known_samples = data.get("KnownVulnerableSamples", []) or []

        driver_name = tags[0] if tags else driver_id

        lines = [
            f"# LOLDriver: {driver_name}",
            "",
            f"**Category**: {category}",
        ]
        if created:
            lines.append(f"**Created**: {created}")
        if mitre_id:
            lines.append(f"**MITRE ATT&CK**: {mitre_id}")
        if cves:
            lines.append("**CVEs**: " + ", ".join(f"`{cve}`" for cve in cves))
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
            for sample in known_samples:
                if not isinstance(sample, dict):
                    continue
                filename = self._sample_name(sample, tags)
                sha256 = sample.get("SHA256", "")
                sha1 = sample.get("SHA1", "")
                md5 = sample.get("MD5", "")
                publisher = sample.get("Publisher", "")
                company = sample.get("Company", "")
                desc = sample.get("Description", "")
                product = sample.get("Product", "")
                original_filename = sample.get("OriginalFilename", "")
                imphash = sample.get("Imphash", "")
                loads_despite_hvci = sample.get("LoadsDespiteHVCI", "")

                lines.append(f"### {filename}")
                if desc:
                    lines.append(f"- **Description**: {desc}")
                if original_filename and original_filename != filename:
                    lines.append(f"- **Original Filename**: {original_filename}")
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
                if imphash:
                    lines.append(f"- **Imphash**: `{imphash}`")
                if loads_despite_hvci not in ("", None):
                    lines.append(f"- **Loads Despite HVCI**: {loads_despite_hvci}")
                lines.append("")

        if detections:
            lines.append("## Detection")
            for detection in detections:
                lines.append(f"- **{detection['type']}**: {detection['value']}")
            lines.append("")

        if resources:
            lines.append("## Resources")
            for res in resources:
                lines.append(f"- {res}")
            lines.append("")

        return to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone LOLDrivers repo: {e}")
            self.duration = time() - start_time
            return 0

        yaml_dir = self.clone_path / "yaml"

        if not yaml_dir.exists():
            self.errors.append(
                f"LOLDrivers yaml directory not found under {self.clone_path}"
            )
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []

        for yml_file in sorted(yaml_dir.glob("*.yaml")):
            try:
                text = yml_file.read_text(encoding="utf-8", errors="replace")
                data = yaml.safe_load(text)
                if not data or not isinstance(data, dict):
                    continue

                driver_id = data.get("Id", yml_file.stem)
                tags = data.get("Tags", []) or []
                category = data.get("Category", "unknown")
                driver_name = tags[0] if tags else driver_id
                known_samples = data.get("KnownVulnerableSamples", []) or []
                commands = data.get("Commands", {}) or {}
                if not isinstance(commands, dict):
                    commands = {}

                markdown = self._build_markdown(data)
                samples, hashes, vendors, products = self._extract_sample_metadata(
                    known_samples,
                    tags,
                )
                cves = self._extract_cves(data)
                detections = self._extract_detections(data.get("Detection", []) or [])

                metadata: dict[str, Any] = {
                    "driver_id": str(driver_id),
                    "driver_name": driver_name,
                    "category": category,
                    "tags": tags,
                    "cves": cves,
                    "vendors": vendors,
                    "products": products,
                    "mitre_id": data.get("MitreID", ""),
                    "verified": str(data.get("Verified", "")),
                    "usecase": commands.get("Usecase", ""),
                    "privileges": commands.get("Privileges", ""),
                    "operating_system": commands.get("OperatingSystem", ""),
                    "sample_count": len(known_samples),
                    "hashes": hashes,
                    "detections": detections,
                    "samples": samples,
                }

                doc = RawDocument(
                    doc_id=f"loldriver-{str(driver_id).lower()}",
                    source="loldrivers",
                    source_url=f"https://www.loldrivers.io/drivers/{driver_id}/",
                    title=f"LOLDriver: {driver_name}",
                    date_collected=date.today(),
                    date_published=self._parse_created(data.get("Created")),
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

        self.doc_count = self._write_documents(docs, self.output_dir, "loldrivers")
        self.duration = time() - start_time
        logger.info(
            f"Collected {self.doc_count} LOLDrivers entries "
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
