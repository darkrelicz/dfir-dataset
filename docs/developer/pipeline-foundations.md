<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Pipeline Foundations</h1>

> This page owns the architecture and rules shared by more than one lifecycle stage.

---

## Architecture

<puml src="../diagrams/pipeline-macro.puml" alt="High-level architecture of the DFIR dataset factory" width="900" />

The repository is a re-runnable dataset pipeline. Versioned YAML files own
durable policy, and Python packages implement mechanics and validation.

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

The [Developer Guide](index.md#core-rules) summarizes the core pipeline
invariants. Additional cross-stage constraints are:

- Shared checks belong in `validation/`; stage wrappers decide severity and
  policy.
- Benchmark cases remain separate from collection, synthesis, and training.
- Teacher-model changes use separately labelled jobs; do not silently fall back
  within the canonical run.
- Local ATT&CK and ATLAS caches influence validation decisions and must be
  retained with reproducible runs.
- Evaluation compatibility does not fingerprint every serving parameter.
  Preserve full target and judge configuration plus server identity separately.

# Changing A Contract Or Boundary

When a field or phase boundary changes:

1. Find every producer and consumer with `rg`.
2. Update the Pydantic or JSONL contract and its validation.
3. Decide whether old artifacts are rejected, migrated, or supported.
4. Add tests for both the new record and incompatible historical records.
5. Update the producing and consuming stage guides.
6. Rebuild the documentation and run at least one end-to-end fixture through
   the affected boundary.

# Reproducible Handover

Use the ownership map in the [Developer Guide](index.md#documentation-ownership)
instead of duplicating live state in a handover. Preserve the exact raw,
synthesis, quality, package, training, and evaluation manifests; configs; code
and environment versions; artifact hashes; unresolved risks; and next action.

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
