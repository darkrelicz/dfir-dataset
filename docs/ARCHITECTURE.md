# Architecture

## Current Project Type

This repository is a Python dataset pipeline, not a website application. No frontend framework, browser routing layer, CSS system, or UI component tree is currently present.

## Runtime And Frameworks

- Language: Python 3.11+
- Packaging: `pyproject.toml` with setuptools
- CLI entrypoint: `dfir-collect = scripts.collect_all:main`
- Core libraries: `pydantic`, `pyyaml`, `jsonlines`, `requests`, `beautifulsoup4`, `gitpython`, `rich`, `tqdm`, `mitreattack-python`
- Tests are configured for `pytest`, but no `tests/` tree is currently present.

## Pipeline Layout

- `collectors/`: Phase 2 source collectors. Each collector normalizes one source into the shared `RawDocument` schema.
- `scripts/collect_all.py`: CLI orchestrator for running one or all collectors and writing `data/raw/collection_manifest.json`.
- `configs/collection.yaml`: Source URLs, clone/cache paths, output directories, and collector-specific options.
- `configs/task_categories.yaml`: Five task categories used by the future instruction-pair synthesizer.
- `configs/synthesis.yaml`: Planned Phase 3 model and generation settings.
- `configs/quality.yaml`: Programmatic taxonomy IDs, coverage levels, scoring weights, and dedup settings.
- `configs/packaging.yaml`: Planned packaging configuration.
- `docs/TAXONOMY.md`: Human-readable 57-category DFIR artifact taxonomy.
- `data/raw/`: Generated collector outputs and cloned upstream repositories. Treat as generated data.

Planned but not yet implemented packages from the project plan: `synthesizers/`, `quality/`, `packaging/`, and `evaluation/`.

## Data Contracts

Collectors emit JSONL records conforming to `collectors.schemas.RawDocument`:

- `doc_id`, `source`, `source_url`, `title`
- `date_collected`, optional `date_published`
- `content_type`, `content_markdown`, `metadata`, `word_count`

Collection runs emit `CollectionManifest` entries containing collector name, version, source URL, collection time, document count, warnings, errors, and duration.

## Current Generated State

The current manifest and direct JSONL counts show all 16 selected Core + Tier 1-2 sources producing raw documents:

- `mitre_attack`: 697
- `sigma_rules`: 3109
- `atomic_red_team`: 1804
- `cisa_advisories`: 3829
- `volatility3_docs`: 194
- `mitre_atlas`: 262
- `cisa_kev`: 268
- `kape_files`: 811
- `hayabusa_rules`: 4836
- `lolbas_gtfobins`: 720
- `forensic_artifacts`: 731
- `velociraptor_artifacts`: 437
- `hijacklibs`: 590
- `loldrivers`: 653
- `ossem_data_dicts`: 699
- `cybersec_skills`: 615

Total raw JSONL rows: 20,255.

## Planned Downstream Architecture

Phase 3 synthesis should read validated `RawDocument` JSONL and write instruction pairs plus generation manifests under `data/synthesized/`. The plan uses Gemini 2.5 Flash as the primary teacher model, Claude Sonnet as a fallback/comparison subset, five task-category prompt templates, and source-type-specific prompt instructions. Canonical synthesized responses use `<reasoning>` blocks with linked evidence, analysis, conclusion, and caveat IDs.

Phase 4 quality assurance should validate structure, ATT&CK/ATLAS IDs, taxonomy refs, tool names, `<reasoning>` link integrity, near-duplicates, source balance, difficulty balance, and the 57-category taxonomy heatmap.

Phase 5 packaging should split by `source_doc_id` to prevent leakage and export local chat-formatted JSONL for training. The canonical export keeps `<reasoning>`; a model-specific GLM export may convert it to `<think>` only if needed. Phase 6 validates LoRA SFT results on DGX Sparks and integrates the best checkpoint into Shepherd.
