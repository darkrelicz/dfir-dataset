from datetime import date, datetime
from typing import Any
from pydantic import BaseModel

class RawDocument(BaseModel):
    """Standardized raw document output by all collectors."""
    doc_id: str                           # e.g. "mitre-attack-T1059.001"
    source: str                           # e.g. "mitre_attack"
    source_url: str
    title: str
    date_collected: date                  
    date_published: date | None = None
    content_type: str                     # e.g. "technique_definition", "sigma_rule"
    content_markdown: str                 # Full content as markdown
    metadata: dict[str, Any]              # Source-specific metadata
    license: str
    word_count: int

class CollectionManifest(BaseModel):
    """Manifest written after each collection run."""
    collector: str
    version: str
    source_url: str
    collected_at: datetime
    document_count: int
    errors: list[str] = []
    warnings: list[str] = []
    duration_seconds: float
