# Project Brief

## Purpose

Build a re-runnable DFIR dataset factory for Shepherd, a local/on-premise digital forensics and incident response AI investigation assistant. The pipeline collects public cybersecurity and forensic sources, normalizes them into a common raw document schema, synthesizes instruction-response pairs, quality-filters them, and packages the result for fine-tuning Shepherd's reasoning layer.

## Context

The intended handoff is a documented, reproducible dataset factory that a successor can rerun and extend for real Shepherd operations.

The fine-tuning target in the plan is LoRA SFT via Unsloth on DGX Sparks using GLM-4.7-Flash as the base model. CRAFT/RAFT is deferred until Shepherd has a RAG layer.

## Product Goal

The target output is not a one-off dataset. It is a reproducible pipeline that a future maintainer can re-run, extend with new sources, audit, and use to regenerate training data as Shepherd evolves.

## Documentation Roles

Operational project memory lives in `PROJECT_BRIEF.md`, `TODO.md`, `DECISIONS.md`, and `DESIGN_SYSTEM.md`. These files carry product intent, current phase state, durable decisions, active work, and presentation rules.

The Markdown source under `docs/` is canonical for stable successor guidance: architecture, handover, source onboarding, prompt design, quality, coverage, taxonomy, training, release gates, and reusable templates. Do not duplicate that prose in `project_state/`. Current run counts and artifact facts remain canonical in generated manifests and are summarized in `docs/current-state/`.

## Current Scope

The selected dataset scope is Core + Tier 1 + Tier 2: all 16 collectors from the plan (C1-C7 and AF1-AF9). Tier 3 and semi-structured/unstructured sources are deferred to the successor.

- Phase 1: DFIR artifact taxonomy and task taxonomy.
- Phase 2: raw source collection into JSONL.
- Phase 3: budget-aware reduced-subset synthesis is complete for the current timeline. `data/synthesized/gemini_subset_1/` contains 6,494 prompts, 6,287 accepted candidate pairs, 206 rejected prompt rows, raw outputs, and a generation manifest for `run-20260701T021807Z`. Full-corpus synthesis is deferred.
- Phase 4: complete for the shortened-timeline reduced subset. Quality filtering has run against the completed reduced subset with the no-API heuristic scoring policy; unresolved review rows are accepted into Phase 5 by explicit time-boxed decision, while rejected rows remain excluded.
- Phase 5: complete for the current reduced subset. The historical generic package remains under `data/packaged/gemini_subset_1/`. The active GLM-specific training view is `package-20260716T053818Z` under `data/packaged/glm47_dfir_v2/`; it keeps the same 5,517 eligible records and splits while removing training-only `[GENERAL KNOWLEDGE]` annotations and converting canonical `<reasoning>` blocks to GLM-native `<think>` blocks. Canonical synthesis and quality outputs remain unchanged.
- Phase 6: evaluator and training-runner implementation is complete. The first LoRA run, `train-20260714T025314Z`, completed one epoch/552 steps but failed post-training termination smoke tests: both the GGUF and direct LoRA adapter repeated content and role tokens and did not emit EOS within a 256-token `hello` test. Treat its adapter/GGUF as rejected diagnostic artifacts, not a tuned release candidate. A v2 retraining run is prepared against `data/packaged/glm47_dfir_v2/` with the original LoRA hyperparameters, explicit EOS-terminated rendering, preflight length checks, and corrected manifest serialization; it is not yet complete. The 68 held-out cases live under `evaluation/benchmark/`. The base-model run `data/evaluation/glm47-flash-base/` completed 68/68 cases with an exploratory overall score of 0.7588, but its `judge_calibration_id` is `uncalibrated`.

## Remaining Workflow

Phase 3 has completed the current budget-aware subset run rather than the older full-corpus plan. Phase 3 writes `accepted.jsonl`, but that file is only a candidate synthesis output, not final training data. Current validators catch structural failures, malformed technique IDs, invented concrete indicators, grounding/tag mismatches, and broken canonical reasoning links; semantic unsupported-claim review belongs in Phase 4 and manual review. Any future full-corpus generation should reuse the same smoke/pilot discipline before spending the larger budget.

