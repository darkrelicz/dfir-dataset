# Architecture & Design Decisions

This document tracks major design decisions for the DFIR dataset pipeline.

### Phase 1: Taxonomy Definition

- **Raw JSONL Base Schema**: Uses `pydantic` schemas for standardizing ingested DFIR formats into a unified `RawDocument`.

### Phase 2: Source Collection Architecture Decisions
- **`yaml.safe_load` over `pySigma`**: We use raw YAML parsing instead of pySigma because it reduces dependency weight and we only need to extract metadata, not translate rules.
- **Atomic Red Team Granularity**: We emit one document per *atomic test*, not per technique file. This finer granularity helps with downstream QA synthesis.
- **RSS + HTML Scrape for CISA Advisories**: CISA does not provide an official API for full advisories, and RSS only contains summaries. We scrape the HTML via `BeautifulSoup` to access the full advisory contents, IOCs, and mitigations.
- **Git Caching Strategy**: SigmaHQ and Atomic Red Team are cloned locally via shallow clones to `data/raw/.repos/` for reproducibility and faster re-runs.

### Taxonomy Design

We moved away from a single monolithic file and separated concerns:
- **`docs/TAXONOMY.md`**: A comprehensive human reference for the artifact categories.
- **`configs/quality.yaml`**: Contains valid domain IDs and coverage mappings for programmatic validation in Phase 4.
- **`configs/task_categories.yaml`**: Defines the 5 core tasks for the Phase 3 synthesizer to select prompt templates.

This separation ensures machine-readable components are strictly config-oriented, while deep contextual documentation lives in markdown.

### Directory Layout

The directory structure follows a pipeline pattern (`collectors/` -> `synthesizers/` -> `quality/` -> `packaging/`). 
Documentation including the taxonomy reference lives in `docs/`, and pipeline configuration including task categories lives in `configs/`.
