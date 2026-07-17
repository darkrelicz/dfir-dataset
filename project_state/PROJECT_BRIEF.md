# Project Brief

## Purpose

Build a reproducible DFIR dataset factory for Shepherd, a local/on-premise AI investigation assistant. The pipeline collects public cybersecurity sources, normalizes them, synthesizes grounded instruction pairs, applies quality gates, and packages training data. The handoff must be auditable and reusable by a future maintainer, not merely produce a one-off dataset.

## Scope

- Collection covers the 16 planned Core, Tier 1, and Tier 2 sources. Tier 3 and less-structured sources are deferred.
- The current target is LoRA SFT of GLM-4.7-Flash with Unsloth on DGX Spark.
- CRAFT/RAFT remains deferred until Shepherd has a RAG layer.
- Full-corpus synthesis is deferred; the current work uses a budget-aware, representative Gemini-generated subset.

## Current State

- Taxonomy, collection, normalization, synthesis, quality filtering, packaging, training, and evaluation tooling are implemented.
- Phase 3 produced 6,287 candidate pairs from 6,494 prompts under `data/synthesized/gemini_subset_1/`.
- Phase 4 produced 4,152 filtered, 1,365 review, and 770 rejected rows under `data/quality/gemini_subset_1/`. Only `quality_status: filtered` is eligible for active packaging.
- The active package is `data/packaged/glm47_v3/`: 4,152 records split into 3,322 train, 415 validation, and 415 test rows by `source_doc_id`. It assigns 75% reasoning and 25% direct responses and maps retained reasoning to GLM `<think>` blocks.
- V1 is rejected because it loops and fails to emit EOS. V2 scored 0.6831 versus the base model's 0.7588 in exploratory evaluation and is not a release candidate. Both scores are uncalibrated and cannot support a final comparison.
- The conservative v3 configuration is ready, but training is pending the `lora_dropout` type fix in `scripts/finetune.py`. The held-out benchmark has 68 cases.

## Release Gate

V3 must pass a bounded direct-adapter EOS smoke test before GGUF promotion. The judge must then be calibrated and frozen before complete base and v3 evaluations are compared. Shepherd integration requires an improved reviewed scorecard with no unacceptable task-level or critical-behavior regressions.

## Project Memory

- `TODO.md` tracks pending work.
- `DECISIONS.md` records durable choices and constraints.
- `DESIGN_SYSTEM.md` defines presentation rules.
- `docs/` contains stable operational guidance.
- Generated manifests are canonical for run IDs, counts, and artifact details.

## Success Criteria

- The pipeline can be rerun, extended, and audited without relying on chat history.
- Training examples remain source-grounded, taxonomy-aligned, and traceable.
- Invalid and unresolved-review examples stay outside active training packages.
- Dataset splits prevent source-document leakage.
- A tuned model is promoted only after termination and calibrated evaluation gates pass.
