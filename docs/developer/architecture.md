<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Architecture</h1>

This page defines system boundaries and the relationships between pipeline
components. Phase behavior, commands, and operating caveats belong in the linked
subsystem guides.

# Runtime

| Area | Current implementation |
|---|---|
| Language | Python 3.11+ |
| Packaging | `pyproject.toml` with setuptools |
| Interfaces | Repository-local Python module CLIs |
| Core libraries | Pydantic, PyYAML, JSON Lines, Google GenAI, Requests, GitPython, Rich, tqdm, Unsloth, Transformers, and TRL |

# Component View

<puml src="../diagrams/pipeline-component.puml" alt="Component diagram for the dataset factory" width="1000" />

| Path | Responsibility |
|---|---|
| `collectors/` | Source-specific parsing and `RawDocument` collection. |
| `synthesizers/` | Planning, prompt rendering, generation, run state, and candidate validation. |
| `synthesizers/prompts/` | Base, category, source-type, content-type, and compactor assets. |
| `validation/` | Pure checks shared across synthesis and quality. |
| `quality/` | Row decisions, scoring, references, dataset gates, and output writing. |
| `dataset_packaging/` | Model-specific views, grouped splits, and package manifests. |
| `evaluation/` | Target generation, judging, scorecards, and comparison gates. |
| `scripts/` | Thin Python module CLIs for package runners. |
| `utils/` | IO, text, Markdown, and Git helpers. |
| `configs/` | Versioned pipeline policy. |
| `project_state/` | Product intent, decisions, and active work. |
| `docs/` | Stable user, developer, and reference guidance. |

# Pipeline Boundaries

<puml src="../diagrams/end-to-end-sequence.puml" alt="End-to-end sequence diagram" width="1000" />

| Phase | Consumes | Produces | Detailed design |
|---|---|---|---|
| Taxonomy and task design | Project intent and DFIR domain definitions | Taxonomy, task policy, and coverage targets | [Taxonomy](../reference/taxonomy.md) · [Coverage Map](coverage-map.md) |
| Collection | Public upstream sources and collection config | Raw source JSONL and collection manifest | [Collectors](collectors.md) |
| Synthesis | Raw documents, profiles, task policy, and prompts | Prompt records, candidates, rejections, and generation manifest | [Synthesis](synthesis.md) |
| Quality | Candidates, raw evidence, local references, and quality policy | Filtered, review, and rejected rows plus audits and manifest | [Validation and Quality](validation-quality.md) |
| Packaging | Filtered rows and model-specific packaging policy | Train, validation, and test views plus package manifest | [Packaging](packaging.md) |
| Evaluation and training | Held-out benchmarks or packaged data | Scorecards, comparisons, adapters, and export artifacts | [Training and Release](training-and-release.md) |

Pydantic and JSONL contracts connect the phases. See [Data
Contracts](data-contracts.md) for fields and manifest scope.

# Cross-Cutting Constraints

- A directory can contain artifacts from more than one invocation; the latest
  manifest describes only its documented scope.
- Several phases write incrementally or replace multiple files independently.
  A completed file set is not automatically a transactionally consistent run.
- Exit code zero is not a universal acceptance signal. Manifests and comparison
  reports contain gates that automation must inspect explicitly.
- Local reference caches affect ATT&CK and ATLAS validation and must be retained
  with logs when reproducible decisions matter.
- Evaluation compatibility does not capture every target-serving parameter.
  Freeze and record effective model settings outside the scorecard when making
  comparison claims.

The precise lifecycle and recovery behavior is documented in [Collectors](collectors.md),
[Synthesis](synthesis.md), [Validation and Quality](validation-quality.md),
[Packaging](packaging.md), and [Training and Release](training-and-release.md).

# Architectural Decisions

- Raw documents remain complete. Prompt-cost reduction occurs only during
  synthesis.
- Configuration owns durable policy; Python modules own mechanics and
  validation.
- Canonical responses use `<reasoning>`, not model-specific training tags.
- Model-specific exports may transform response tags and provenance markers
  without mutating canonical synthesis or quality records.
- Shared validation primitives remain separate from phase-specific severity and
  policy.
- Candidate generation is not a quality decision; only filtered rows are
  eligible for packaging.
- Packaged splits are grouped by `source_doc_id` to prevent source leakage.
- Benchmark cases remain held out from synthesis and training.
- Model promotion requires bounded termination checks and complete compatible,
  calibrated evaluation evidence.
- Teacher-model changes run as separately labelled jobs rather than silently
  falling back within a canonical run.

Durable rationale and superseded choices are recorded in
`project_state/DECISIONS.md`. Current package, training, and evaluation results
belong in [Current State](../current-state/index.md), not in this architecture
description.
