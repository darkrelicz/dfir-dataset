"""C4: CISA Advisories Collector.

Clones the cisagov/CSAF repository which contains machine-readable CSAF
(Common Security Advisory Framework) JSON files for both IT and OT
advisories. One document per advisory JSON file.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import logging

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument

logger = logging.getLogger(__name__)


class CISAAdvisoriesCollector(BaseCollector):

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

    def _extract_cves(self, vulnerabilities: list[dict]) -> list[str]:
        """Extract CVE IDs from the vulnerabilities array."""
        cves = []
        for vuln in vulnerabilities:
            cve = vuln.get("cve", "")
            cves.append(cve)
        return cves

    def _build_markdown(self, advisory: dict) -> str:
        """Build markdown from a CSAF advisory JSON."""
        document = advisory.get("document", {})
        vulnerabilities = advisory.get("vulnerabilities", [])

        title = document.get("title", "Untitled Advisory")
        tracking = document.get("tracking", {})
        publisher = document.get("publisher", {})
        notes = document.get("notes", [])
        references = document.get("references", [])

        lines = [
            f"# {title}",
            "",
            f"**Category**: {document.get('category', '')}",
            f"**Publisher**: {publisher.get('name', '')}",
            f"**Published**: {tracking.get('initial_release_date', '')}",
            f"**Last Updated**: {tracking.get('current_release_date', '')}",
            f"**Version**: {tracking.get('version', '')}",
            "",
        ]

        # Notes (contains the actual advisory content)
        if notes:
            for note in notes:
                note_category = note.get("category", "")
                note_title = note.get("title", "")
                note_text = note.get("text", "")

                header = note_title or note_category
                if header:
                    lines.append(f"## {header}")
                if note_text:
                    lines.append(note_text)
                lines.append("")

        # Vulnerabilities
        if vulnerabilities:
            lines.append("## Vulnerabilities")
            lines.append("")
            for vuln in vulnerabilities:
                cve = vuln.get("cve", "Unknown")
                vuln_title = vuln.get("title", "")
                lines.append(f"### {cve}")
                if vuln_title:
                    lines.append(f"**Title**: {vuln_title}")

                notes = vuln.get("notes", [])
                summary = ""
                for note in notes:
                    if note.get("category") == "summary":
                        summary = note.get("text")
                        break

                if summary:
                    lines.append(f"**Summary**: {summary}")

                # CVSS scores
                scores = vuln.get("scores", [])
                for score in scores:
                    cvss = score.get("cvss_v3", {}) or score.get("cvss_v2", {})
                    if cvss:
                        base_score = cvss.get("baseScore", "")
                        severity = cvss.get("baseSeverity", "")
                        vector = cvss.get("vectorString", "")
                        if base_score:
                            lines.append(f"- **CVSS Score**: {base_score} ({severity})")
                        if vector:
                            lines.append(f"- **Vector**: `{vector}`")

                # CWE
                cwes = vuln.get("cwe", {})
                if cwes:
                    cwe_id = cwes.get("id", "")
                    cwe_name = cwes.get("name", "")
                    if cwe_id:
                        lines.append(f"- **CWE**: {cwe_id} - {cwe_name}")

                # Remediation
                remediations = vuln.get("remediations", [])
                if remediations:
                    lines.append("**Remediations**:")
                    for rem in remediations:
                        details = rem.get("details", "")
                        rem_url = rem.get("url", "")
                        if details:
                            lines.append(f"- {details}")
                        if rem_url:
                            lines.append(f"  - URL: {rem_url}")

                lines.append("")

        # References
        if references:
            lines.append("## References")
            for ref in references:
                ref_url = ref.get("url", "")
                ref_summary = ref.get("summary", "")
                if ref_url:
                    lines.append(f"- [{ref_summary or ref_url}]({ref_url})")
            lines.append("")

        return self._to_markdown("\n".join(lines))

    def collect(self) -> int:
        start_time = time()

        try:
            self._clone_repo(self.url, self.clone_path, shallow=self.shallow_clone)
        except Exception as e:
            self.errors.append(f"Failed to clone CSAF repo: {e}")
            self.duration = time() - start_time
            return 0

        if not self.clone_path.exists():
            self.errors.append(f"CSAF files directory not found: {self.clone_path}")
            self.duration = time() - start_time
            return 0

        docs: list[RawDocument] = []
        csaf_dir = self.clone_path / "csaf_files"

        advisory_files = sorted(csaf_dir.rglob("*.json"))
        logger.info(f"Found {len(advisory_files)} CSAF advisory files")

        for json_file in advisory_files:
            try:
                text = json_file.read_text(encoding="utf-8", errors="replace")
                advisory = json.loads(text)

                if not isinstance(advisory, dict) or "document" not in advisory:
                    continue

                document = advisory["document"]
                tracking = document.get("tracking", {})
                title = document.get("title", "Untitled")
                advisory_id = tracking.get("id", json_file.stem)
                category = document.get("category", "")

                vulnerabilities = advisory.get("vulnerabilities", [])
                cves = self._extract_cves(vulnerabilities)

                markdown = self._build_markdown(advisory)

                # Determine IT vs OT from file path
                rel_path = json_file.relative_to(csaf_dir)
                advisory_type = "Information Technology" if "IT" in str(rel_path) else "Operational Technology"

                date_published = None
                raw_date = tracking.get("initial_release_date", "")
                if raw_date:
                    try:
                        date_published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                metadata: dict[str, Any] = {
                    "advisory_id": advisory_id,
                    "category": category,
                    "advisory_type": advisory_type,
                    "cves": cves,
                    "cve_count": len(cves),
                    "publisher": document.get("publisher", {}).get("name", ""),
                    "version": tracking.get("version", ""),
                }

                doc = RawDocument(
                    doc_id=f"cisa-{advisory_id.lower()}",
                    source="cisa_advisories",
                    source_url=f"https://github.com/cisagov/CSAF/blob/develop/csaf_files/{rel_path}",
                    title=title,
                    date_collected=date.today(),
                    date_published=date_published,
                    content_type="threat_advisory",
                    content_markdown=markdown,
                    metadata=metadata,
                    word_count=self._count_words(markdown),
                )
                docs.append(doc)

            except json.JSONDecodeError as e:
                self.warnings.append(f"JSON parse error in {json_file}: {e}")
            except Exception as e:
                self.warnings.append(f"Error processing {json_file}: {e}")

        self.doc_count = self._write_documents(docs, self.output_dir, "cisa_advisories")
        self.duration = time() - start_time
        logger.info(f"Collected {self.doc_count} CISA advisories in {self.duration:.1f}s")
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
