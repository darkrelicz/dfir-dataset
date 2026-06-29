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
- Inline rejection covers invalid JSON, strict schema failures, wrong source IDs, too many or too few pairs, broken `<reasoning>` links, duplicate reasoning IDs, missing caveats, empty evidence/analysis/caveat text, missing taxonomy refs, invalid taxonomy refs, malformed ATT&CK/ATLAS IDs, and invented concrete indicators.
- Gemini 2.5 Flash is the selected primary teacher model.
- Phase 3 generation uses the direct Gemini API via the Google GenAI SDK and `GEMINI_API_KEY`.
- Gemini request controls such as `thinking_level` belong under `generation` in `configs/synthesis.yaml`, because they are sent in the Interactions API `generation_config`.
- Local API secrets live in `.env`, which is ignored by git. Do not commit real API keys.
- OpenRouter is not used for canonical instruction generation because Gemini 2.5 Flash is not available through OpenRouter's distillable-model path.
- Claude Sonnet or any alternate teacher model must run as a separate, explicitly labeled comparison job rather than an automatic fallback, so generated data provenance stays clean.
- The planned pilot gate is at least 75% pass rate before full synthesis.
- Canonical synthesized responses use `<reasoning>`, not `<think>`.
- The `<reasoning>` block is an auditable rationale with linked IDs: evidence (`E1`), analysis (`A1 [uses E1]`), conclusions (`C1 [uses E1,A1]`), and caveats (`CV1 [applies_to C1]`).
- Prompting should require source-grounded evidence, confidence labels, explicit caveats, uncertainty calibration, and final answers that do not introduce claims absent from linked conclusions.
- The Pydantic response schema is not a substitute for prompt instructions about the linked reasoning chain. Keep the concise `<reasoning>` structure and example in the prompt even when using Gemini `response_format`.
- A model-specific packaging exporter may convert `<reasoning>` to `<think>` for GLM training only if the training recipe requires that exact tag. The canonical synthesized and packaged dataset remains `<reasoning>`.
- Pilot sampling is source-aware and stratified by content type and source richness so the pilot reviews both thin and rich examples. Pair counts are source-richness aware: documents under 250 words generate one pair, and thin content types such as artifact definitions, event dictionaries, and abuse database entries are capped to avoid padded hallucinations.
- Prompting uses a two-layer source model: broad `source_type` instructions from the collector source plus selective exact `content_type` overrides from each raw document.
- Source and content-type prompt policy should live in config, not hard-coded Python mappings.
- Taxonomy refs are deterministic-first prompt metadata. `PromptBuilder` computes one to three candidate refs from source/content/tactic/platform hints and renders them as a JSON list; the full 57-ID taxonomy list is not repeated in every prompt. The model should normally use the rendered refs, while validators still reject missing or unknown refs.
- Category and difficulty distribution targets come from `configs/task_categories.yaml`; prompt generation should treat that config as the source of truth while still respecting source-profile category allowlists.
- Prompt/category/difficulty config parsing and prompt-template asset preflight belong in `synthesizers/prompt_policy.py`, not in `PromptBuilder`.
- Do not create a separate prompt file for every raw `content_type` by default. Add content-type templates only when the generation behavior differs materially from the broad source type.
- Prompt rendering writes `prompts.jsonl` by default. Per-prompt Markdown files are opt-in for manual inspection with `--write-prompt-files`.
- Prompt planning belongs in `synthesizers/planner.py`; CLI entrypoints should not own document selection, category balancing, difficulty assignment, or prompt-plan construction.
- `PromptBuilder` should render prompts from explicit category and difficulty choices supplied by the planner, rather than silently assigning fallback categories or difficulties.
- Phase 2 raw documents should remain complete for provenance and reprocessing. Prompt-cost reduction belongs in Phase 3 prompt-time compactors under `synthesizers/prompts/compactors/`.
- Source compactors should follow the naming convention `synthesizers/prompts/compactors/<source>_compactor.py` and expose `compact_for_prompt(doc, content)`. Shared dispatch, truncation, and Markdown helpers live in `prompt_compactors.py`.
- `cisa_advisories_compactor.py` is the first source-specific prompt compactor. It preserves advisory metadata, dates, CVE count/IDs, summary/recommendation/context sections, and top CVSS vulnerability blocks while omitting repeated legal/vendor boilerplate, references, and lower-priority vulnerability blocks from prompts.
- The first Gemini generation runner is sequential and can skip present outputs with `--skip-present`. Present-output skipping should only skip terminal accepted/rejected prompts whose prompt hash and model match the current run; raw model output alone is not terminal. Prefer a reviewed one-prompt smoke test and pilot run before adding concurrency.
- Generation execution belongs in `synthesizers/runner.py`; `scripts/synthesize.py` should stay a thin argument parser and dispatcher.
- Prompt hashing, run IDs, and present-output detection are synthesis run-state concerns and should live outside the CLI entrypoint.
- The Gemini runner has a full-mode rejection-rate circuit breaker. By default, after 20 current-run attempted prompts in full synthesis, generation stops if rejected prompts are at least 20%. Pilot mode still validates each generated output but does not stop early based on aggregate rejection rate.
- Phase 3 full generation must not begin until the Gemini pilot has acceptable validator pass rate and acceptable manual quality.
- `accepted.jsonl` from Phase 3 is only candidate synthesis output. It must pass Phase 4 quality validation before packaging or training.
- Phase 4 quality validation should be primarily deterministic and heuristic, with AI-assisted judging and manual review used for fuzzy quality issues such as weak reasoning or unsupported claims.
- Phase 5 packaging consumes Phase 4 filtered output, not raw Phase 3 `accepted.jsonl`.

## Training And Hosting

- Dataset hosting is local-only on DGX Sparks storage, not HuggingFace Hub, unless this decision changes.
- Training is planned as LoRA SFT via Unsloth on GLM-4.7-Flash.
- Baseline evaluation must run before fine-tuning, including AI/LLM-specific ATLAS cases.
