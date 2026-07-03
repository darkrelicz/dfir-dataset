from collections.abc import Mapping
from typing import Any


def valid_taxonomy_refs_from_config(config: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    domains = config.get("taxonomy", {}).get("domains", {})
    for domain in domains.values():
        refs.update(str(value) for value in domain.get("ids", []))
    return refs
