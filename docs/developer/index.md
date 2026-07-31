<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Developer Guide</h1>

This guide explains how the DFIR dataset factory is structured and where each
part of the implementation lives. Read the architecture first, then follow the
pipeline from Collectors through Evaluation. Each stage page covers its
configuration, contracts, extension workflow, output lifecycle, and validation.

For command usage rather than implementation, use the [User
Guide](../user/index.md).

<box type="info" seamless header="Recommended reading order">

Start with [High-Level Architecture](#high-level-architecture), then continue
through the [Implementation Guide](#implementation-guide) beginning with
[Collectors](#1-collectors).

Read [Fine-tuning](finetuning.md) and [Evaluation](evaluation.md) together when
making a promotion decision.

</box>

---

## High-Level Architecture

<puml src="../diagrams/pipeline-macro.puml" alt="High-level architecture of the DFIR dataset factory" width="900" />

The repository is a re-runnable, artifact-producing pipeline:

1. collectors normalize public DFIR sources without discarding source evidence;
2. synthesis plans prompts and generates grounded candidate instruction pairs;
3. quality filtering validates candidates and selects package-eligible rows;
4. packaging creates deterministic, model-specific views and isolated splits;
5. fine-tuning trains and exports an adapter, then tests its direct behavior;
6. evaluation compares complete compatible base and tuned runs before promotion.

Versioned YAML files under `configs/` own durable policy. Python packages own
mechanics and validation. Modules under `scripts/` are thin command-line
entrypoints. Generated directories under `data/` are versioned run artifacts,
not implementation source.

### Artifact Flow

<puml src="../diagrams/pipeline-artifacts-detail.puml" alt="Detailed flow of primary artifacts between pipeline stages" width="450" />

| Stage | Input → output | Implementation | Policy |
|---|---|---|---|
| Collection | Public sources → `RawDocument` | `collectors/`, `scripts/collect_all.py` | `configs/collection.yaml` |
| Synthesis | `RawDocument` → candidate `InstructionPair` | `synthesizers/`, `scripts/synthesize.py` | `configs/synthesis.yaml`, `configs/source_profiles.yaml`, `configs/task_categories.yaml`, prompt assets |
| Quality filtering | Candidate pair → `QualityDecision` and filtered row | `validation/`, `quality/`, `scripts/quality_filter.py` | `configs/quality.yaml`, `configs/task_categories.yaml` |
| Packaging | Filtered row → model-specific train/validation/test rows | `dataset_packaging/`, `scripts/package_dataset.py` | `configs/packaging*.yaml` |
| Fine-tuning | Packaged rows → adapter/export and direct-gate evidence | `scripts/finetune.py`, `scripts/test_lora.py` | `configs/finetune*.yaml` |
| Evaluation | Benchmark + served target → scorecard and comparison | `evaluation/`, `scripts/run_evaluation.py`, `scripts/compare_evaluations.py` | `configs/evaluation.yaml`, `evaluation/benchmark/` |

### Repository Boundaries

| Path | Responsibility |
|---|---|
| `collectors/` | Source access, parsing, normalization, and `RawDocument` creation |
| `synthesizers/` | Selection, prompt planning/rendering, teacher calls, run state, and candidate validation |
| `validation/` | Pure checks shared by synthesis and quality |
| `quality/` | Row decisions, scoring, deduplication, balance checks, and audits |
| `dataset_packaging/` | Model-specific views, grouped splits, and package manifests |
| `evaluation/` | Target generation, local judging, scorecards, checkpoints, and comparisons |
| `scripts/` | Thin repository-local CLIs and training orchestration |
| `configs/` | Versioned pipeline policy |
| `docs/` | Stable user, developer, reference, and current-state documentation |
| `project_state/` | Product intent, durable decisions, and pending work |
| `data/` | Generated inputs, outputs, manifests, and run evidence |

The [DFIR Artifact Taxonomy](../reference/taxonomy.md) is the stable domain
reference used across the pipeline.

---

## Implementation Guide

The implementation follows the artifact flow. When changing a stage, begin with
its policy and contract, then inspect the implementation, CLI wiring, output
lifecycle, and validation ladder in the linked guide.

### 1. Collectors

Collectors are the first implementation boundary. They fetch or read a public
source and normalize each logical source item into a complete `RawDocument`.

| Concern | Owner |
|---|---|
| Shared collection contract and ID rules | `collectors/schemas.py`, `collectors/base.py` |
| Source-specific parsing | `collectors/<source_key>.py` |
| Source URLs, caches, outputs, and filters | `configs/collection.yaml` |
| Collector registration and CLI orchestration | `scripts/collect_all.py` |
| Downstream source/content-type behavior | `configs/source_profiles.yaml` |

Start with the [Collectors guide](collectors.md). For a new source or parser
change, follow [Adding Or Changing A
Source](collectors.md#adding-or-changing-a-source) and its validation ladder.
Preserve complete evidence, stable `doc_id` values, provenance, and upstream
revision information.

### 2. Synthesis

Synthesis selects raw documents, assigns task categories and difficulty, renders
evidence-grounded prompts, calls the teacher model, and validates canonical
candidate pairs.

| Concern | Owner |
|---|---|
| Prompt plan and assignment | `synthesizers/planner.py`, `synthesizers/sampler.py` |
| Prompt assembly and policy loading | `synthesizers/prompt_builder.py`, `synthesizers/prompt_policy.py` |
| Global, category, source, and content instructions | `synthesizers/prompts/` |
| Prompt evidence reduction | `synthesizers/prompts/compactors/` |
| Teacher clients, generation, resume, and output state | `synthesizers/clients/`, `synthesizers/runner.py`, `synthesizers/run_state.py` |
| Candidate contract and Phase 3 acceptance | `synthesizers/schemas.py`, `synthesizers/validators.py` |

Use the [Synthesis guide](synthesis.md). Begin prompt or compactor work at
[Changing Synthesis](synthesis.md#changing-synthesis), and render prompts before
spending API budget. Synthesis output remains candidate data, not training data.

### 3. Quality Filtering

Quality filtering applies reusable checks, row-level decisions and scores,
deduplication, distribution checks, source balance, taxonomy audits, and review
sampling.

| Concern | Owner |
|---|---|
| Reusable pure checks | `validation/` |
| Quality contracts and decision records | `quality/schemas.py` |
| Row-level policy and severity | `quality/validators.py` |
| Dataset-wide gates | `quality/dataset.py` |
| References and orchestration | `quality/references.py`, `quality/runner.py` |
| Thresholds, weights, balance, and tools | `configs/quality.yaml` |

Use the [Quality Filtering guide](quality-filtering.md). Follow [Changing Quality
Policy](quality-filtering.md#changing-quality-policy) when adding a rule or
altering severity. Only rows marked `filtered` may continue to packaging.

### 4. Packaging

Packaging converts canonical filtered rows into model-specific message views
and creates deterministic train, validation, and test splits grouped by
`source_doc_id`.

| Concern | Owner |
|---|---|
| Package record contract | `dataset_packaging/schemas.py` |
| Response transforms, split logic, output, and manifest | `dataset_packaging/runner.py` |
| Versioned model and response-style policy | `configs/packaging*.yaml` |
| CLI | `scripts/package_dataset.py` |

Use the [Packaging guide](packaging.md). Follow [Changing
Packaging](packaging.md#changing-packaging) for a new response style or model
family. Keep model-native tags out of synthesis and quality artifacts.

### 5. Fine-tuning

Fine-tuning loads a packaged dataset, validates compatibility, runs LoRA SFT,
exports candidate artifacts, and produces the evidence needed for a direct
adapter behavior gate.

| Concern | Owner |
|---|---|
| Training, preflight, checkpoints, export, and manifest | `scripts/finetune.py` |
| Direct-adapter termination and behavior gate | `scripts/test_lora.py` |
| Versioned model, LoRA, trainer, and export settings | `configs/finetune*.yaml` |

Use the [Fine-tuning guide](finetuning.md). Follow [Changing The Training
Recipe](finetuning.md#changing-the-training-recipe) for model, trainer,
tokenizer, LoRA, or export changes. A successful training run is not a promotion
decision; the direct-adapter gate must pass first.

### 6. Evaluation

Evaluation generates target responses for held-out benchmark cases, scores them
with a separately served calibrated judge, checkpoints progress, compares
compatible base and tuned runs, and records promotion evidence.

| Concern | Owner |
|---|---|
| Benchmark cases | `evaluation/benchmark/*.jsonl` |
| Contracts | `evaluation/schemas.py` |
| Target clients and structured output | `evaluation/model_clients.py`, `evaluation/structured_output.py` |
| Judge and scoring | `evaluation/judge.py`, `evaluation/scoring.py` |
| Run/checkpoint orchestration | `evaluation/runner.py`, `scripts/run_evaluation.py` |
| Compatibility and regression comparison | `evaluation/comparison.py`, `scripts/compare_evaluations.py` |
| Benchmark, target, judge, and calibration policy | `configs/evaluation.yaml` |

Use the [Evaluation guide](evaluation.md). Follow [Changing
Evaluation](evaluation.md#changing-evaluation) for benchmark, client, judge,
checkpoint, scoring, or comparison changes. Promotion requires complete,
calibrated, compatible evidence and review of task-level and severe cases.

---

## Shared Contracts And Provenance

<puml src="../diagrams/contracts-macro.puml" alt="Macro view of core data contracts" width="900" />

<puml src="../diagrams/contracts-fields-detail.puml" alt="Detailed provenance fields carried through core records" width="300" />

| Record | Defined in | Stable responsibility |
|---|---|---|
| `RawDocument` | `collectors/schemas.py` | Complete normalized source evidence with stable `doc_id` |
| `PromptRecord` | `synthesizers/schemas.py` | One planned model call tied to a source document |
| `InstructionPair` | `synthesizers/schemas.py` | Strict canonical candidate pair with provenance and grounding |
| `QualityCandidate` / `QualityDecision` | `quality/schemas.py` | Candidate input and its filtered/review/rejected decision |
| Packaged message row | `dataset_packaging/runner.py` | Model-specific chat view plus preserved provenance |
| `BenchmarkCase` / `CaseScore` | `evaluation/schemas.py` | Held-out task contract and local-judge result |

Canonical responses begin with a linked `<reasoning>` block and finish with a
practitioner-ready answer. Model-specific tags such as `<think>` are export
concerns and must never be written back into synthesis or quality artifacts.

Deterministic provenance fields such as source, source document, category,
difficulty, and taxonomy references come from the prompt plan rather than from
teacher-model output. Every downstream transformation must preserve the source
document identity.

### Changing A Contract Or Boundary

When a field or phase boundary changes:

1. find every producer and consumer with `rg`;
2. update the Pydantic or JSONL contract and its validation;
3. decide whether old artifacts are rejected, migrated, or supported;
4. add tests for both the new record and incompatible historical records;
5. update the producing and consuming stage guides;
6. run at least one end-to-end fixture through the affected boundary.

---

## Taxonomy And Configuration

<puml src="../diagrams/policy-macro.puml" alt="Macro view of taxonomy and policy inputs" width="600" />

<puml src="../diagrams/policy-ownership-detail.puml" alt="Detailed ownership of taxonomy and policy configuration" width="950" />

The [DFIR Artifact Taxonomy](../reference/taxonomy.md) defines stable domain
labels. Task and quality configuration select and measure those labels without
duplicating their definitions in stage code.

| Configuration | Owner |
|---|---|
| `configs/collection.yaml` | Source URLs, caches, outputs, and collector filters |
| `configs/source_profiles.yaml` | Source/content types, allowed tasks, pair caps, thin-source rules, and sample targets |
| `configs/synthesis.yaml` | Teacher model, generation controls, retries, prompt-size limits, and circuit breaker |
| `configs/task_categories.yaml` | Task definitions and category/difficulty targets |
| `configs/quality.yaml` | Taxonomy IDs, reasoning bounds, issue policy, scoring, deduplication, balance, and tools |
| `configs/packaging*.yaml` | Split, message, response-style, and model-transform policy |
| `configs/finetune*.yaml` | Model, LoRA, trainer, checkpoint, and export settings |
| `configs/evaluation.yaml` | Benchmark, target generation, judge, and calibration identity |

Prefer configuration for durable policy and Python for mechanics. Do not add a
hard-coded branch before checking whether the owning config can express the
change. When adding a field, update its loader, validation, defaults, examples,
and stage documentation together.

---

## Manifests And Output Boundaries

| Manifest | Writer | Scope |
|---|---|---|
| `collection_manifest.json` | `scripts.collect_all` | Latest collection invocation |
| `generation_manifest.json` | `synthesizers.runner` | Latest completed synthesis invocation in a directory |
| `quality_manifest.json` | `quality.runner` | Current quality input batch |
| `packaging_manifest.json` | `dataset_packaging.runner` | Package inputs, response styles, splits, and overlap check |
| `training_manifest.json` | `scripts.finetune` | Completed training/export invocation |
| `evaluation_manifest.json` | `evaluation.runner` | Evaluation identity, status, progress, and scorecard paths |

Manifests are not interchangeable with directory inventories. Several runners
append rows or replace multiple files independently, and a manifest may describe
only the latest invocation while older rows remain. A zero exit code is also not
a universal acceptance signal. Inspect manifest status, error fields, counts,
audits, and gates documented by the owning stage.

Use a fresh output directory after changing inputs, prompts, policy, schema, or
model settings unless the stage guide explicitly guarantees safe resume.
Preserve manifests, exact configuration, logs, code revision, environment
information, and artifact hashes together.

---

## Cross-Cutting Rules

1. Preserve complete source evidence during collection; compact only prompt views.
2. Carry stable provenance through every downstream record.
3. Treat synthesis output as candidates; package only rows marked `filtered`.
4. Split packages by `source_doc_id` to prevent source leakage.
5. Keep shared pure checks in `validation/`; stage wrappers own severity and policy.
6. Keep benchmark cases separate from collection, synthesis, and training.
7. Label teacher-model changes as separate jobs; do not silently fall back within a canonical run.
8. Preserve local ATT&CK and ATLAS caches that influenced validation decisions.
9. Do not promote a model without an enforcing direct-adapter behavior gate and complete, calibrated, compatible evaluation evidence.

---

## Local Setup

Prerequisites are Python 3.11 or later and Git. Documentation diagrams require
Java and Graphviz. Model-backed synthesis requires a Gemini API key, and local
fine-tuning requires a compatible CUDA environment.

```bash
git clone https://github.com/darkrelicz/dfir-dataset.git
cd dfir-dataset
python -m venv .venv
source .venv/bin/activate
pip install torch==2.10.0+cu130 --index-url https://download.pytorch.org/whl/cu130
pip install -e ".[dev]"
ruff check .
python -m scripts.collect_all --list
```

Use the validation ladder in the affected stage guide. Validate from focused
checks and representative fixtures to a stage smoke run, manifest inspection,
and a downstream fixture. Do not treat a successful CLI exit or lint result as
behavioral proof.

Preview the documentation with:

```bash
cd docs
npm install
npm run serve
```

---

## Documentation And Handover

<puml src="../diagrams/docs-macro.puml" alt="Macro view of documentation delivery" width="900" />

<puml src="../diagrams/docs-build-detail.puml" alt="Detailed documentation build and deployment sequence" width="1000" />

| Information | Owner |
|---|---|
| Stable implementation and maintenance guidance | `docs/developer/` |
| User-facing commands and source summaries | `docs/user/` |
| Stable domain definitions | `docs/reference/` |
| Current results and candidate status | [Current State](../current-state/index.md) |
| Superseded run history | [Revisions](../current-state/revisions.md) |
| Product intent and release criteria | `project_state/PROJECT_BRIEF.md` |
| Durable architecture, data, training, and release decisions | `project_state/DECISIONS.md` |
| Pending and deferred work | `project_state/TODO.md` |
| Run-specific identity, settings, counts, status, and paths | Generated manifests under `data/` |

Record information once in its canonical owner and link to it elsewhere. Do not
leave essential architectural or operational knowledge only in chat, logs, or a
commit message. Preserve exact manifests, configs, code and environment
versions, artifact hashes, unresolved risks, and the next action during a
handover.

Embed each PlantUML diagram in the page whose behavior it explains. Keep macro
views separate from control-flow, contract, or lifecycle detail. Diagram source
lives under `docs/diagrams/`; never edit generated files under `docs/_site/`.

After changing documentation or a diagram:

```bash
cd docs
npm run build
```

Do not commit secrets. Keep `GEMINI_API_KEY`, DGX access, and other credentials
in the environment or an approved secret store.
