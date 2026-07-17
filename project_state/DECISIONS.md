# Decisions

This file records durable choices and accepted constraints. Current run status belongs in `PROJECT_BRIEF.md` and `TODO.md`; implementation guidance belongs in `docs/`.

## Project Shape And State

- This repository is a re-runnable Python dataset pipeline
- Operational state lives in `project_state/`; stable architecture and operating guidance live in the MarkBind source under `docs/`. Generated manifests are authoritative for run-specific facts.
- Shared `utils/` code remains low-level and domain-neutral. Source-specific parsing stays with collectors or synthesizer modules.
- Dataset and model hosting remain local to DGX storage. Hugging Face publishing is deferred unless this decision changes.

## Scope And Data Contracts

- The selected source scope is Core + Tier 1 + Tier 2: all 16 collectors C1-C7 and AF1-AF9. Tier 3 and broader unstructured sources are deferred.
- Collectors normalize source material into the shared `RawDocument` schema and preserve complete raw content for provenance and reprocessing.
- The artifact taxonomy remains broader than current source coverage. The five training behaviors are artifact analysis, TTP identification, triage and hunting, detection engineering, and incident report generation.
- Human-readable taxonomy guidance lives in `docs/reference/taxonomy.md`; machine validation and scoring policy live in `configs/quality.yaml`; generation behavior targets live in `configs/task_categories.yaml`.

## Synthesis

- Gemini 2.5 Flash through the direct Google GenAI API is the canonical teacher. Alternate teachers run as separately labeled comparison jobs, never automatic fallbacks.
- Secrets stay in `.env` or the process environment and are never committed.
- Raw documents collected in collectors phase remain complete. Prompt-cost reduction happens only in the synthesis stage through source-aware planning and prompt-time compactors.
- Prompt planning, category balancing, and difficulty assignment belong in `synthesizers/planner.py`; prompt-policy parsing and asset preflight belong in `synthesizers/prompt_policy.py`; CLIs remain thin dispatchers.
- Canonical responses use linked `<reasoning>` blocks and explicit grounding provenance. Model-specific tags such as `<think>` are export-time views only.
- Data synthesis stage rejects structural and deterministic grounding failures inline and writes complete provenance/manifests. Its `accepted.jsonl` remains candidate data until quality validation stage.
- Full-corpus synthesis is deferred. Any future full run requires a fresh smoke test and reviewed pilot.

## Quality And Packaging

- Quality validation stage remains a separate deterministic/heuristic quality filter while sharing pure validation primitives with data synthesis stage. Manual review handles fuzzy semantic judgments. AI-assisted reviews are deferred for now.
- Only `filtered.jsonl` is eligible for active packaging. Review and rejected rows are excluded until adjudicated.
- Data packaging stage rejects any input row not marked `quality_status: filtered` and splits by `source_doc_id` to prevent train/validation/test leakage.
- The active GLM view deterministically derives a 75% reasoning / 25% direct mix using the configured seed. Direct examples strip canonical reasoning; retained reasoning maps to `<think>`; `[GENERAL KNOWLEDGE]` annotations are removed. Data from synthesis and quality validation stages are not mutated.
- Data packaging stage is named `dataset_packaging/` to avoid shadowing Python's third-party `packaging` module.

## Training And Evaluation

- Training uses 4-bit-loaded GLM-4.7-Flash with Unsloth LoRA SFT. Unsloth must import before TRL/Transformers so its fused-loss patches are installed.
- A completed optimizer run is not releasable. The direct adapter must emit EOS on bounded smoke prompts before GGUF promotion, serving, or evaluation.
- Benchmark cases are derived separately from synthesis/training and require manual review. Future training cycles should establish a calibrated baseline before tuning.
- Evaluation stage uses one separately served local LLM judge. Target generation and judging remain sequential, with atomic checkpoints after every successful verdict.
- Base/tuned comparisons require identical benchmark identity, case IDs, judge model and quantization, protocol, inference settings, and a real calibrated non-placeholder ID. Aggregate gains cannot override material task-level or severe DFIR regressions.
