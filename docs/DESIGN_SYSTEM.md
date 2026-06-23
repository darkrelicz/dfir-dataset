# Design System

## Current UI State

No website or application UI exists in this repository. There are no routes, pages, CSS files, React/Vue/Svelte components, design tokens, or static assets for a frontend.

## Current Presentation Surfaces

The project currently presents information through:

- Markdown documentation in `docs/` and `README.md`.
- CLI output from `scripts/collect_all.py`.
- Generated JSONL and JSON manifest files under `data/raw/`.

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

## Future Website Guidance

If a website or dashboard is added later, update this file with the actual framework, routing model, styling approach, component conventions, and accessibility expectations before building major UI features.
