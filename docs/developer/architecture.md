<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Architecture

This repository is a Python dataset pipeline. It is not a product frontend, API
server, or model-serving runtime.

## Runtime

| Area | Current Implementation |
|---|---|
| Language | Python 3.11+ |
| Packaging | `pyproject.toml` with setuptools |
| CLI entrypoints | `dfir-collect`, `dfir-synthesize`, `dfir-quality`, `dfir-package`, `dfir-evaluate`, `dfir-compare-evals`, `dfir-train-lora` |
| Core libraries | `pydantic`, `pyyaml`, `jsonlines`, `google-genai`, `requests`, `gitpython`, `rich`, `tqdm`, `mitreattack-python`, `unsloth`, `transformers`, `trl` |

## Component View

<puml src="../diagrams/pipeline-component.puml" alt="Component diagram for the dataset factory" width="1000" />

## End-To-End Sequence

<puml src="../diagrams/end-to-end-sequence.puml" alt="End-to-end sequence diagram" width="1000" />

## Phase 6 Evaluation Sequence

<puml src="../diagrams/phase6-evaluation-sequence.puml" alt="Sequential Phase 6 target generation, judging, and checkpointing" width="1000" />

## Main Packages

| Path | Responsibility |
|---|---|
| `collectors/` | Phase 2 source-specific collection into `RawDocument` JSONL. |
| `scripts/collect_all.py` | CLI orchestrator for configured collectors. |
| `synthesizers/` | Phase 3 planning, prompt rendering, Gemini generation, run state, and generated-output validation. |
| `synthesizers/prompts/` | Base, category, source-type, content-type, and compactor prompt assets. |
| `validation/` | Pure reusable validation primitives shared by Phase 3 and Phase 4. |
| `quality/` | Phase 4 row gates, scoring, references, dataset audits, and output writing. |
| `dataset_packaging/` | Phase 5 local JSONL packaging for Unsloth/GLM SFT. |
| `evaluation/` | Phase 6 local LLM judging, structured-output parsing, sequential target/judge orchestration, scorecard manifests, and comparison gates. |
| `scripts/` | Thin CLI entrypoints that dispatch to package runners. |
| `utils/` | Low-level helpers for IO, text normalization, Markdown frontmatter, and git URLs. |
| `configs/` | Machine-readable policy and pipeline settings. |
| `project_state/` | Durable project memory and operating guides. |
| `docs/` | This MarkBind successor guide site. |

## Pipeline Phases

### Phase 2 Collection

`scripts.collect_all` loads `configs/collection.yaml`, maps source keys to
collector classes, and runs selected collectors. Each collector writes one JSONL
file under `data/raw/<source>/` and returns a `CollectionManifest` entry. The
script combines these entries into `data/raw/collection_manifest.json`.

### Phase 3 Synthesis

`scripts.synthesize` exposes three subcommands:

* `validate-raw`
* `render-prompts`
* `run`

`synthesizers.planner` selects documents and assigns category/difficulty.
`PromptBuilder` renders prompt records from config and templates. Prompt-time
compactors produce shorter source views without mutating raw documents.

`GeminiClient` uses the Google GenAI SDK `models.generate_content` path with
structured JSON response settings. The runner writes prompts, raw outputs,
accepted candidate rows, rejected rows, and a generation manifest.

### Shared Validation

`validation/` holds pure primitives:

* reasoning block parsing and link validation;
* grounding field and `[GENERAL KNOWLEDGE]` tag consistency;
* concrete indicator extraction and invention checks;
* ATT&CK/ATLAS ID regexes;
* taxonomy ref extraction from config.

Phase 3 and Phase 4 call these primitives through separate policy wrappers.

### Phase 4 Quality

`quality.runner` loads configs, raw docs, and references; validates every Phase 3
candidate row; scores candidates; applies dataset gates; writes filtered,
review, rejected, spot-check, and manifest outputs.

Phase 4 deliberately does not call Phase 3's generated-output validators.

### Phase 5 Packaging

`dataset_packaging.runner` reads Phase 4 filtered and review rows, builds
chat-style message records, splits by `source_doc_id`, writes train/validation/test
JSONL, and creates a packaging manifest. The package name is
`dataset_packaging/` to avoid shadowing Python's third-party `packaging` module.

### Phase 6 Evaluation And Training

`evaluation.runner` loads held-out benchmark cases and calls either a local
OpenAI-compatible model endpoint or a prediction JSONL file. A separately
configured local judge is mandatory, and the runner writes only
`scorecards/llm_judge/`. Cases are processed sequentially: the target response
is generated, that response is judged, and only then does the runner advance to
the next case. After every verdict, predictions, case results, aggregate scores,
and the run manifest are atomically refreshed. Partial checkpoints are marked
`in_progress`; comparison accepts only `complete` scorecards. Objective TTP,
IOC, and ranking tasks request structured JSON for inspectability, but the judge
now evaluates both formatting and content.

These checkpoints do not implement resume. A new invocation starts the case
loop from the beginning and does not hydrate prior predictions or scores.

The judge receives the answer key, scoring rubric, and `acceptable_variants`.
Each variant is a complete independently valid alternative. Its structured
verdict includes a bounded score, concise reason, optional criterion scores, and
a range-validated matched-variant index.

`evaluation.comparison` accepts only judge scorecards and requires matching
benchmark fingerprint, case IDs, judge protocol/configuration fingerprint, and
calibration ID. Per-task regression gates prevent a headline improvement from
hiding a material task regression. `calibration_id` is reproducibility metadata,
not an implemented calibration procedure. The comparison currently checks that
IDs are present and equal but does not reject the placeholder value
`uncalibrated`; release policy must enforce a real ID until code does.

`scripts.finetune` launches local Unsloth LoRA SFT using
`configs/finetune_glm47flash.yaml`.

## Current Generated State

The current reduced-subset package is:

```text
data/packaged/gemini_subset_1/
```

It contains 5,517 records split into 4,414 train, 552 validation, and 551 test
rows. The split has no `source_doc_id` overlap.

The first training run is `train-20260714T025314Z`. It completed one epoch and
552 steps with final training loss `0.95973044`, then exported a LoRA adapter
and Q4_K_M GGUF under `data/finetune/glm47_flash_subset1/`.

The exploratory base evaluation `data/evaluation/glm47-flash-base/` completed
68/68 cases with overall normalized judge score `0.7588`. Its calibration ID is
`uncalibrated`, so the result verifies the runner and provides diagnostic cases
but is not a final baseline. Calibrated base and tuned runs remain outstanding.

## Important Architectural Decisions

* Raw documents remain complete. Prompt-cost reduction happens only during
  Phase 3 prompt rendering.
* Config files own policy; Python modules own mechanics.
* Canonical responses use `<reasoning>`, not `<think>`.
* Gemini 2.5 Flash is the primary teacher model for canonical generation.
* Alternate teacher models must run as separate labeled jobs.
* Phase 3 `accepted.jsonl` is candidate data, not final training data.
* Phase 5 currently packages filtered plus review rows by explicit time-boxed
  decision.
* Phase 6 benchmark cases are held out from synthesis/training and must be
  manually reviewed before baseline scoring.
* A complete evaluation checkpoint is not necessarily calibrated evidence;
  comparison claims require the same frozen, non-placeholder calibration ID.
