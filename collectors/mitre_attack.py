from datetime import date, datetime, timezone
from pathlib import Path
from time import time
from typing import Any

from mitreattack.stix20 import MitreAttackData

from collectors.base import BaseCollector, CollectionManifest


class MitreAttackCollector(BaseCollector):
    def __init__(self, config: dict):
        self.config = config
        self.file = config["file"]
        self.include_revoked_deprecated = config.get("include__revoked_deprecated", False)

        self.errors = []
        self.warnings = []
        self.duration = 0.0
        self.doc_count = 0

    def collect(self, output_dir: Path) -> int:
        start_time = time()

        try:
            mitre_data = MitreAttackData(str(self.file))
        except Exception as e:
            self.errors.append(f"Failed to load MitreAttackData: {e}")
            self.duration = time() - start_time
            return 0
        
        techniques = mitre_data.get_techniques(remove_revoked_deprecated=not self.include_revoked_deprecated)
        for technique in techniques:
            print(technique)

        collected_at = datetime.now(timezone.utc).isoformat()
        return self.doc_count