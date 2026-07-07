from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PackagedSplitSummary(BaseModel):
    """Counts and output path for one packaged split."""

    path: str
    records: int
    source_doc_ids: int


class PackagingManifest(BaseModel):
    """Run summary for Phase 5 local dataset packaging."""

    run_id: str
    created_at: datetime
    config_path: str
    input_quality_dir: str
    quality_run_id: str | None = None
    output_dir: str
    packaged_pairs: int
    response_style: dict[str, Any]
    split_config: dict[str, Any]
    splits: dict[str, PackagedSplitSummary]
    source_doc_overlap: dict[str, list[str]]
