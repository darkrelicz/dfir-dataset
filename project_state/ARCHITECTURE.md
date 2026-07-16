# Architecture

## Current Project Type

This repository is a Python dataset pipeline. The primary product code is not a frontend application, browser routing layer, CSS system, or UI component tree. The `docs/` directory is a separate MarkBind documentation site used for successor-facing GitHub Pages documentation.

## Runtime And Frameworks

- Language: Python 3.11+
- Packaging: `pyproject.toml` with setuptools
- CLI entrypoints: `dfir-collect`, `dfir-synthesize`, `dfir-quality`, `dfir-package`, `dfir-evaluate`, `dfir-compare-evals`, and `dfir-train-lora`
- Main libraries: `pydantic`, `pyyaml`, `jsonlines`, `google-genai`, `requests`, `gitpython`, `rich`, `tqdm`, `mitreattack-python`, `unsloth`, `transformers`, and `trl`
- CUDA-specific training environment: `training-cuda130` adds the pinned Torch/fsspec constraints after installing the matching CUDA Torch wheel.
- Tests are configured for `pytest`; focused judge-response, sequential-runner, and comparison tests live under `tests/`.

## Pipeline Layout

- `collectors/`: Phase 2 source collectors. Each collector normalizes one source into the shared `RawDocument` schema.
- `scripts/collect_all.py`: CLI orchestrator for running one or all collectors and writing `data/raw/collection_manifest.json`.
- `utils/`: Shared low-level helpers for YAML/JSON/JSONL IO, text cleanup, list normalization, slug/filename generation, stable hashing, ordered threshold checks, Markdown frontmatter parsing, and GitHub source URL/commit helpers.
- `configs/collection.yaml`: Source URLs, clone/cache paths, output directories, and collector-specific options.
- `configs/task_categories.yaml`: Five task categories, target distributions, and category-specific `quality_signals` used by synthesis and Phase 4 heuristic scoring.
- `configs/synthesis.yaml`: Phase 3 model settings, pair targets, Gemini thinking budget, API retry/backoff, validation retry, and prompt-size controls.
- `configs/source_profiles.yaml`: Phase 3 source profiles, content-type overrides, pair caps, and pilot sampling targets.
- `configs/quality.yaml`: Programmatic taxonomy IDs, coverage levels, scoring weights, no-API heuristic terms, and dedupe/balance settings.
- `configs/packaging.yaml`: Phase 5 packaging inputs, local output paths, source-document split settings, chat record format, and response-style policy.
- `configs/evaluation.yaml`: Phase 6 benchmark input path, target and judge endpoint settings, generation parameters, and prompt wrapper.
- `configs/finetune_glm47flash.yaml`: Phase 6 local Unsloth/GLM LoRA SFT settings, dataset paths, LoRA hyperparameters, training arguments, and export paths.
- `synthesizers/`: Phase 3 scaffolding for source profiles, content-type profiles, prompt policy validation, prompt planning, prompt rendering, prompt-time source compaction, pilot sampling, model clients, schemas, run-state helpers, generation execution, and validation helpers.
- `validation/`: Shared pure validation primitives for reasoning blocks, grounding tags, concrete indicators, mapping ID formats, and taxonomy config extraction. Phase 3 and Phase 4 call these primitives through separate stage-specific wrappers.
- `scripts/synthesize.py`: Thin CLI for raw corpus validation, no-API prompt rendering, and Gemini-backed instruction-pair generation.
- `quality/`: Phase 4 quality filtering for Phase 3 accepted pairs, including stage-specific row validators built on shared validation primitives, local ATT&CK/ATLAS ID reference checks, config-backed tool allowlist checks, config-driven heuristic rubric scoring, near-duplicate checks, source/category/difficulty/taxonomy audits, manual spot-check sampling, manifest output, and stage-level logging.
- `scripts/quality_filter.py`: Thin CLI for running the Phase 4 quality filter against a Phase 3 `accepted.jsonl`; configures `INFO` stage logs by default.
- `dataset_packaging/`: Phase 5 local dataset packaging for Unsloth/GLM SFT. It reads Phase 4 filtered and review rows directly, converts configured rows into direct-answer examples, splits by `source_doc_id`, and writes chat JSONL plus a small packaging manifest.
- `scripts/package_dataset.py`: Thin CLI for running Phase 5 packaging from `configs/packaging.yaml`; configures `INFO` stage logs by default.
- `evaluation/`: Phase 6 benchmark schemas, structured-output parsing, local LLM judging, OpenAI-compatible and prediction-file model clients, sequential orchestration, atomic per-case checkpoints, judge scorecard output, and before/after comparison helpers.
- `scripts/run_evaluation.py`: Thin CLI for running the Phase 6 evaluator against a local OpenAI-compatible model endpoint or a prediction JSONL file.
- `scripts/compare_evaluations.py`: Thin CLI for comparing baseline and fine-tuned Phase 6 score outputs.
- `scripts/finetune.py`: Phase 6 Unsloth LoRA SFT runner for GLM-4.7-Flash.
- `project_state/TAXONOMY.md`: Human-readable 57-category DFIR artifact taxonomy.
- `docs/`: Self-contained MarkBind documentation site for user/developer guides, PlantUML source diagrams, current implementation notes, and suggested improvements. Built locally with `npm run build` from inside `docs/`.
- `.github/workflows/deploy-guides.yml`: GitHub Pages workflow for building `docs/` with MarkBind and deploying the generated `docs/_site` artifact.
- `data/raw/`: Generated collector outputs and cloned upstream repositories. Treat as generated data.

