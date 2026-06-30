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
- `utils/`: Shared low-level helpers for YAML/JSON/JSONL IO, text cleanup, list normalization, slug/filename generation, stable hashing, ordered threshold checks, Markdown frontmatter parsing, and GitHub source URL/commit helpers.
- `configs/collection.yaml`: Source URLs, clone/cache paths, output directories, and collector-specific options.
- `configs/task_categories.yaml`: Five task categories used by the future instruction-pair synthesizer.
- `configs/synthesis.yaml`: Phase 3 model settings, pair targets, Gemini thinking budget, API retry/backoff, validation retry, and prompt-size controls.
- `configs/source_profiles.yaml`: Phase 3 source profiles, content-type overrides, pair caps, and pilot sampling targets.
- `configs/quality.yaml`: Programmatic taxonomy IDs, coverage levels, scoring weights, and dedup settings.
- `configs/packaging.yaml`: Planned packaging configuration.
- `synthesizers/`: Phase 3 scaffolding for source profiles, content-type profiles, prompt policy validation, prompt planning, prompt rendering, prompt-time source compaction, pilot sampling, model clients, schemas, run-state helpers, generation execution, and validation helpers.
- `scripts/synthesize.py`: Thin CLI for raw corpus validation, no-API prompt rendering, and Gemini-backed instruction-pair generation.
- `docs/TAXONOMY.md`: Human-readable 57-category DFIR artifact taxonomy.
- `data/raw/`: Generated collector outputs and cloned upstream repositories. Treat as generated data.

Planned but not yet implemented packages from the project plan: `quality/`, `packaging/`, and `evaluation/`. The `synthesizers/` package includes the direct Gemini client and generation runner; Claude comparison jobs are not implemented.

## Data Contracts

Collectors emit JSONL records conforming to `collectors.schemas.RawDocument`:

- `doc_id`, `source`, `source_url`, `title`
- `date_collected`, optional `date_published`
- `content_type`, `content_markdown`, `metadata`, `word_count`

Collection runs emit `CollectionManifest` entries containing collector name, version, source URL, collection time, document count, warnings, errors, and duration.

## Current Generated State

The current manifest and direct JSONL counts show all 16 selected Core + Tier 1-2 sources producing raw documents:

- `mitre_attack`: 697
- `sigma_rules`: 3111
- `atomic_red_team`: 1811
- `cisa_advisories`: 3849
- `volatility3_docs`: 194
- `mitre_atlas`: 262
- `cisa_kev`: 270
- `kape_files`: 811
- `hayabusa_rules`: 4839
- `lolbas_gtfobins`: 720
- `forensic_artifacts`: 731
- `velociraptor_artifacts`: 437
- `hijacklibs`: 590
- `loldrivers`: 656
- `ossem_data_dicts`: 699
- `cybersec_skills`: 670

Total raw JSONL rows: 20,347. Raw corpus validation currently passes with 16 files, 20,347 documents, 20,347 unique document IDs, and zero issues.

## Planned Downstream Architecture

Phase 3 synthesis should read validated `RawDocument` JSONL and write instruction pairs plus generation manifests under `data/synthesized/`. The plan uses the direct Gemini API through the Google GenAI SDK, with Gemini 2.5 Flash as the primary teacher model, five task-category prompt templates, source-type-specific prompt instructions, and selective content-type prompt overrides. Any Claude or alternate-model comparison must run as a separate, explicitly labeled job rather than an automatic fallback. Canonical synthesized responses use `<reasoning>` blocks with linked evidence, analysis, conclusion, and caveat IDs.

Current Phase 3 scaffold includes:

