<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Shepherd DFIR Dataset Guides

This MarkBind site is the successor-facing guide for the Shepherd DFIR dataset
factory. It documents the current implementation first, then separates future
improvement ideas into their own section.

The source of truth for project state remains the durable memory documents under
`../project_state/`, especially:

* `../project_state/PROJECT_BRIEF.md`
* `../project_state/ARCHITECTURE.md`
* `../project_state/DECISIONS.md`
* `../project_state/TODO.md`

These guides make that state easier to navigate, but they should not replace
the generated manifests under `../data/`.

## Current Production Path

As of 2026-07-07, the active handoff path is:

1. Raw source collection under `../data/raw/`.
2. Reduced-subset Gemini synthesis under `../data/synthesized/gemini_subset_1/`.
3. Phase 4 quality filtering under `../data/quality/gemini_subset_1/`.
4. Phase 5 local packaging under `../data/packaged/gemini_subset_1/`.
5. Phase 6 baseline evaluation and LoRA SFT are the next project tasks.

The current packaged training inputs are:

* `../data/packaged/gemini_subset_1/train.jsonl`
* `../data/packaged/gemini_subset_1/validation.jsonl`
* `../data/packaged/gemini_subset_1/test.jsonl`

## Guide Map

### User Guides

* [Quick Start](user/quickstart.md)
* [Current Project State](user/current-state.md)
* [Running The Pipeline](user/running-the-pipeline.md)
* [Source Guide](user/source-guide.md)
* [Quality And Packaging](user/quality-and-packaging.md)

### Developer Guides

* [Architecture](developer/architecture.md)
* [Data Contracts](developer/data-contracts.md)
* [Collectors](developer/collectors.md)
* [Synthesis](developer/synthesis.md)
* [Validation And Quality](developer/validation-quality.md)
* [Packaging](developer/packaging.md)
* [Configuration](developer/configuration.md)
* [Extension Points](developer/extension-points.md)
* [Diagrams](developer/diagrams.md)
* [Project State Memory](developer/project-state-memory.md)
* [Suggested Improvements](developer/suggested-improvements.md)

## Architecture At A Glance

<puml src="diagrams/pipeline-component.puml" alt="Component diagram for the Shepherd DFIR dataset factory" width="1000" />

## End-To-End Flow

<puml src="diagrams/end-to-end-sequence.puml" alt="Sequence diagram for collection, synthesis, quality, and packaging" width="1000" />
