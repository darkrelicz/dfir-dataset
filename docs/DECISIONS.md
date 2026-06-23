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
- CISA advisory collection uses RSS/HTML scraping because summaries alone are insufficient for DFIR training examples.
- Cybersecurity Skills entries are filtered by body length to avoid thin workflow templates becoming hallucinated synthesis examples.

## Taxonomy And Config Separation

- `docs/TAXONOMY.md` is the human-readable 57-category DFIR artifact taxonomy.
- `configs/quality.yaml` is the machine-readable taxonomy validation and coverage map.
- `configs/task_categories.yaml` defines the five model behavior categories used for synthesis.

## Product Shape

- This repository is currently a Python data pipeline, not a website.
- No frontend framework, route structure, styling system, or component library has been selected.

## Phase 3 Guardrails

- Do not run full instruction-pair synthesis from an incomplete or invalid raw corpus.
- Thin sources should generate fewer pairs per document to reduce invented forensic detail.
- Synthesis should preserve source provenance and write generation manifests for auditability.
- Phase 3 should reject obvious generation failures inline instead of relying on Phase 4 to catch them.
- Inline rejection covers invalid JSON, wrong source IDs, too many or too few pairs, broken `<reasoning>` links, empty evidence, invalid taxonomy refs, malformed ATT&CK/ATLAS IDs, and invented concrete indicators.
- Gemini 2.5 Flash is the selected primary teacher model.
- Phase 3 generation uses the direct Gemini API via the Google GenAI SDK and `GEMINI_API_KEY`.
- OpenRouter is not used for canonical instruction generation because Gemini 2.5 Flash is not available through OpenRouter's distillable-model path.
- Claude Sonnet or any alternate teacher model must run as a separate, explicitly labeled comparison job rather than an automatic fallback, so generated data provenance stays clean.
- The planned pilot gate is at least 65% pass rate before full synthesis.
- Canonical synthesized responses use `<reasoning>`, not `<think>`.
- The `<reasoning>` block is an auditable rationale with linked IDs: evidence (`E1`), analysis (`A1 [uses E1]`), conclusions (`C1 [uses E1,A1]`), and caveats (`CV1 [applies_to C1]`).
- Prompting should require source-grounded evidence, confidence labels, explicit caveats, uncertainty calibration, and final answers that do not introduce claims absent from linked conclusions.
- A model-specific packaging exporter may convert `<reasoning>` to `<think>` for GLM training only if the training recipe requires that exact tag. The canonical synthesized and packaged dataset remains `<reasoning>`.
- Pair counts are source-richness aware: documents under 250 words generate one pair, and thin content types such as artifact definitions, event dictionaries, and abuse database entries are capped to avoid padded hallucinations.
- Prompting uses a two-layer source model: broad `source_type` instructions from the collector source plus selective exact `content_type` overrides from each raw document.
- Do not create a separate prompt file for every raw `content_type` by default. Add content-type templates only when the generation behavior differs materially from the broad source type.

## Training And Hosting

- Dataset hosting is local-only on DGX Sparks storage, not HuggingFace Hub, unless this decision changes.
- Training is planned as LoRA SFT via Unsloth on GLM-4.7-Flash.
- Baseline evaluation must run before fine-tuning, including AI/LLM-specific ATLAS cases.
