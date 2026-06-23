# Project Brief

## Purpose

Build a re-runnable DFIR dataset factory for Shepherd, a local/on-premise digital forensics and incident response AI investigation assistant. The pipeline collects public cybersecurity and forensic sources, normalizes them into a common raw document schema, synthesizes instruction-response pairs, quality-filters them, and packages the result for fine-tuning Shepherd's reasoning layer.

## Context

This is Project 1 of the summer internship plan. The intended handoff is a documented, reproducible dataset factory that a successor can rerun and extend for real Shepherd operations.

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

## Current Project Type

Despite occasional references to a website, the current codebase is not a website project. There is no detected web framework, frontend router, styling system, page layout, or reusable UI component library.

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
