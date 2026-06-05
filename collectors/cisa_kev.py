import datetime
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from collectors.base import BaseCollector
from collectors.schemas import RawDocument

class CISAKEVCollector(BaseCollector):
    SOURCE_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    LICENSE = "Public Domain"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.output_dir = config["output_dir"]
        self.json_url = config.get("json_url", self.SOURCE_URL)
        self.group_by = config.get("group_by", "vendorProject")
        self.min_group_size = config.get("min_group_size", 1)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.doc_count = 0
        self.duration = 0.0

    def collect(self, output_dir: Path) -> int:
        start_time = time.time()
        try:
            resp = requests.get(self.json_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.errors.append(f"Failed to fetch KEV catalog: {e}")
            self.duration = time.time() - start_time
            return 0

        vulnerabilities = data.get("vulnerabilities", [])
        
        groups = defaultdict(list)
        for vuln in vulnerabilities:
            vendor = vuln.get(self.group_by, "Unknown")
            groups[vendor].append(vuln)

        docs = []
        collected_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        for vendor, vulns in groups.items():
            if len(vulns) < self.min_group_size:
                continue
                
            vendor_slug = vendor.lower().replace(" ", "-").replace("/", "-")
            
            cve_list = []
            products = set()
            ransomware_count = 0
            dates = []
            
            markdown_lines = [f"# KEV Catalog: {vendor}", ""]
            markdown_lines.append("| CVE | Product | Date Added | Ransomware | Remediation |")
            markdown_lines.append("|---|---|---|---|---|")
            
            for v in vulns:
                cve = v.get("cveID", "")
                cve_list.append(cve)
                product = v.get("product", "")
                if product:
                    products.add(product)
                
                date_added = v.get("dateAdded", "")
                if date_added:
                    dates.append(date_added)
                    
                rw = v.get("knownRansomwareCampaignUse", "Unknown")
                if str(rw).lower() == "known":
                    ransomware_count += 1
                
                desc = v.get("shortDescription", "").replace("\n", " ")
                rem = v.get("requiredAction", "").replace("\n", " ")
                markdown_lines.append(f"| {cve} | {product} | {date_added} | {rw} | {rem} |")
                
            markdown_lines.append("")
            
            dates.sort()
            date_range = [dates[0], dates[-1]] if dates else []
            
            content_markdown = self._to_markdown("\n".join(markdown_lines))
            
            doc = RawDocument(
                doc_id=f"kev-{vendor_slug}",
                source="cisa_kev",
                source_url=self.json_url,
                title=f"CISA KEV Catalog for {vendor}",
                date_collected=collected_at,
                content_type="kev_vendor_group",
                content_markdown=content_markdown,
                metadata={
                    "vendor": vendor,
                    "cve_count": len(cve_list),
                    "cves": cve_list,
                    "products": list(products),
                    "ransomware_use_count": ransomware_count,
                    "date_range": date_range
                },
                license=self.LICENSE,
                word_count=self._count_words(content_markdown)
            )
            docs.append(doc)
            
        self.doc_count = self._write_documents(docs, output_dir, "cisa_kev")
        self.duration = time.time() - start_time
        return self.doc_count

    def validate(self, output_dir: Path) -> dict[str, Any]:
        return {}

    def manifest(self) -> dict[str, Any]:
        return {
            "collector": "CISAKEVCollector",
            "version": self.VERSION,
            "source_url": self.json_url,
            "license": self.LICENSE,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "document_count": self.doc_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration
        }
