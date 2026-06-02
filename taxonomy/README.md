# Taxonomy

This directory contains the source of truth for the DFIR task taxonomy, which defines what the Shepherd model will be trained to do.

## Key Files

- `dfir_taxonomy.yaml` — The core structured document defining categories, difficulty distributions, and example tasks.
- `validate_taxonomy.py` — Schema validation script using Pydantic.
- `gap_analysis.py` — Identifies coverage gaps against the MITRE ATT&CK tactics list.
- `review_checklist.md` — Checklist for human review of the taxonomy.

## Downstream Usage

This taxonomy is consumed programmatically by:
1. **Phase 3 (Synthesis)**: Uses category IDs to select prompt templates.
2. **Phase 4 (Quality Scorer)**: Validates category and difficulty labels.
3. **Phase 4 (Distribution Auditor)**: Checks dataset distribution against targets defined in the YAML.

## Extending the Taxonomy

To add new capabilities:
1. Add a new category to the `categories` list in `dfir_taxonomy.yaml`.
2. Provide at least 10 example tasks spanning junior/mid/senior difficulties.
3. Adjust the `category_distribution` percentages so they sum to 1.0.
4. Run `python validate_taxonomy.py` to ensure schema compliance.
