from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QualitySeverity = Literal["reject", "review"]
QualityStatus = Literal["filtered", "rejected", "review"]
Difficulty = Literal["junior", "mid", "senior"]
Confidence = Literal["high", "medium", "low"]
Grounding = Literal["source_only", "source_plus_general"]
ReasoningFormat = Literal["canonical_reasoning_v1"]


class QualityCandidate(BaseModel):
    """Candidate instruction pair entering Phase 4 quality gates."""

    model_config = ConfigDict(extra="allow")

    instruction: str
    response: str
    category: str
    difficulty: Difficulty
    confidence: Confidence
    mitre_techniques: list[str] = Field(default_factory=list)
    atlas_techniques: list[str] = Field(default_factory=list)
    tools_referenced: list[str] = Field(default_factory=list)
    source_doc_id: str
    source: str
    taxonomy_refs: list[str] = Field(default_factory=list)
    grounding: Grounding
    reasoning_format: ReasoningFormat = "canonical_reasoning_v1"


class QualityIssue(BaseModel):
    """One deterministic or heuristic quality issue for a candidate pair."""

    code: str
    severity: QualitySeverity
    message: str


class QualityScore(BaseModel):
    """Heuristic Phase 4 score aligned with docs/QUALITY_RUBRIC.md."""

    factual_accuracy: float
    reasoning_quality: float
    operational_relevance: float
    specificity: float
    completeness: float
    total: float


class QualityDecision(BaseModel):
    """Quality decision for one Phase 3 accepted pair."""

    status: QualityStatus
    issues: list[QualityIssue] = Field(default_factory=list)
    score: QualityScore | None = None


class QualityManifest(BaseModel):
    """Run summary for a Phase 4 quality filtering pass."""

    run_id: str
    input_path: str
    raw_dir: str
    output_dir: str
    created_at: datetime
    total_pairs: int
    filtered_pairs: int
    review_pairs: int
    rejected_pairs: int
    rejection_counts: dict[str, int]
    review_counts: dict[str, int]
    source_distribution: dict[str, int]
    category_distribution: dict[str, int]
    difficulty_distribution: dict[str, int]
    taxonomy_distribution: dict[str, int]
    score_threshold: float | None = None
    review_threshold: float | None = None
    dataset_audits: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
