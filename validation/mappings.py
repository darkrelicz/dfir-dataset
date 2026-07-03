import re

MITRE_ID_RE = re.compile(r"^T\d{4}(?:\.\d{3})?\??$")
MITRE_ID_ANYWHERE_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\??\b")
ATLAS_ID_RE = re.compile(r"^AML\.T\d{4}(?:\.\d{3})?\??$")
ATLAS_ID_ANYWHERE_RE = re.compile(r"\bAML\.T\d{4}(?:\.\d{3})?\??\b")


def normalized_mapping_id(value: str) -> str:
    return value.rstrip("?")
