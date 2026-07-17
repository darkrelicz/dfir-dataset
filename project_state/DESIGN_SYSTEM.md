# Design System

## Current Presentation Surfaces

The project currently presents information through:

- Canonical stable documentation in `docs/` and the repository overview in `README.md`.
- CLI output from the thin entrypoints under `scripts/`.
- Generated JSONL and JSON manifests under `data/raw/`, `data/synthesized/`, `data/quality/`, `data/packaged/`, `data/evaluation/`, and `data/finetune/`.

## Documentation Style

- Keep operational state concise and keep stable explanatory guidance in `docs/`.
- Prefer short sections with stable headings.
- Avoid large code dumps.
- Use exact file and config names when documenting architecture or tasks.
- Separate human references from machine-readable configuration.

## CLI Style

- Keep command output readable and summary-first.
- `rich` tables are acceptable for collection summaries.
- Errors and warnings should identify the source collector and next debugging target.
- Long-running stages should log stable progress identifiers such as source, prompt ID, case ID, and completed/total counts.
- Partial artifacts must be visibly distinguishable from complete artifacts; Evaluation stage uses `in_progress` and `complete` status fields.
