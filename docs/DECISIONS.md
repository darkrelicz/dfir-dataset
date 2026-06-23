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
- Gemini 2.5 Flash is the selected primary teacher model. Claude Sonnet is fallback/comparison only if pilot quality is below threshold.
- The planned pilot gate is at least 65% pass rate before full synthesis.
- Prompting should require source-grounded evidence, confidence labels, explicit caveats, and uncertainty calibration.
- The plan currently packages reasoning inside the assistant response using `<think>` tags; if this is changed later, update synthesis prompts, packaging docs, and this decision log together.

## Training And Hosting

- Dataset hosting is local-only on DGX Sparks storage, not HuggingFace Hub, unless this decision changes.
- Training is planned as LoRA SFT via Unsloth on GLM-4.7-Flash.
- Baseline evaluation must run before fine-tuning, including AI/LLM-specific ATLAS cases.
