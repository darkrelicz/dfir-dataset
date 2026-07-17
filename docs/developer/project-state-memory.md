<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Project State Memory</h1>

The project must not rely on chat history as durable memory. Current state,
decisions, and TODOs belong in repository documents.

# Operational State Files

| File | Role |
|---|---|
| `project_state/PROJECT_BRIEF.md` | Product intent, phase status, current run state, and success criteria. |
| `project_state/DECISIONS.md` | Durable decisions and accepted risks. |
| `project_state/TODO.md` | Active and deferred work. |
| `project_state/DESIGN_SYSTEM.md` | Documentation and CLI presentation rules. |

Generated manifests are canonical for run-specific counts:

* `data/raw/collection_manifest.json`
* `data/synthesized/<run>/generation_manifest.json`
* `data/quality/<run>/quality_manifest.json`
* `data/packaged/<run>/packaging_manifest.json`
* `data/evaluation/<run>/evaluation_manifest.json`
* `data/evaluation/<run>/scorecards/llm_judge/scores.json`
* `data/finetune/<run>/training_manifest.json`

# Canonical Stable Documentation

The Markdown source under `docs/` is the single source for stable architecture,
operating guides, handover material, taxonomy references, and reusable
templates. Important migrated pages include:

* [Architecture](architecture.md)
* [Adding Sources](adding-sources.md)
* [Prompt Guide](prompt-guide.md)
* [Quality Rubric](quality-rubric.md)
* [Coverage Map](coverage-map.md)
* [Benchmark Design](benchmark-design.md)
* [Training And Release](../user/training-and-release.md)
* [Handover Guide](../user/handover.md)
* [DFIR Artifact Taxonomy](../reference/taxonomy.md)

The rendered MarkBind site is the GitHub Pages presentation of these source
files. Do not edit generated files under `docs/_site/`.

The documentation should:

* describe the current implementation from code, operational state, and
  generated manifests;
* link to operational state or manifests where live status belongs;
* include architecture and UML diagrams as PlantUML source;
* keep suggested improvements separate from current behavior;
* be updated when architecture, commands, contracts, or handoff workflows change.

# Documentation Update Rule

When a change affects project direction, architecture, active work, or durable
decisions:

1. update the code/config;
2. update generated manifests if a pipeline stage was rerun;
3. update `project_state/` when product intent, decisions, active work, or
   presentation rules changed;
4. update the canonical `docs/` page when stable architecture, commands,
   contracts, workflows, or successor guidance changed.

# Current Packaging Policy

Phase 5 packages only filtered rows. Review and rejected rows remain excluded.
The active GLM v3 view derives a deterministic 75% reasoning / 25% direct mix
from filtered rows without mutating Phase 4 outputs.
