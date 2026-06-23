from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Difficulty = Literal["junior", "mid", "senior"]
Confidence = Literal["high", "medium", "low"]
Grounding = Literal["source_only", "source_plus_general"]
ReasoningFormat = Literal["canonical_reasoning_v1"]


class InstructionPair(BaseModel):
    """Canonical synthesized instruction pair before quality filtering."""

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


class PromptRecord(BaseModel):
    """One model prompt to generate pairs for a raw source document."""

    prompt_id: str
    source_doc_id: str
    source: str
    source_type: str
    content_type: str
    category: str
    difficulty: Difficulty
    pairs_requested: int
    prompt: str


class GenerationManifest(BaseModel):
    """Audit metadata for a synthesis run or dry-run prompt render."""

    run_id: str
    mode: Literal["pilot", "full", "dry_run"]
    model: str
    created_at: datetime
    source_doc_count: int
    prompt_count: int
    output_dir: str
    config_path: str
    notes: list[str] = Field(default_factory=list)


class RawCorpusIssue(BaseModel):
    path: str
    line: int | None = None
    message: str


class RawCorpusValidation(BaseModel):
    raw_dir: str
    file_count: int
    document_count: int
    unique_doc_ids: int
    source_counts: dict[str, int]
    issues: list[RawCorpusIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


class ReasoningLinkIssue(BaseModel):
    message: str


class ReasoningLinkValidation(BaseModel):
    ok: bool
    evidence_ids: list[str]
    analysis_ids: list[str]
    conclusion_ids: list[str]
    caveat_ids: list[str]
    issues: list[ReasoningLinkIssue] = Field(default_factory=list)


class GeneratedPairIssue(BaseModel):
    source_doc_id: str | None = None
    pair_index: int | None = None
    message: str


class GeneratedPairValidation(BaseModel):
    ok: bool
    pairs: list[InstructionPair] = Field(default_factory=list)
    issues: list[GeneratedPairIssue] = Field(default_factory=list)
