"""C7: CISA Known Exploited Vulnerabilities (KEV) Catalog Collector.

Downloads the CISA KEV JSON catalog and groups entries by vendor,
producing one document per vendor group.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import requests

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)

class CISAKEVCollector(BaseCollector):

    def __init__(self, config: dict):
        self.config = config
        self.json_url = config["json_url"]
        self.output_dir = Path(config["output_dir"])
        self.group_by = config.get("group_by", "vendorProject")
        self.min_group_size = config.get("min_group_size", 1)

        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration = 0.0
        self.doc_count = 0

    def _build_markdown(self, vendor: str, entries: list[dict]) -> str:
        """Build markdown for a vendor group of KEV entries."""
        products = sorted(set(e.get("product", "Unknown") for e in entries))
        ransomware_entries = [e for e in entries if str(e.get("knownRansomwareCampaignUse", "")).lower() == "known"]

        lines = [
            f"# CISA KEV: {vendor}",
            "",
            f"**Vendor**: {vendor}",
            f"**Products**: {', '.join(products)}",
            f"**Total CVEs**: {len(entries)}",
            f"**Ransomware-linked**: {len(ransomware_entries)}",
            "",
        ]

        # Summary table
        lines.append("## Vulnerabilities")
        lines.append("")
        lines.append("| CVE | Product | Vulnerability Name | Ransomware | Due Date |")
        lines.append("|---|---|---|---|---|")

        for entry in sorted(entries, key=lambda e: e.get("dateAdded", "")):
            cve = entry.get("cveID", "N/A")
            product = entry.get("product", "N/A")
            vuln_name = entry.get("vulnerabilityName", "N/A")
            ransomware = "Yes" if str(entry.get("knownRansomwareCampaignUse", "")).lower() == "known" else "No"
            due_date = entry.get("dueDate", "N/A")
            lines.append(f"| {cve} | {product} | {vuln_name} | {ransomware} | {due_date} |")

        lines.append("")

        # Detailed entries
        lines.append("## Details")
        lines.append("")

        for entry in entries:
            cve = entry.get("cveID", "N/A")
            product = entry.get("product", "N/A")
            vuln_name = entry.get("vulnerabilityName", "")
            description = entry.get("shortDescription", "")
            action = entry.get("requiredAction", "")
            date_added = entry.get("dateAdded", "")
            due_date = entry.get("dueDate", "")
            is_known_ransom = "Yes" if str(entry.get("knownRansomwareCampaignUse", "")).lower() == "known" else "No"
            notes = entry.get("notes", "")
            cwes = entry.get("cwes", "N/A")

            lines.append(f"### {cve}: {vuln_name}")
            lines.append(f"- **Product**: {product}")
            lines.append(f"- **Date Added**: {date_added}")
            lines.append(f"- **Due Date**: {due_date}")
            lines.append(f"- **Linked to Ransomware Campagins**: {is_known_ransom}")
            if action:
                lines.append(f"- **Required Action**: {action}")
            if notes:
                lines.append(f"- **Notes**: {notes}")
            lines.append(f"- **CWEs**: {cwes}")
            lines.append(f"- **Description**: {description}")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            logger.info(f"Downloading CISA KEV catalog from {self.json_url}")
            resp = requests.get(self.json_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.errors.append(f"Failed to download KEV catalog: {e}")
            self.duration = time() - start_time
            return 0

        vulnerabilities = data.get("vulnerabilities", [])
        catalog_version = data.get("catalogVersion", "")
        catalog_date = self._parse_datetime(data.get("dateReleased", ""))
        logger.info(f"KEV catalog: {len(vulnerabilities)} entries, version {catalog_version}")

        # Group by vendor
        vendor_groups: dict[str, list[dict]] = defaultdict(list)
        for vuln in vulnerabilities:
            vendor = vuln.get(self.group_by, "Unknown")
            vendor_groups[vendor].append(vuln)

        docs: list[RawDocument] = []

        for vendor, entries in sorted(vendor_groups.items()):
            if len(entries) < self.min_group_size:
                continue

            try:
                markdown = self._build_markdown(vendor, entries)

                cve_ids = [e.get("cveID", "") for e in entries if e.get("cveID")]
                products = sorted(set(e.get("product", "") for e in entries))
                ransomware_count = sum(
                    1 for e in entries
                    if str(e.get("knownRansomwareCampaignUse", "")).lower() == "known"
                )

                vendor_slug = vendor.lower().replace(" ", "-").replace("/", "-")[:50]

                metadata: dict[str, Any] = {
                    "vendor": vendor,
                    "products": products,
                    "cve_ids": cve_ids,
                    "cve_count": len(entries),
                    "ransomware_linked_count": ransomware_count,
                    "catalog_version": catalog_version,
                }

                doc = RawDocument(
                    doc_id=f"kev-{vendor_slug}",
                    source="cisa_kev",
                    source_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                    title=f"CISA KEV: {vendor} ({len(entries)} CVEs)",
                    date_collected=date.today(),
                    date_published=catalog_date,
                    content_type="vulnerability_catalog",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except Exception as e:
                self.warnings.append(f"Failed to process vendor group {vendor}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "cisa_kev")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} KEV vendor groups in {self.duration:.1f}s")
        return self.doc_count

    def manifest(self) -> CollectionManifest:
        return CollectionManifest(
            collector=self.__class__.__name__,
            version=self.VERSION,
            source_url=self.json_url,
            collected_at=datetime.now(timezone.utc),
            document_count=self.doc_count,
            errors=self.errors,
            warnings=self.warnings,
            duration_seconds=self.duration,
        )
