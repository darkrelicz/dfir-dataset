<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Data Contracts</h1>

The pipeline is held together by a few stable Pydantic and JSONL contracts.

<puml src="../diagrams/raw-document-class.puml" alt="Class diagram for core data contracts" width="900" />

# RawDocument

Defined in `collectors/schemas.py`.

| Field | Type | Notes |
|---|---|---|
| `doc_id` | `str` | Stable source-specific ID. Must not depend on run order. |
| `source` | `str` | Source key such as `mitre_attack`. |
| `source_url` | `str` | Upstream source URL or public documentation URL. |
| `title` | `str` | Human-readable title. |
| `date_collected` | `date` | Collection date. |
| `date_published` | `datetime or None` | Upstream publication date when available. |
| `content_type` | `str` | Specific content label used by synthesis policy. |
| `content_markdown` | `str` | Normalized full source content. |
| `metadata` | `dict[str, Any]` | Source-specific structured metadata. |
| `word_count` | `int` | Count from `utils.text.count_words`. |

# CollectionManifest

Each collector returns a manifest entry with:

* collector class name;
* package version;
* source URL;
* collection timestamp;
* document count;
* errors and warnings;
* duration.

`scripts.collect_all` writes the combined list to
`data/raw/collection_manifest.json`.

# PromptRecord

Defined in `synthesizers/schemas.py`.

Prompt records represent one model call for one raw document:

* `prompt_id`
* `source_doc_id`
* `source`
* `source_type`
* `content_type`
* `category`
* `difficulty`
* `pairs_requested`
* `taxonomy_refs`
* `prompt`

`synthesizers.run_state.prompt_record_row` adds `prompt_hash` before writing
`prompts.jsonl`.

# InstructionPair

Defined in `synthesizers/schemas.py` with `extra="forbid"`.

| Field | Notes |
|---|---|
| `instruction` | Analyst-facing task prompt. |
| `response` | Must begin with canonical `<reasoning>` and end with a final answer. |
| `category` | Normalized from the prompt record in Phase 3 validation. |
| `difficulty` | `junior`, `mid`, or `senior`; normalized from prompt record. |
| `confidence` | `high`, `medium`, or `low`. |
| `mitre_techniques` | ATT&CK technique IDs only, optional `?` suffix. |
| `atlas_techniques` | ATLAS technique IDs only, optional `?` suffix. |
| `tools_referenced` | Tool names used for quality allowlist/source checks. |
| `source_doc_id` | Normalized from prompt record. |
| `source` | Normalized from prompt record. |
| `taxonomy_refs` | Normalized from prompt record. |
| `grounding` | `source_only` or `source_plus_general`. |

Phase 3 overwrites deterministic provenance fields from `PromptRecord` before
schema validation, because the teacher model should not be trusted for those
values.

# QualityCandidate And QualityDecision

`QualityCandidate` is the Phase 4 input schema. It mirrors `InstructionPair`,
but ignores extra fields because Phase 3 rows include run metadata.

`QualityDecision` contains:

* `status`: `filtered`, `review`, or `rejected`;
* `issues`: deterministic and heuristic issue codes;
* `score`: a `QualityScore` with five dimensions and total.

# Packaged Record

The current package format is `messages_jsonl`.

```json
{
  "id": "dfir-000001",
  "messages": [
    {"role": "system", "content": "You are Shepherd, a DFIR AI assistant..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "source_doc_id": "...",
    "source": "...",
    "category": "...",
    "difficulty": "...",
    "confidence": "...",
    "taxonomy_refs": [],
    "mitre_techniques": [],
    "atlas_techniques": [],
    "tools_referenced": [],
    "grounding": "...",
    "quality_status": "...",
    "quality_issues": [],
    "quality_score": {},
    "reasoning_style": "reasoning",
    "model_transforms": ["canonical_reasoning_to_glm_think"],
    "run_id": "...",
    "prompt_id": "...",
    "prompt_hash": "...",
    "pair_index": 0,
    "model": "...",
    "generated_at": "...",
    "quality_run_id": "...",
    "source_pair_key": "prompt-id:0"
  }
}
```

Canonical synthesis and quality records retain `<reasoning>` and grounding
annotations. A model-specific package may record export-time transformations in
`model_transforms`; the GLM v3 view maps retained reasoning tags, derives direct
answers for the configured subset, and removes literal `[GENERAL KNOWLEDGE]`
markers without changing canonical inputs.

# Manifest Contracts

| Manifest | Writer | Purpose |
|---|---|---|
| `collection_manifest.json` | `scripts.collect_all` | Raw collection summary. |
| `generation_manifest.json` | `synthesizers.runner` | Prompt/generation run summary. |
| `quality_manifest.json` | `quality.runner` | Quality counts, distributions, and audits. |
| `packaging_manifest.json` | `dataset_packaging.runner` | Split counts, response styles, and leakage check. |
| `evaluation_manifest.json` | `evaluation.runner` | Evaluation status, benchmark identity, target identity, case progress, and scorecard paths. |
| `training_manifest.json` | `scripts.finetune` | Dataset provenance, model/LoRA/export settings, and trainer result. |

# Phase 6 BenchmarkCase

Defined in `evaluation/schemas.py`. Each held-out case contains:

* stable `case_id`, `task_type`, and `difficulty`;
* target `prompt` and optional incident `context`;
* `expected_answer` concepts, exclusions, gold labels, and alternatives;
* per-case metric, strictly positive maximum points, and rubric;
* optional tags and notes for human reviewers.

`expected_answer.acceptable_variants` is a list of lists. Each inner list is one
complete independently acceptable alternative, not another cumulative set of
requirements. The answer key is sent only to the judge, never to the evaluated
target model.

# JudgeVerdict And CaseScore

The local judge must return a JSON object containing a bounded `score`, a
non-empty `reason`, optional numeric `criteria`, and an optional
`matched_acceptable_variant`. The matched index is zero-based and must point to
an existing acceptable variant.

The evaluator converts that verdict into `CaseScore`:

* raw score is bounded to the case's `max_points`;
* normalized score is raw score divided by maximum points;
* details retain the judge model, reason, criteria, matched variant, and
  validation-attempt count.

Because the evaluator has only one scoring mechanism, `CaseScore` and
`EvaluationManifest` do not contain evaluator-selection fields. The manifest
contains one singular `scorecard` summary.

# Prediction Replay Rows

`prediction_file` mode reads JSONL with exactly one candidate answer per
benchmark case. Every non-empty row must contain the canonical fields:

```json
{"case_id":"phase6-ai-atlas-001","prediction":"Candidate answer text"}
```

Additional metadata written by an earlier evaluation run is ignored. The
loader requires the `prediction` field, rejects duplicate `case_id` values, and
fails when a selected benchmark case has no matching row. Historical answer
aliases such as `response`, `output`, and `answer` are not accepted.

# Evaluation Outputs

After every successful verdict, `evaluation.runner` atomically refreshes:

| Output | Contract |
|---|---|
| `predictions.jsonl` | Target prediction and model metadata keyed by `case_id`. |
| `scorecard/case_results.jsonl` | One validated `CaseScore` per completed case. |
| `scorecard/scores.json` | Overall/task aggregates, case IDs, benchmark fingerprint, judge fingerprints, calibration ID, and run progress. |
| `evaluation_manifest.json` | Run identity, target configuration identity, case progress, status, and scorecard summary. |

Partial scorecards use `run_status: in_progress`; the last checkpoint changes
them to `complete`. The comparison command accepts only complete compatible
scorecards.
