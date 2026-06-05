import datetime
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from lxml import etree

from collectors.base import BaseCollector
from collectors.schemas import RawDocument

class CISAAdvisoryCollector(BaseCollector):
    SOURCE_URL = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
    LICENSE = "Public Domain"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.rss_url = config.get("rss_url", self.SOURCE_URL)
        self.request_delay_seconds = config.get("request_delay_seconds", 1.0)
        self.max_advisories = config.get("max_advisories", None)
        self.user_agent = config.get("user_agent", "dfir-dataset-collector/0.1 (research)")
        
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.doc_count = 0
        self.duration = 0.0

    def collect(self, output_dir: Path) -> int:
        start_time = time.time()
        headers = {"User-Agent": self.user_agent}

        try:
            resp = requests.get(self.rss_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # Use lxml HTML parser because the RSS might be messy, or standard XML parser
            # etree.fromstring requires bytes
            root = etree.fromstring(resp.content)
        except Exception as e:
            self.errors.append(f"Failed to fetch or parse CISA RSS feed: {e}")
            self.duration = time.time() - start_time
            return 0

        # RSS feed items
        items = root.findall(".//item")
        if self.max_advisories is not None:
            items = items[:self.max_advisories]

        docs = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for item in items:
            title_elem = item.find("title")
            link_elem = item.find("link")
            pub_date_elem = item.find("pubDate")
            
            title = title_elem.text if title_elem is not None else "Unknown Title"
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""

            if not link:
                self.warnings.append(f"No link found for advisory: {title}")
                continue

            try:
                time.sleep(self.request_delay_seconds)
                page_resp = requests.get(link, headers=headers, timeout=30)
                page_resp.raise_for_status()
                soup = BeautifulSoup(page_resp.content, "lxml")
            except Exception as e:
                self.warnings.append(f"Failed to fetch advisory {link}: {e}")
                continue

            content_div = soup.find("div", class_="l-content") or soup.find("main") or soup.body
            if not content_div:
                self.warnings.append(f"Could not find main content for {link}")
                continue

            body_text = content_div.get_text(separator="\n")

            cves = list(set(re.findall(r"CVE-\d{4}-\d{4,7}", body_text)))
            mitre_techniques = list(set(re.findall(r"T\d{4}(?:\.\d{3})?", body_text)))

            iocs = {
                "ips": list(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", body_text))),
                "hashes": list(set(re.findall(r"\b[A-Fa-f0-9]{32,64}\b", body_text)))
            }

            markdown_lines = [
                f"# {title}",
                "",
                f"**Published:** {pub_date}",
                f"**Source:** {link}",
                "",
                "## Content",
                body_text.strip(),
                ""
            ]

            content_markdown = self._to_markdown("\n".join(markdown_lines))

            advisory_id = link.rstrip("/").split("/")[-1]

            doc = RawDocument(
                doc_id=f"cisa-{advisory_id}",
                source="cisa_advisories",
                source_url=link,
                title=title,
                date_collected=collected_at,
                date_published=pub_date,
                content_type="advisory",
                content_markdown=content_markdown,
                metadata={
                    "advisory_id": advisory_id,
                    "cves": cves,
                    "affected_products": [],
                    "iocs": iocs,
                    "mitre_techniques": mitre_techniques,
                    "severity": "unknown"
                },
                license=self.LICENSE,
                word_count=self._count_words(content_markdown)
            )
            docs.append(doc)

        self.doc_count = self._write_documents(docs, output_dir, "cisa_advisories")
        self.duration = time.time() - start_time
        return self.doc_count

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}

    def manifest(self) -> dict[str, Any]:
        return {
            "collector": "CISAAdvisoryCollector",
            "version": self.VERSION,
            "source_url": self.rss_url,
            "license": self.LICENSE,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_count": self.doc_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration
        }
