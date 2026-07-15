from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExpectedAnswer(BaseModel):
    """Answer key fields used by deterministic Phase 6 scoring."""

    required_concepts: list["AnswerConcept"] = Field(default_factory=list)
    forbidden_concepts: list["AnswerConcept"] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    acceptable_variants: list[Any] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    gold_labels: dict[str, Any] = Field(default_factory=dict)


class AnswerConcept(BaseModel):
    """Atomic answer concept with acceptable deterministic aliases."""

    id: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class ScoringConfig(BaseModel):
    """Per-case metric and rubric settings."""

    metric: str = "rubric"
    max_points: float = 5.0
    rubric: list[Any] = Field(default_factory=list)


class BenchmarkCase(BaseModel):
    """Held-out benchmark case shown to the evaluated model."""

    case_id: str
    task_type: str
    difficulty: str
    prompt: str
    context: str | None = None
    expected_answer: ExpectedAnswer = Field(default_factory=ExpectedAnswer)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    tags: list[str] = Field(default_factory=list)
    notes_for_human_reviewer: str | None = None


class CaseScore(BaseModel):
    """One score produced by a named evaluator for one benchmark case."""

    case_id: str
    task_type: str
    evaluator: str
    metric: str
    score: float
    normalized_score: float
    max_points: float
    details: dict[str, Any] = Field(default_factory=dict)
    manual_review_recommended: bool = False


class JudgeVerdict(BaseModel):
    """Validated structured response returned by a local LLM judge."""

    score: float
    reason: str
    criteria: dict[str, float] = Field(default_factory=dict)

    @field_validator("reason")
    @classmethod
    def require_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("judge reason must not be empty")
        return value.strip()


class EvaluationManifest(BaseModel):
    """Run-level metadata for a Phase 6 evaluation pass."""

    run_id: str
    created_at: datetime
    config_path: str
    cases_path: str
    output_dir: str
    model_label: str
    model: str
    generation_mode: str
    evaluator_mode: str
    case_count: int
    case_ids: list[str]
    benchmark_fingerprint: str
    scorecards: dict[str, dict[str, Any]]
