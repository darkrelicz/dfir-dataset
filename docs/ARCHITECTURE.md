# Architecture

## Current Project Type

This repository is a Python dataset pipeline, not a website application. No frontend framework, browser routing layer, CSS system, or UI component tree is currently present.

## Runtime And Frameworks

- Language: Python 3.11+
- Packaging: `pyproject.toml` with setuptools
- CLI entrypoint: `dfir-collect = scripts.collect_all:main`
- Core libraries: `pydantic`, `pyyaml`, `jsonlines`, `google-genai`, `requests`, `gitpython`, `rich`, `tqdm`, `mitreattack-python`
- Tests are configured for `pytest`, but no `tests/` tree is currently present.

## Pipeline Layout

- `collectors/`: Phase 2 source collectors. Each collector normalizes one source into the shared `RawDocument` schema.
- `scripts/collect_all.py`: CLI orchestrator for running one or all collectors and writing `data/raw/collection_manifest.json`.
- `configs/collection.yaml`: Source URLs, clone/cache paths, output directories, and collector-specific options.
- `configs/task_categories.yaml`: Five task categories used by the future instruction-pair synthesizer.
- `configs/synthesis.yaml`: Planned Phase 3 model and generation settings.
- `configs/source_profiles.yaml`: Phase 3 source profiles, content-type overrides, pair caps, and pilot sampling targets.
- `configs/quality.yaml`: Programmatic taxonomy IDs, coverage levels, scoring weights, and dedup settings.
- `configs/packaging.yaml`: Planned packaging configuration.
- `synthesizers/`: Phase 3 scaffolding for source profiles, content-type profiles, prompt rendering, pilot sampling, schemas, and validation helpers.
- `scripts/synthesize.py`: CLI for raw corpus validation and no-API prompt rendering.
- `docs/TAXONOMY.md`: Human-readable 57-category DFIR artifact taxonomy.
- `data/raw/`: Generated collector outputs and cloned upstream repositories. Treat as generated data.

Planned but not yet implemented packages from the project plan: `quality/`, `packaging/`, and `evaluation/`. The `synthesizers/` package currently covers offline scaffolding only; it does not yet call Gemini or Claude.

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
- `cisa_advisories`: 3831
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
- `cybersec_skills`: 670

Total raw JSONL rows: 20,312. Raw corpus validation currently passes.

## Planned Downstream Architecture

Phase 3 synthesis should read validated `RawDocument` JSONL and write instruction pairs plus generation manifests under `data/synthesized/`. The plan uses the direct Gemini API through the Google GenAI SDK, with Gemini 2.5 Flash as the primary teacher model, five task-category prompt templates, source-type-specific prompt instructions, and selective content-type prompt overrides. Any Claude or alternate-model comparison must run as a separate, explicitly labeled job rather than an automatic fallback. Canonical synthesized responses use `<reasoning>` blocks with linked evidence, analysis, conclusion, and caveat IDs.

Current Phase 3 scaffold includes deterministic source profiles, content-type profiles, source-type prompt templates, content-type prompt overrides, task-category prompt templates, raw corpus validation, pilot sampling, prompt-size trimming via `max_source_chars`, generated-pair rejection gates, and dry-run prompt rendering. Source profile policy is data-driven in `configs/source_profiles.yaml`, while `synthesizers/source_profiles.py` loads and validates that config. Model clients, retry/rate-limit handling, and batch manifests for real generation are still pending.

Prompt construction uses two layers: coarse `source_type` guidance derived from the collector `source`, then optional exact `content_type` guidance derived from each raw document. This keeps broad behavior stable while adding specialized handling for labels such as `atomic_test`, `lolbas_windows_lolbin`, `gtfobins_linux_abuse_function`, `hayabusa_rule`, `event_dictionary`, `tool_module`, `tool_plugin`, and Velociraptor artifact variants.

The generated-pair rejection gates catch invalid JSON, schema failures, wrong or missing `source_doc_id`, source/category/difficulty mismatches, too many or too few pairs, invalid taxonomy refs, invalid ATT&CK/ATLAS ID formats, broken `<reasoning>` links, empty evidence/analysis lines, missing final answers, and concrete indicators not present in the source document.

Phase 4 quality assurance should validate structure, ATT&CK/ATLAS IDs, taxonomy refs, tool names, `<reasoning>` link integrity, near-duplicates, source balance, difficulty balance, and the 57-category taxonomy heatmap.

Phase 5 packaging should split by `source_doc_id` to prevent leakage and export local chat-formatted JSONL for training. The canonical export keeps `<reasoning>`; a model-specific GLM export may convert it to `<think>` only if needed. Phase 6 validates LoRA SFT results on DGX Sparks and integrates the best checkpoint into Shepherd.
