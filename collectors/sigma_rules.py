from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

import requests

from collectors.base import BaseCollector, CollectionManifest
from collectors.schemas import RawDocument


class SigmaRulesCollector(BaseCollector):
    def __init__(self, config: dict):
        self.config = config
        self.url = config["url"]
        self.output_dir = Path(config["output_dir"])
        self.clone_path = Path(config["clone_path"])
        self.rules_subdir = Path(config["rules_subdir"])
        self.shadow_clone = config.get("shadow_clone", True)
        self.min_rule_level = config.get("min_rule_level")

        self.errors = []
        self.warnings = []
        self.duration = 0.0
        self.doc_count = 0

    def collect(self) -> int:
        start_time = time()

        docs = []

        self.doc_count = self._write_documents(docs, self.output_dir, "sigma_rules")
        self.duration = time() - start_time
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
    
if __name__ == "__main__":
    import yaml

    with open("configs/collection.yaml", "r") as f:
        full_config = yaml.safe_load(f)

    sigma_config = full_config["sources"]["sigma_rules"]
    collector = SigmaRulesCollector(config=sigma_config)

    collector.collect()
    print(collector.manifest())