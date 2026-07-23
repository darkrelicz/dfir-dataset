<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Pipeline Foundations</h1>

This page owns the architecture and the rules shared by more than one lifecycle
stage. Stage-specific behavior belongs in the linked stage guide.

# Architecture

The repository is a re-runnable dataset factory, not a serving application.
Versioned YAML and Markdown own durable policy; Python packages implement
mechanics and validation.

## Macro View

<puml src="../diagrams/pipeline-macro.puml" alt="Macro view of the dataset factory lifecycle" width="350" />

## Artifact Flow Detail

<puml src="../diagrams/pipeline-artifacts-detail.puml" alt="Detailed flow of primary artifacts between pipeline stages" width="450" />

| Path | Responsibility |
|---|---|
| `collectors/` | Source parsing and `RawDocument` collection |
| `synthesizers/` | Selection, prompt rendering, generation, run state, and candidate validation |
| `validation/` | Pure checks shared by synthesis and quality |
| `quality/` | Row decisions, scoring, deduplication, balance checks, and audits |
| `dataset_packaging/` | Model-specific views, grouped splits, and package manifests |
| `evaluation/` | Target generation, local judging, scorecards, and comparisons |
| `scripts/` | Thin repository-local module CLIs |
| `configs/` | Versioned pipeline policy |
| `project_state/` | Product intent, durable decisions, and pending work |

| Stage | Consumes | Produces |
|---|---|---|
| Collection | Public sources and collection policy | Raw JSONL and collection manifest |
| Synthesis | Raw documents, task policy, profiles, and prompts | Prompt records, candidate pairs, rejections, and generation manifest |
| Quality filtering | Candidates, raw evidence, references, and quality policy | Filtered, review, and rejected rows plus audits |
| Packaging | Filtered rows and export policy | Train, validation, and test views plus package manifest |
| Fine-tuning | Packaged data and a versioned training recipe | Adapter, checkpoints, GGUF, logs, and training manifest |
| Evaluation | Held-out cases or saved predictions | Predictions, verdicts, scorecards, and comparison report |

# Taxonomy And Policy

## Macro View

<puml src="../diagrams/policy-macro.puml" alt="Macro view of taxonomy and policy inputs" width="600" />

## Ownership Detail

<puml src="../diagrams/policy-ownership-detail.puml" alt="Detailed ownership of taxonomy and policy configuration" width="950" />

The [DFIR Artifact Taxonomy](../reference/taxonomy.md) defines stable domain
labels. Task and quality configuration select and measure those labels without
duplicating their definitions in stage code.

# Shared Data Flow

## Macro View

<puml src="../diagrams/contracts-macro.puml" alt="Macro view of core data contracts" width="900" />

## Provenance Detail

<puml src="../diagrams/contracts-fields-detail.puml" alt="Detailed provenance fields carried through core records" width="300" />

The important record boundaries are:

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

# Manifest Boundaries

| Manifest | Writer | Scope |
|---|---|---|
| `collection_manifest.json` | `scripts.collect_all` | Latest collection invocation |
| `generation_manifest.json` | `synthesizers.runner` | Latest completed synthesis invocation in a directory |
| `quality_manifest.json` | `quality.runner` | Current quality input batch |
| `packaging_manifest.json` | `dataset_packaging.runner` | Package inputs, response styles, splits, and overlap check |
| `training_manifest.json` | `scripts.finetune` | Completed training/export invocation |
| `evaluation_manifest.json` | `evaluation.runner` | Evaluation identity, status, progress, and scorecard paths |

Manifests are not interchangeable with directory inventories. Several runners
append rows or replace multiple files independently, and a manifest can describe
only the latest invocation while older rows remain. A zero exit code is also not
a universal acceptance signal. Read the stage guide and inspect manifest status,
error fields, counts, audits, and gates.

# Configuration Ownership

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

