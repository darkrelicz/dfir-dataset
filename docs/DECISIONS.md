# Decisions

## Durable Project State

- Durable project context lives in `docs/PROJECT_BRIEF.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN_SYSTEM.md`, `docs/TODO.md`, and this file.
- Do not rely on chat history for project memory. Update these files when project direction, architecture, design rules, tasks, or major decisions change.

## Data Model

- All collectors normalize source material into the shared Pydantic `RawDocument` schema.
- Collector run metadata is stored in `CollectionManifest` entries and combined at `data/raw/collection_manifest.json`.

## Dataset Scope

- The selected scope is Core + Tier 1 + Tier 2: all 16 collectors C1-C7 and AF1-AF9.
- Tier 3 sources AF10-AF15 are deferred. Semi-structured and unstructured sources are also deferred unless the plan changes.
- The dataset is organized around five task categories: Artifact Analysis, TTP Identification, Triage & Threat Hunting, Detection Engineering, and Incident Report Generation.
- The artifact taxonomy remains broader than this iteration's source coverage so the successor has a roadmap.

## Source Collection

- Git-backed sources use local shallow clones under `data/raw/.repos/` for reproducibility and faster reruns.
- Sigma rules are parsed with `yaml.safe_load` instead of pySigma because the pipeline currently needs metadata extraction rather than rule translation.
- Atomic Red Team emits one raw document per atomic test, not one document per technique file.
- Cybersecurity Skills entries are filtered by body length to avoid thin workflow templates becoming hallucinated synthesis examples.

## Taxonomy And Config Separation

- `docs/TAXONOMY.md` is the human-readable 57-category DFIR artifact taxonomy.
- `configs/quality.yaml` is the machine-readable taxonomy validation and coverage map.
- `configs/task_categories.yaml` defines the five model behavior categories used for synthesis.
- `configs/source_profiles.yaml` defines Phase 3 source profiles, content-type overrides, pair caps, and pilot sampling targets.

## Product Shape

- This repository is a Python data pipeline.
- Shared `utils/` helpers should remain low-level and domain-neutral: serialization, text normalization, stable IDs, simple coercions, ordered threshold checks, Markdown frontmatter parsing, and generic Git source helpers. Source-specific parsing should stay inside collectors or synthesizer modules.

## Phase 3 Guardrails

