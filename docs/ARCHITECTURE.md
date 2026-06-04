# Architecture & Design Decisions

This document tracks major design decisions for the DFIR dataset pipeline.

### Phase 1: Taxonomy Definition

- **Raw JSONL Base Schema**: Uses `pydantic` schemas for standardizing ingested DFIR formats into a unified `RawDocument`.

### Phase 2: Source Collection Architecture Decisions
- **`yaml.safe_load` over `pySigma`**: We use raw YAML parsing instead of pySigma because it reduces dependency weight and we only need to extract metadata, not translate rules.
- **Atomic Red Team Granularity**: We emit one document per *atomic test*, not per technique file. This finer granularity helps with downstream QA synthesis.
- **RSS + HTML Scrape for CISA Advisories**: CISA does not provide an official API for full advisories, and RSS only contains summaries. We scrape the HTML via `BeautifulSoup` to access the full advisory contents, IOCs, and mitigations.
- **Git Caching Strategy**: SigmaHQ and Atomic Red Team are cloned locally via shallow clones to `data/raw/.repos/` for reproducibility and faster re-runs.

### Why YAML for the Taxonomy?

The master plan initially implied a markdown document for the taxonomy. We chose a **structured YAML file** (`taxonomy/dfir_taxonomy.yaml`) instead because:

1. **Machine-Readable**: It can be programmatically consumed by the Phase 3 synthesis pipeline (to select prompt templates by category ID), the Phase 4 quality scorer (to validate category labels), and the Phase 4 distribution auditor (to check against target percentages).
2. **Diffable**: YAML is easier to track in version control than arbitrary text or tables.
3. **Extensible**: The successor can easily add new categories or tasks by adding blocks to the YAML structure.

### Why Pydantic for Validation?

We use Pydantic (`taxonomy/validate_taxonomy.py`) to validate the taxonomy YAML because:
- It provides strict type safety (e.g., ensuring difficulty is one of `junior`, `mid`, `senior`).
- It gives clear, actionable error messages if someone breaks the schema.
- It allows for custom validators (like checking MITRE ATT&CK ID formats via regex).

### Directory Layout

The directory structure follows a pipeline pattern (`collectors/` -> `synthesizers/` -> `quality/` -> `packaging/`). 
We added a `taxonomy/` root directory specifically for Phase 1 artifacts to keep them separate from the pipeline code and configuration files. This makes it clear that the taxonomy is a core guiding document, not just another config.
