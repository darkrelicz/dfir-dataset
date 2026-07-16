<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Project State Memory

The project must not rely on chat history as durable memory. Current state,
decisions, and TODOs belong in repository documents.

## Canonical State Files

| File | Role |
|---|---|
| `project_state/PROJECT_BRIEF.md` | Product intent, phase status, current run state, and success criteria. |
| `project_state/ARCHITECTURE.md` | Current codebase structure and implementation architecture. |
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

## Operating Guides

These files are reusable guides or templates rather than the canonical phase
status pages. Some are filled with a current run snapshot when the guide itself
requires it:

* `project_state/HANDOVER.md`
* `project_state/ADDING_SOURCES.md`
* `project_state/COVERAGE_MAP.md`
* `project_state/DATASET_CARD.md`
* `project_state/PROMPT_GUIDE.md`
* `project_state/QUALITY_RUBRIC.md`
* `project_state/TRAINING_RECIPE.md`

Update them when the process changes. Do not use them for run-specific counts.

## This MarkBind Site

`docs/` is the GitHub Pages source for successor-friendly documentation.

It should:

* summarize current implementation from code and durable state docs;
* link back to canonical files;
* include architecture and UML diagrams as PlantUML source;
* keep suggested improvements separate from current behavior;
* be updated when architecture, commands, contracts, or handoff workflows change.

## Documentation Update Rule

When a change affects project direction, architecture, active work, or durable
decisions:

1. update the code/config;
2. update generated manifests if a pipeline stage was rerun;
3. update the relevant `project_state/` state file;
4. update `docs/` when successor-facing navigation or implementation details
   changed.

## Current Accepted Risk To Preserve

For the shortened deadline, Phase 5 packages both filtered rows and review rows.
Review rows are transformed into direct-answer examples. Rejected rows remain
excluded.

This belongs in state docs and manifests because it changes how future readers
should interpret the packaged dataset.