- Deterministic source profiles, content-type profiles, source-type prompt templates, content-type prompt overrides, task-category prompt templates, deterministic taxonomy-ref suggestions, raw corpus validation, stratified pilot sampling across source/content richness, prompt-time source compaction, prompt-size trimming via `max_source_chars`, generated-pair rejection gates, dry-run prompt rendering, and a sequential Gemini generation runner.
- Source profile policy is data-driven in `configs/source_profiles.yaml`, while `synthesizers/source_profiles.py` loads and validates that config.
- Prompt/category/difficulty policy and prompt-template asset preflight live in `synthesizers/prompt_policy.py`.
- Category and difficulty distribution targets are read from `configs/task_categories.yaml`; category assignment balances planned pair counts against those targets while respecting each source profile's allowed categories.
- In addition to `pilot` and `full`, synthesis supports `subset` mode for budget-aware training runs. `subset_targets` in `configs/source_profiles.yaml` select a representative source/content/richness-aware slice that currently renders 6,494 one-pair prompts across all 16 sources.
- Document selection, category assignment, difficulty assignment, and prompt-plan construction live in `synthesizers/planner.py`; `PromptBuilder` renders prompts from those explicit planning choices.
- Raw Phase 2 documents remain complete; `synthesizers/prompts/compactors/prompt_compactors.py` creates prompt-ready source views and dynamically loads source compactors named `synthesizers/prompts/compactors/<source>_compactor.py` exposing `compact_for_prompt(doc, content)`.
- Source-specific compactors currently include `cisa_advisories_compactor.py`, `cisa_kev_compactor.py`, `mitre_attack_compactor.py`, `cybersec_skills_compactor.py`, `velociraptor_artifacts_compactor.py`, `loldrivers_compactor.py`, and `hijacklibs_compactor.py`.
- `cisa_advisories_compactor.py` keeps advisory metadata, key summary/recommendation sections, a capped CVE list, and top CVSS vulnerability blocks while omitting repeated legal/vendor boilerplate and lower-priority vulnerability blocks from prompts.
- `cisa_kev_compactor.py` keeps vendor/product/CVE summary metadata and selected KEV detail blocks while capping large vendor vulnerability catalogs.
- `mitre_attack_compactor.py` keeps technique identifiers, tactics/platforms, descriptions, selected concrete procedure examples, mitigations, and detections while capping large ATT&CK procedure lists.
- `cybersec_skills_compactor.py` keeps skill metadata, framework mappings, tools, core workflow sections, selected workflow steps, and scenarios while shortening long scripts/code blocks without leaving malformed Markdown code fences.
- `velociraptor_artifacts_compactor.py` keeps artifact metadata, parameters, references, reports, full Velociraptor query bodies, and long structured parameter defaults; it opts out of shared source truncation so VQL `precondition`, `export`, `query`, `queries`, VQL-like defaults, and structured defaults are not capped.
- `loldrivers_compactor.py` keeps driver IDs, categories, ATT&CK/CVE mappings, abuse commands, detection strings, selected hashes, and selected vulnerable sample metadata while capping repeated sample blocks.
- `hijacklibs_compactor.py` keeps DLL names, expected locations, hijack types, vulnerable executable paths, conditions, variables, hashes, and privilege/elevation flags while capping repeated executable/signature blocks.
- Prompt rendering and Gemini execution live in `synthesizers/runner.py`, while `scripts/synthesize.py` only parses CLI arguments and dispatches.
- Prompt rendering writes `prompts.jsonl` by default; individual Markdown prompt files are opt-in with `--write-prompt-files`.
- The Gemini runner reads `GEMINI_API_KEY` from `.env` or the environment, writes `prompts.jsonl`, `raw_outputs.jsonl`, `accepted.jsonl`, `rejected.jsonl`, and `generation_manifest.json`, annotates prompt/output rows with prompt hashes and run IDs, records generation attempt and validation retry metadata, and can skip present terminal accepted/rejected prompts whose prompt hash and model match the current run when `--skip-present` is supplied.
- API retries use configurable exponential backoff with jitter. Validation failures can trigger a regeneration prompt that includes the validator errors and hard output requirements; raw outputs for both original generations and validation retries are preserved.
- Prompt hashes, run IDs, and present-output detection live in `synthesizers/run_state.py` rather than the CLI.
- In full mode only, a current-run rejection-rate circuit breaker stops generation when rejected prompts meet or exceed the configured threshold after a minimum number of attempts.
- Pilot mode still validates each generated output, but does not stop early based on aggregate rejection rate.
- Broader rate-limit orchestration and alternate-model comparison jobs are still pending.

Prompt construction uses two guidance layers plus one source-content layer: coarse `source_type` guidance derived from the collector `source`, optional exact `content_type` guidance derived from each raw document, and optional prompt-time content compaction by source. This keeps broad behavior stable while adding specialized handling for labels such as `atomic_test`, `lolbas_windows_lolbin`, `gtfobins_linux_abuse_function`, `hayabusa_rule`, `event_dictionary`, `tool_module`, `tool_plugin`, and Velociraptor artifact variants. Taxonomy refs are deterministic-first: `PromptBuilder` suggests one to three valid taxonomy IDs from source/content/tactic/platform hints, stores them on `PromptRecord`, renders them as a JSON list in the prompt, and the validator normalizes deterministic metadata from the prompt record before checking generated content.

The generated-pair rejection gates catch invalid JSON, strict schema failures including extra fields, too many or too few pairs, invalid ATT&CK/ATLAS ID formats, broken `<reasoning>` links, duplicate reasoning IDs, missing caveats, empty evidence/analysis/caveat lines, missing final answers, grounding/tag mismatches between `grounding` and `[GENERAL KNOWLEDGE]`, and concrete indicators not present in the source document. Generated `source_doc_id`, `source`, `category`, `difficulty`, `taxonomy_refs`, and `reasoning_format` are overwritten from the prompt record before these checks, because they are deterministic provenance fields.

Phase 4 quality assurance should validate structure, ATT&CK/ATLAS IDs, taxonomy refs, tool names, `<reasoning>` link integrity, near-duplicates, source balance, difficulty balance, and the 57-category taxonomy heatmap.

Phase 5 packaging should split by `source_doc_id` to prevent leakage and export local chat-formatted JSONL for training. The canonical export keeps `<reasoning>`; a model-specific GLM export may convert it to `<think>` only if needed. 

Phase 6 validates LoRA SFT results on DGX Sparks and integrates the best checkpoint into Shepherd.

## Remaining Pipeline Gates

The Gemini client uses `models.generate_content` with `response_mime_type="application/json"` and a sanitized `InstructionPair` response schema, then validates the resulting JSON through the same Phase 3 rejection gates. If validation fails and `generation.validation_retries` is greater than zero, the runner can ask Gemini to regenerate using the original prompt plus a compact list of validation errors.

The remaining workflow is intentionally gated:

1. Phase 3 pilot: run Gemini on the planned pilot sample, then manually review 100% of pilot output. Fix prompts, validators, source profiles, or pair counts before continuing.
2. Phase 3 full generation: run the full Gemini job only after the pilot has acceptable pass rate and manual quality. `accepted.jsonl` is the input to Phase 4, not final training data.
3. Phase 4 quality validation: consume `accepted.jsonl`, apply deterministic checks, heuristic scoring, weak-reasoning and unsupported-claim checks, near-duplicate detection, balance audits, and targeted review. Produce a filtered dataset plus review and rejection manifests.
4. Phase 5 packaging: consume the Phase 4 filtered dataset, split by `source_doc_id`, and write GLM-friendly train/validation/test JSONL plus a packaging manifest.
5. Phase 6 fine-tuning: run baseline evaluation, train LoRA SFT on GLM-4.7-Flash, rerun evaluation, compare against baseline, and integrate into Shepherd only if results improve.