The project plan's packaging phase is implemented as `dataset_packaging/` rather than `packaging/` to avoid shadowing Python's common third-party `packaging` library. Phase 6 evaluation/training scaffolding now lives in `evaluation/` plus thin scripts. The `synthesizers/` package includes the direct Gemini client and generation runner; Claude comparison jobs are not implemented.

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

## Synthesis And Downstream Architecture

Phase 3 synthesis reads validated `RawDocument` JSONL and writes instruction pairs plus generation manifests under `data/synthesized/`. The current run is a budget-aware subset with 6,494 rendered prompts, 6,287 accepted candidate pairs, and 206 prompt rows rejected. Full-corpus synthesis is deferred to a future budget window or successor. The generation path uses the direct Gemini API through the Google GenAI SDK, with Gemini 2.5 Flash as the primary teacher model, five task-category prompt templates, source-type-specific prompt instructions, and selective content-type prompt overrides. Any Claude or alternate-model comparison must run as a separate, explicitly labeled job rather than an automatic fallback. Canonical synthesized responses use `<reasoning>` blocks with linked evidence, analysis, conclusion, and caveat IDs.

### Implemented Phase 3 components include

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

The generated-pair rejection gates catch invalid JSON, strict schema failures including extra fields, too many or too few pairs, invalid ATT&CK/ATLAS ID formats, broken `<reasoning>` links, duplicate reasoning IDs, missing caveats, empty evidence/analysis/caveat lines, missing final answers, grounding/tag mismatches between `grounding` and `[GENERAL KNOWLEDGE]`, and concrete indicators not present in the source document. Generated `source_doc_id`, `source`, `category`, `difficulty`, and `taxonomy_refs` are overwritten from the prompt record before these checks, because they are deterministic provenance fields.

### Current Phase 4 implementation