Prompt cost is reduced at prompt time, not by shortening the collected raw corpus. Source-specific compactors live under `synthesizers/prompts/compactors/`; current implemented compactors cover `cisa_advisories`, `cisa_kev`, `mitre_attack`, `cybersec_skills`, `velociraptor_artifacts`, `loldrivers`, and `hijacklibs`.

Phase 4 consumes Phase 3 `accepted.jsonl` and applies deterministic validators, config-driven heuristic quality scores, deduplication, balance checks, and targeted manual or AI-assisted review. It does not call Phase 3's generated-output validators, but both stages now share pure primitives from `validation/` for reasoning, grounding, concrete indicators, mapping ID formats, and taxonomy config extraction. Heuristic scoring is no-API and currently uses task-category `quality_signals`, task descriptions, generic-answer penalty terms, operational verbs, tiered source-token overlap, concrete artifact counts, and response-length tiers. It writes `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, `manual_spot_check_sample.jsonl`, and `quality_manifest.json` under `data/quality/<run>/`. The quality CLI logs each major sub-stage by default so long runs show progress through reference loading, row validation, dataset audits, output writing, and manifest creation.

The current reduced-pair quality snapshot is `data/quality/gemini_subset_1/`, generated by `quality-20260708T064057Z`: 6,287 Phase 3 candidate pairs were checked, with 4,152 filtered, 1,365 routed to review, 770 rejected, and 100 filtered rows sampled for manual spot-check. These numbers are intentionally below the older full-synthesis `10k-15k` target because the project is now using a budget-aware representative subset. For the current deadline, the Phase 5 package-eligible set is 5,517 pairs: all filtered rows plus review rows. Rejected rows remain ineligible.

Phase 5 consumes the Phase 4 package-eligible dataset, splits by `source_doc_id`, and packages examples into chat/SFT JSONL. The active GLM training view is `package-20260716T053818Z` under `data/packaged/glm47_dfir_v2/`: 5,517 records split into 4,414 train, 552 validation, and 551 test rows, with no `source_doc_id` overlap. It preserves the 4,152 reasoning / 1,365 direct-answer policy, but the GLM-only exporter removes `[GENERAL KNOWLEDGE]` markers from assistant text and maps `<reasoning>` to `<think>`. Its preflight rejects empty responses, retained annotations/canonical tags, and unbalanced GLM tags. The historical generic package remains preserved for provenance.

Phase 6 has a complete exploratory base scorecard but no valid tuned artifact or calibrated comparison. The v1 tuned artifact failed the mandatory EOS/termination smoke gate. The next sequence is: complete v2 training, require short-prompt EOS termination from the direct adapter before GGUF promotion, then calibrate the judge and produce new complete base/tuned scorecards. The evaluator processes one case at a time and atomically checkpoints outputs after every successful verdict. Shepherd integration remains blocked until the v2 artifact passes smoke tests and the calibrated comparison shows improvement without unacceptable regressions.


## Intended Users

- The internship/project owner building the initial dataset factory.
- A future full-time maintainer who will expand sources and rerun the pipeline.
- Shepherd developers who will consume the resulting fine-tuning dataset.

## Success Criteria

- Collectors are reproducible and produce valid `RawDocument` JSONL.
- Source coverage maps cleanly to the documented DFIR taxonomy and task categories.
- Instruction pairs are grounded in source evidence, cite artifacts or source details, and calibrate uncertainty.
- Reduced-subset synthesis artifacts are preserved, pass Phase 4 hard rejection gates, and carry quality-status provenance into packaging.
- Quality filters exclude hard-invalid examples and preserve review-risk metadata for time-boxed rows carried into packaging.
- Project state, the documentation source, and generated manifests preserve enough current context for future coding sessions without relying on chat history.
