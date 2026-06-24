# Project Brief

## Purpose

Build a re-runnable DFIR dataset factory for Shepherd, a local/on-premise digital forensics and incident response AI investigation assistant. The pipeline collects public cybersecurity and forensic sources, normalizes them into a common raw document schema, synthesizes instruction-response pairs, quality-filters them, and packages the result for fine-tuning Shepherd's reasoning layer.

## Context

The intended handoff is a documented, reproducible dataset factory that a successor can rerun and extend for real Shepherd operations.

The fine-tuning target in the plan is LoRA SFT via Unsloth on DGX Sparks using GLM-4.7-Flash as the base model. CRAFT/RAFT is deferred until Shepherd has a RAG layer.

## Product Goal

The target output is not a one-off dataset. It is a reproducible pipeline that a future maintainer can re-run, extend with new sources, audit, and use to regenerate training data as Shepherd evolves.

## Current Scope

The selected dataset scope is Core + Tier 1 + Tier 2: all 16 collectors from the plan (C1-C7 and AF1-AF9). Tier 3 and semi-structured/unstructured sources are deferred to the successor.

- Phase 1: DFIR artifact taxonomy and task taxonomy.
- Phase 2: raw source collection into JSONL.
- Phase 3: planned instruction-pair synthesis.
- Phase 4: planned quality filtering, validation, deduplication, and distribution audits.
- Phase 5: planned local dataset packaging.
- Phase 6: planned fine-tuning validation and Shepherd integration.

## Remaining Workflow

Phase 3 proceeds in two gates: first run and manually review a small Gemini pilot, then run full instruction-pair generation only after the pilot has acceptable validator pass rate and manual quality. Phase 3 writes `accepted.jsonl`, but that file is only a candidate synthesis output, not final training data.

Phase 4 consumes Phase 3 `accepted.jsonl` and applies deterministic validators, heuristic quality scores, deduplication, balance checks, and targeted manual or AI-assisted review. Its output should be a filtered dataset plus review/rejection manifests.

Phase 5 consumes the Phase 4 filtered dataset, splits by `source_doc_id`, and packages the examples into GLM-friendly chat/SFT JSONL. The canonical data keeps `<reasoning>`; a model-specific export may convert to `<think>` only if required.

Phase 6 runs baseline evaluation, LoRA SFT on GLM-4.7-Flash, post-training evaluation, and Shepherd integration only if the tuned model improves over baseline.


## Intended Users

- The internship/project owner building the initial dataset factory.
- A future full-time maintainer who will expand sources and rerun the pipeline.
- Shepherd developers who will consume the resulting fine-tuning dataset.

## Success Criteria

- Collectors are reproducible and produce valid `RawDocument` JSONL.
- Source coverage maps cleanly to the documented DFIR taxonomy and task categories.
- Instruction pairs are grounded in source evidence, cite artifacts or source details, and calibrate uncertainty.
- Pilot synthesis reaches the planned quality gate before full generation.
- Quality filters remove low-confidence, duplicated, invalid, or hallucinated examples.
- Documentation preserves enough project state for future coding sessions without relying on chat history.