Prefer configuration for durable policy and Python for mechanics. The stage
guides identify known exceptions and untyped configuration hazards. Do not add
a hard-coded branch before checking whether the owning config can express the
change.

# Cross-Cutting Constraints

- Shared checks belong in `validation/`; stage wrappers decide severity and
  policy.
- Raw documents remain complete. Prompt compaction is a derived view.
- Candidate generation is not a quality decision.
- Review and rejected rows are never package inputs.
- Package splits are grouped by `source_doc_id`.
- Benchmark cases remain separate from collection, synthesis, and training.
- Teacher-model changes use separately labelled jobs; do not silently fall back
  within the canonical run.
- Local ATT&CK and ATLAS caches influence validation decisions and must be
  retained with reproducible runs.
- Evaluation compatibility does not fingerprint every serving parameter.
  Preserve full target and judge configuration plus server identity separately.

# Change Discipline

For any stage change:

1. Read its guide and identify the code, configuration, contract, and output
   lifecycle involved.
2. Make the smallest policy or implementation change.
3. Start with deterministic unit or schema checks.
4. Validate existing artifacts before generating new ones.
5. Use a dry run, then a representative smoke run, then a reviewed pilot before
   an expensive full run.
6. Inspect rejected rows, warnings, distributions, and manifests—not only exit
   status.
7. Use a fresh output directory when the stage guide does not explicitly
   guarantee safe reuse.
8. Update stable documentation and durable project state only when their owned
   facts changed.

## Changing A Contract Or Boundary

When a field or phase boundary changes:

1. Find every producer and consumer with `rg`.
2. Update the Pydantic or JSONL contract and its validation.
3. Decide whether old artifacts are rejected, migrated, or supported.
4. Add tests for both the new record and incompatible historical records.
5. Update the producing and consuming stage guides.
6. Rebuild the documentation and run at least one end-to-end fixture through
   the affected boundary.

# Project Memory And Handover

The project must not rely on chat history. Use:

| File | Content |
|---|---|
| `project_state/PROJECT_BRIEF.md` | Product intent, current state, release gate, and success criteria |
| `project_state/DECISIONS.md` | Durable choices and accepted constraints |
| `project_state/TODO.md` | Pending and deferred work |
| `project_state/DESIGN_SYSTEM.md` | Documentation and CLI presentation rules |
| [Current State](../current-state/index.md) | Current run and candidate facts |
| [Revisions](../current-state/revisions.md) | Superseded run history |

A handover packet should identify the exact raw, synthesis, quality, package,
training, and evaluation manifests; the configs used; code and environment
versions; artifact hashes; unresolved risks; and the next action. It must also
state these invariants:

- `accepted.jsonl` is candidate data; `filtered.jsonl` is the first
  package-eligible data.
- canonical responses use `<reasoning>`; model-specific conversion happens at
  packaging.
- package splits must remain source-document isolated.
- a completed training loop is not a release decision.
- direct-adapter termination and behavior checks must enforce failure.
- only complete, calibrated, compatible scorecards can support promotion.

Do not commit secrets. Keep `GEMINI_API_KEY`, DGX access, and other credentials
in the environment or an approved secret store.

# Documentation And Diagram Maintenance

## Macro View

<puml src="../diagrams/docs-macro.puml" alt="Macro view of documentation delivery" width="900" />

## Build Detail

<puml src="../diagrams/docs-build-detail.puml" alt="Detailed documentation build and deployment sequence" width="1000" />

Embed each PlantUML diagram in the page whose behavior it explains. Begin with a
small macro view, then use separate detail diagrams for control flow, contracts,
or lifecycle boundaries. Do not mix all of those concerns in one canvas.
Diagram source lives under `docs/diagrams/`; Java is required for rendering and
non-sequence diagrams also require Graphviz.

After changing a command, contract, configuration field, stage boundary, or
diagram:

```bash
cd docs
npm run build
```

Never edit generated files under `docs/_site/`.