The Phase 4 quality gate consumes Phase 3 `accepted.jsonl` and writes `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, `manual_spot_check_sample.jsonl`, and `quality_manifest.json` under `data/quality/<run>/`. It does not call Phase 3's generated-output validators; instead, Phase 3 and Phase 4 share pure primitives from `validation/` while keeping separate stage policies. Phase 4 validates candidate row shape, source provenance, taxonomy refs, ATT&CK/ATLAS IDs against local reference caches when present, tool names against source text and the config-backed allowlist, `<reasoning>` link integrity and step count, grounding/tag consistency, final-answer presence, and concrete indicators absent from source. It then computes no-API heuristic rubric scores using `configs/task_categories.yaml` category `quality_signals` and descriptions, `configs/quality.yaml` operational verbs and generic-answer penalty terms, tiered source-token overlap, concrete artifact counts, caveat presence, and response-length tiers. Dataset gates apply near-duplicate checks, source balance review, category balance audit, difficulty balance audit, and taxonomy coverage audit. Objective failures go to `rejected.jsonl`; non-blocking concerns such as mapping metadata inconsistencies, unknown tools, overlong reasoning, source-balance pressure, or `source_plus_general` concrete indicators go to `review_queue.jsonl`. The CLI logs config loading, output setup, raw/reference loading, row validation progress, dataset gates, output writes, spot-check sampling, and manifest writing so users can see which sub-stage is complete.

Phase 5 packaging splits by `source_doc_id` to prevent leakage and exports local chat-formatted JSONL for training. Under the shortened timeline, the package input is the union of Phase 4 `filtered.jsonl` and `review_queue.jsonl`; the packager does not read or recount `rejected.jsonl`. The current package at `data/packaged/gemini_subset_1/` contains `train.jsonl`, `validation.jsonl`, `test.jsonl`, and `packaging_manifest.json`. Packaged records use a `messages` array with system/user/assistant turns plus metadata preserving `quality_status`, `quality_issues`, `quality_score`, source, category, difficulty, taxonomy refs, and source document IDs. The package keeps filtered rows as `<reasoning>` examples and converts review rows into direct-answer examples by stripping the reasoning block, yielding an approximately 75/25 reasoning/direct mix for Unsloth GLM-4.7-Flash training. Hugging Face dataset-card and upload work are intentionally not implemented for the current local training path.

The first Phase 6 training run, `train-20260714T025314Z`, completed one epoch/552 steps against package `package-20260708T071253Z`. Checkpoints and `training_manifest.json` live under `data/finetune/glm47_flash_lora_dfir_subset1/`; the configured export paths place the final LoRA adapter under `data/finetune/glm47_flash_subset1/lora_adapter/`, and the generated Q4_K_M file is under `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/`. The manifest records training loss about 0.9597 and runtime about 38,019 seconds. It also exposes current reproducibility defects: the manifest's `training` object is empty because the runner reads a nonexistent `training` key instead of `finetune`; `loftq_config` was serialized as the string `None`; and the actual GGUF directory has an added `_gguf` suffix not reflected in the configured path.

Phase 6 evaluation validates the trained artifact before any Shepherd integration. The evaluator can call a local OpenAI-compatible endpoint or replay prediction JSONL keyed by `case_id`. It writes only `scorecards/llm_judge/`; the former statistical scorer has been removed. TTP, typed IOC, and ranked-action tasks request structured JSON for inspectability, while report and reasoning tasks remain free-form. For each case, the target response is generated first, then the separately configured local judge receives the full answer key, rubric, and `acceptable_variants` and returns a validated JSON verdict. After each verdict, the runner atomically replaces `predictions.jsonl`, judge `case_results.jsonl`, aggregate `scores.json`, and `evaluation_manifest.json`. Partial checkpoints are marked `in_progress`, and comparison rejects them. Checkpointing preserves completed work for inspection but does not resume it; a new invocation starts from case one. Scorecards fingerprint the full judge configuration and protocol and record a calibration ID; comparison requires matching benchmark content, case IDs, judge fingerprint, and calibration ID. It does not currently reject the literal placeholder `uncalibrated`, so the non-placeholder requirement remains release policy rather than an enforced code gate. The base-model run `data/evaluation/glm47-flash-base/` completed 68/68 cases at an exploratory overall score of 0.7588. It identifies the judge as uncalibrated, so it is not final comparison evidence. `pyproject.toml` declares Unsloth/Transformers/TRL and the `training-cuda130` extra carries CUDA-specific Torch/fsspec constraints.

### Phase 6 evaluation artifact contract

- `data/evaluation/<run>/predictions.jsonl`: target responses for successfully judged cases only.
- `data/evaluation/<run>/scorecards/llm_judge/case_results.jsonl`: bounded per-case scores, judge reasons/criteria, acceptable-variant match metadata, and manual-review flags.
- `data/evaluation/<run>/scorecards/llm_judge/scores.json`: rolling aggregate, completed/planned counts, benchmark fingerprint, judge protocol/config fingerprint, calibration ID, and `run_status`.
- `data/evaluation/<run>/evaluation_manifest.json`: authoritative run metadata, completed case IDs, planned/completed counts, scorecard paths/configuration, and top-level `in_progress` or `complete` status.

Atomic replacement keeps these four files mutually consistent at each completed-case boundary. It preserves completed work after interruption but does not automatically resume a run; prediction-file replay remains the available recovery path.

## Remaining Pipeline Gates

The Gemini client uses `models.generate_content` with `response_mime_type="application/json"` and a sanitized `InstructionPair` response schema, then validates the resulting JSON through the same Phase 3 rejection gates. If validation fails and `generation.validation_retries` is greater than zero, the runner can ask Gemini to regenerate using the original prompt plus a compact list of validation errors.

The remaining workflow is intentionally gated around Phase 6 training and later stages:

1. Phase 6 benchmark and calibration: finish manual benchmark review, build the human-scored calibration/holdout sets, and freeze a versioned judge configuration.
2. Phase 6 base evaluation: complete a calibrated `python -m scripts.run_evaluation` run against untrained GLM-4.7-Flash; exploratory uncalibrated outputs do not satisfy this gate.
3. Phase 6 tuned evaluation: serve the existing tuned Q4_K_M artifact and rerun the identical benchmark with the frozen judge.
4. Phase 6 comparison: compare only complete scorecards with `python -m scripts.compare_evaluations`, review critical cases manually, and integrate into Shepherd only if results improve.
5. Future full-corpus synthesis: if budget returns, rerun a smoke test and reviewed pilot before launching the larger full-generation job. Treat its `accepted.jsonl` as candidate data until Phase 4 passes again.
