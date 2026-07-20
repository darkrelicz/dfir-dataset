from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExpectedAnswer(BaseModel):
    """Answer key fields supplied only to the Phase 6 LLM judge."""

    required_concepts: list["AnswerConcept"] = Field(default_factory=list)
    forbidden_concepts: list["AnswerConcept"] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    acceptable_variants: list[list[str]] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    gold_labels: dict[str, Any] = Field(default_factory=dict)


class AnswerConcept(BaseModel):
    """Atomic answer concept with aliases supplied to the judge."""

    id: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class ScoringConfig(BaseModel):
    """Per-case local-judge rubric settings."""

    max_points: float = Field(default=5.0, gt=0)
    rubric: list[Any] = Field(default_factory=list)


class TargetOutput(BaseModel):
    """Response format requested from the evaluated target model."""

    format: Literal[
        "free_form",
        "techniques_json",
        "iocs_json",
        "ranked_actions_json",
    ]


class BenchmarkCase(BaseModel):
    """Held-out benchmark case shown to the evaluated model."""

    case_id: str
    task_type: str
    difficulty: str
    prompt: str
    context: str | None = None
    expected_answer: ExpectedAnswer = Field(default_factory=ExpectedAnswer)
    target_output: TargetOutput
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    tags: list[str] = Field(default_factory=list)
    notes_for_human_reviewer: str | None = None


class CaseScore(BaseModel):
    """One LLM-judge score for one benchmark case."""

    case_id: str
    task_type: str
    score: float
    normalized_score: float
    max_points: float
    details: dict[str, Any] = Field(default_factory=dict)


class JudgeVerdict(BaseModel):
    """Validated structured response returned by a local LLM judge."""

    score: float
    reason: str
    criteria: dict[str, float] = Field(default_factory=dict)
    matched_acceptable_variant: int | None = None

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
    status: Literal["in_progress", "complete"]
    planned_case_count: int
    config_path: str
    cases_path: str
    output_dir: str
    model_label: str
    model: str
    generation_mode: str
    case_count: int
    case_ids: list[str]
    benchmark_fingerprint: str
    scorecard: dict[str, Any]
