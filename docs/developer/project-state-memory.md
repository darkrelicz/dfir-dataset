# Project State Memory

The project must not rely on chat history as durable memory. Current state,
decisions, and TODOs belong in repository documents.

## Canonical State Files

| File | Role |
|---|---|
| `docs/PROJECT_BRIEF.md` | Product intent, phase status, current run state, and success criteria. |
| `docs/ARCHITECTURE.md` | Current codebase structure and implementation architecture. |
| `docs/DECISIONS.md` | Durable decisions and accepted risks. |
| `docs/TODO.md` | Active and deferred work. |
| `docs/DESIGN_SYSTEM.md` | Documentation and CLI presentation rules. |

Generated manifests are canonical for run-specific counts:

* `data/raw/collection_manifest.json`
* `data/synthesized/<run>/generation_manifest.json`
* `data/quality/<run>/quality_manifest.json`
* `data/packaged/<run>/packaging_manifest.json`

## Operating Guides

These files are reusable guides or templates, not live status pages:

* `docs/HANDOVER.md`
* `docs/ADDING_SOURCES.md`
* `docs/COVERAGE_MAP.md`
* `docs/DATASET_CARD.md`
* `docs/PROMPT_GUIDE.md`
* `docs/QUALITY_RUBRIC.md`
* `docs/TRAINING_RECIPE.md`

Update them when the process changes. Do not use them for run-specific counts.

## This MarkBind Site

`guides/` is the GitHub Pages source for successor-friendly documentation.

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
3. update the relevant `docs/` state file;
4. update `guides/` when successor-facing navigation or implementation details
   changed.

## Current Accepted Risk To Preserve

For the shortened deadline, Phase 5 packages both filtered rows and review rows.
Review rows are transformed into direct-answer examples. Rejected rows remain
excluded.

This belongs in state docs and manifests because it changes how future readers
should interpret the packaged dataset.
