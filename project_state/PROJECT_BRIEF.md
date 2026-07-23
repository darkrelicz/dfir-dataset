# Project Brief

## Purpose

Build a reproducible, auditable DFIR dataset factory for Shepherd, a local AI
investigation assistant. The pipeline collects public sources, synthesizes
grounded instruction data, applies quality gates, packages model-specific views,
and supports training and evaluation.

## Scope

- Cover the 16 Core, Tier 1, and Tier 2 sources; defer broader sources.
- Fine-tune GLM-4.7-Flash with Unsloth LoRA SFT on DGX Spark.
- Use the representative Gemini subset; defer full-corpus synthesis.
- Defer CRAFT/RAFT until Shepherd has a RAG layer.

## Current State

- Pipeline tooling is implemented from collection through evaluation.
- Synthesis produced 6,287 candidates; quality retained 4,152 filtered rows.
- `data/packaged/glm47_v3/` contains all filtered rows, split 3,322/415/415 by
  `source_doc_id`, with a 75% reasoning and 25% direct response mix.
- No model is promoted. V5 or staged v6 must be selected as the next candidate,
  and corrected enforcing adapter tests remain pending.
- The 68-case benchmark and existing scores are not yet calibrated release
  evidence.

## Release Gate

- Require bounded direct-adapter termination, repetition, and template-leakage
  checks while preserving `model.generation_config.eos_token_id`.
- Calibrate and freeze the judge, then compare complete base and tuned runs with
  identical benchmark and inference inputs.
- Promote only a candidate with a reviewed improvement and no unacceptable
  task-level or critical-behavior regressions.

## Success Criteria

- The pipeline is reproducible and auditable without chat history.
- Training data is grounded, traceable, filtered-only, and leakage-resistant.
- Run facts are preserved in generated manifests and stable guidance in `docs/`.
- Model promotion requires passing termination and calibrated evaluation gates.