- Do not run full instruction-pair synthesis from an incomplete or invalid raw corpus.
- Thin sources should generate fewer pairs per document to reduce invented forensic detail.
- Synthesis should preserve source provenance and write generation manifests for auditability.
- Phase 3 should reject obvious generation failures inline instead of relying on Phase 4 to catch them.
- Inline rejection covers invalid JSON, strict schema failures, too many or too few pairs, broken `<reasoning>` links, duplicate reasoning IDs, missing caveats, empty evidence/analysis/caveat text, missing taxonomy refs after deterministic metadata normalization, invalid taxonomy refs, malformed ATT&CK/ATLAS IDs, grounding/tag mismatches, and invented concrete indicators.
- Gemini 2.5 Flash is the selected primary teacher model.
- Phase 3 generation uses the direct Gemini API via the Google GenAI SDK and `GEMINI_API_KEY`.
- Gemini request controls belong under `generation` in `configs/synthesis.yaml`; the Gemini client maps supported controls into `models.generate_content` config alongside structured JSON response settings. Use `thinking_budget` for Gemini 2.5 thinking control. Do not use `thinking_level` with the current `gemini-2.5-flash` `generate_content` path because the API rejects it for this model. Do not request thought summaries for structured JSON generation.
- Local API secrets live in `.env`, which is ignored by git. Do not commit real API keys.
- OpenRouter is not used for canonical instruction generation because Gemini 2.5 Flash is not available through OpenRouter's distillable-model path.
- Claude Sonnet or any alternate teacher model must run as a separate, explicitly labeled comparison job rather than an automatic fallback, so generated data provenance stays clean.
- The historical full-synthesis pilot gate was at least 75% pass rate before full-corpus synthesis. Under the shortened timeline, the completed `subset` run is the current Phase 3 deliverable, and full-corpus synthesis is deferred.
- Canonical synthesized responses use `<reasoning>`, not `<think>`.
- The `<reasoning>` block is an auditable rationale with linked IDs: evidence (`E1`), analysis (`A1 [uses E1]`), conclusions (`C1 [uses E1,A1]`), and caveats (`CV1 [applies_to C1]`).
- Prompting should require source-grounded evidence, confidence labels, explicit caveats, uncertainty calibration, and final answers that do not introduce claims absent from linked conclusions.
- The `grounding` field is a validation contract. Use `source_only` only when the response contains no `[GENERAL KNOWLEDGE]` tags, and use `source_plus_general` whenever the response includes any well-established but non-source claim tagged with `[GENERAL KNOWLEDGE]`.
- The Pydantic response schema is not a substitute for prompt instructions about the linked reasoning chain. Keep the concise `<reasoning>` structure and example in the prompt even when using Gemini structured JSON output.
- A model-specific packaging exporter may convert `<reasoning>` to `<think>` for GLM training only if the training recipe requires that exact tag. The canonical synthesized and packaged dataset remains `<reasoning>`.
- Pilot sampling is source-aware and stratified by content type and source richness so the pilot reviews both thin and rich examples. Pair counts are source-richness aware: documents under 250 words generate one pair, and thin content types such as artifact definitions, event dictionaries, and abuse database entries are capped to avoid padded hallucinations.
- Prompting uses a two-layer source model: broad `source_type` instructions from the collector source plus selective exact `content_type` overrides from each raw document.
- Source and content-type prompt policy should live in config, not hard-coded Python mappings.
- Taxonomy refs are deterministic-first prompt metadata. `PromptBuilder` computes one to three candidate refs from source/content/tactic/platform hints, stores them on `PromptRecord`, and renders them as a JSON list; the full 57-ID taxonomy list is not repeated in every prompt. Validators normalize generated `category`, `difficulty`, `source_doc_id`, `source`, and `taxonomy_refs` from the prompt record before checking the pair, so model typos in deterministic provenance do not reject otherwise valid content.
- Category and difficulty distribution targets come from `configs/task_categories.yaml`; prompt generation should treat that config as the source of truth while still respecting source-profile category allowlists.
- Prompt/category/difficulty config parsing and prompt-template asset preflight belong in `synthesizers/prompt_policy.py`, not in `PromptBuilder`.
- Do not create a separate prompt file for every raw `content_type` by default. Add content-type templates only when the generation behavior differs materially from the broad source type.
- Prompt rendering writes `prompts.jsonl` by default. Per-prompt Markdown files are opt-in for manual inspection with `--write-prompt-files`.
- Prompt planning belongs in `synthesizers/planner.py`; CLI entrypoints should not own document selection, category balancing, difficulty assignment, or prompt-plan construction.
- `PromptBuilder` should render prompts from explicit category and difficulty choices supplied by the planner, rather than silently assigning fallback categories or difficulties.
- Phase 2 raw documents should remain complete for provenance and reprocessing. Prompt-cost reduction belongs in Phase 3 prompt-time compactors under `synthesizers/prompts/compactors/`.
- Source compactors should follow the naming convention `synthesizers/prompts/compactors/<source>_compactor.py` and expose `compact_for_prompt(doc, content)`. Shared dispatch, truncation, and Markdown helpers live in `prompt_compactors.py`.
- `cisa_advisories_compactor.py` is the first source-specific prompt compactor. It preserves advisory metadata, dates, CVE count/IDs, summary/recommendation/context sections, and top CVSS vulnerability blocks while omitting repeated legal/vendor boilerplate, references, and lower-priority vulnerability blocks from prompts.
- `cisa_kev_compactor.py` compacts vendor-grouped KEV catalogs by preserving vendor/product/CVE summary metadata and selected detail blocks, prioritizing ransomware-linked and recent catalog additions.
- `mitre_attack_compactor.py` and `cybersec_skills_compactor.py` compact high-volume prompt sources by capping large procedure/workflow/code sections while preserving identifiers, mappings, detections, tools, and operational examples.
- `velociraptor_artifacts_compactor.py` must preserve Velociraptor query bodies in full. It may shorten duplicate prose and non-query boilerplate, but it should not cap VQL `precondition`, `export`, `query`, `queries`, VQL-like parameter defaults, or long structured parameter defaults such as YARA, Grok, CSV, registry glob, JSON, and YAML blocks.
- Source compactors may set `skip_source_truncation` when the source value would be harmed by the shared `max_source_chars` tail/head truncation. Velociraptor uses this because VQL bodies are the main training signal.
- `loldrivers_compactor.py` and `hijacklibs_compactor.py` compact abuse-database sources by preserving concrete commands, paths, hashes, CVEs, detection strings, hijack conditions, and privilege/elevation flags while capping repeated sample or executable/signature blocks.
- The first Gemini generation runner is sequential and can skip present outputs with `--skip-present`. Present-output skipping should only skip terminal accepted/rejected prompts whose prompt hash and model match the current run; raw model output alone is not terminal. The runner uses configurable API retry/backoff with jitter and can perform one or more validation-feedback regenerations for recoverable validation failures. Prefer a reviewed one-prompt smoke test and pilot run before adding concurrency.
- Generation execution belongs in `synthesizers/runner.py`; `scripts/synthesize.py` should stay a thin argument parser and dispatcher.
- Prompt hashing, run IDs, and present-output detection are synthesis run-state concerns and should live outside the CLI entrypoint.
- The Gemini runner has a full-mode rejection-rate circuit breaker. By default, after 20 current-run attempted prompts in full synthesis, generation stops if rejected prompts are at least 20%. Pilot mode still validates each generated output but does not stop early based on aggregate rejection rate.
- The current Phase 3 deliverable is `data/synthesized/gemini_subset_1/`, a budget-aware reduced subset with 6,494 prompts and 6,287 accepted candidate pairs for `run-20260701T021807Z`.
- Future full-corpus generation must not begin until a fresh Gemini smoke test and reviewed pilot have acceptable validator pass rate and manual quality.
- `accepted.jsonl` from Phase 3 is only candidate synthesis output. It must pass Phase 4 quality validation before packaging or training.

