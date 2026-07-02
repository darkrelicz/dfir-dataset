# Design System

## Current Presentation Surfaces

The project currently presents information through:

- Markdown documentation in `docs/` and `README.md`.
- CLI output from `scripts/collect_all.py`.
- Generated JSONL and JSON manifest files under `data/raw/`, `data/synthesized/`, and `data/quality/`.

## Documentation Style

- Keep durable docs concise and operational.
- Prefer short sections with stable headings.
- Avoid large code dumps.
- Use exact file and config names when documenting architecture or tasks.
- Separate human references from machine-readable configuration.

## CLI Style

- Keep command output readable and summary-first.
- `rich` tables are acceptable for collection summaries.
- Errors and warnings should identify the source collector and next debugging target.