## Phase 4 Guardrails

- Phase 4 quality validation should be primarily deterministic and heuristic, with AI-assisted judging and manual review used for fuzzy quality issues such as weak reasoning or unsupported claims.
- Phase 4 must not depend on Phase 3's generated-output validators for differentiation. Phase 3 and Phase 4 share pure validation primitives in `validation/`, but each stage keeps its own policy wrapper. Phase 4 has row-level gates for schema, source provenance, taxonomy refs, ATT&CK/ATLAS IDs, reasoning links, grounding, invented indicators, source specificity, operational value, and rubric scoring, plus dataset-level gates for near-duplicates and distribution audits. Only `filtered.jsonl` is eligible for Phase 5 packaging.
- Phase 4 ATT&CK/ATLAS validation uses local reference caches when present (`data/raw/.cache/enterprise-attack.json` and `data/raw/.repos/atlas-data/dist/ATLAS.yaml`) with raw-corpus fallbacks. This keeps validation reproducible and offline while avoiding false rejections from the reduced prompt subset.
- The old `10k-15k` filtered-pair target belongs to the full-synthesis plan. Under the shortened timeline and reduced subset budget, the gate should optimize for coverage, factuality, and reviewability rather than forcing the old pair count.
- Phase 4 should expose sub-stage progress through normal Python logging. `scripts/quality_filter.py` defaults to `--log-level INFO` and logs config loading, output preparation, raw/reference loading, row-validation progress, dataset audits, JSONL writes, manual spot-check sampling, and manifest writing.
- Phase 5 packaging consumes Phase 4 filtered output, not raw Phase 3 `accepted.jsonl`.

## Training And Hosting

- Dataset hosting is local-only on DGX Sparks storage, not HuggingFace Hub, unless this decision changes.
- Training is planned as LoRA SFT via Unsloth on GLM-4.7-Flash.
- Baseline evaluation must run before fine-tuning, including AI/LLM-specific ATLAS cases.
