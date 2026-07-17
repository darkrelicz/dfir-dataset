# TODO

## Immediate

- Finish reviewing the 68 tracked benchmark cases under `evaluation/benchmark/` and record the review owner/date.
- Treat the completed `data/evaluation/glm47-flash-base/` run and its 0.7588 overall score as exploratory because its scorecard says `judge_calibration_id: uncalibrated`; do not compare it as a final baseline.
- Build and adjudicate a stratified human-scored calibration set, assign a non-placeholder `calibration_id`, freeze the judge configuration, and rerun complete calibrated base and tuned evaluations before comparison or integration.
- Enforce the calibration policy in `evaluation.comparison`: reject placeholder IDs such as `uncalibrated`, not only missing or mismatched values.
- Add fingerprint-safe evaluation resume support; current atomic checkpoints preserve completed cases but a rerun starts from case one and may overwrite the same run directory.
- Add configurable retry/failure behavior for empty target `content`; the current client only warns and passes the empty answer to the judge.
- Preserve `train-20260714T025314Z` for failure analysis, but mark its adapter and GGUF as rejected: direct-adapter and Web UI smoke tests looped, emitted role/template tokens, and failed to emit EOS.
- Complete the v2 LoRA retraining with `configs/finetune_glm47flash_v2.yaml`, then run a bounded direct-adapter `hello` smoke test. Require `EOS generated: True` before GGUF promotion or benchmark evaluation.
- Record the actual v2 GGUF output path, package/runtime versions, artifact hashes, validation metrics, and selected checkpoint after training completes.
- Treat full review-queue adjudication and manual spot-check completion as deferred quality hardening unless the timeline expands.

## Phase 3 Synthesis

- Current status: complete for the shortened-timeline reduced subset and for the GLM-specific v2 training view.
- Preserve `data/synthesized/gemini_subset_1/prompts.jsonl`, `raw_outputs.jsonl`, `accepted.jsonl`, `rejected.jsonl`, and `generation_manifest.json` for audit and retry analysis.
- Current subset output: 6,494 prompts, 6,287 accepted candidate pairs, 206 rejected prompt rows, and 7,779 raw output rows for `run-20260701T021807Z`.
- Treat Phase 3 `accepted.jsonl` as candidate synthesis output, not final training data.
- Make any Claude or alternate-model comparison run as a separate labeled job, not an automatic fallback.
- Add broader rate-limit orchestration or concurrency only if future generation runs require it.

## Deferred Full-Corpus Generation

- Leave full-corpus Gemini generation to the successor or a future budget window unless the current timeline changes.
- Before any future full-corpus run, rerun a one-prompt smoke test and a reviewed pilot with the then-current prompts, compactors, validators, and configs.
- Use `--skip-present` when resuming interrupted or high-demand Gemini runs, since raw output alone is not terminal and accepted/rejected rows are keyed by prompt hash and model.

## Phase 4 Quality

- Current status: complete for the shortened-timeline reduced subset by time-boxed acceptance. Hard rejects remain excluded; review rows are allowed into Phase 5 with quality provenance.
- Keep Phase 4 independent as a stage while sharing pure validation primitives from `validation/`. Implemented in `quality/` with separate Phase 4 policy wrappers.
- Deterministic checks for schema, source provenance, taxonomy validity, reasoning-link integrity, ATT&CK/ATLAS ID validity, tool names, invented indicators, and final-answer consistency are implemented. Review/tune them only after examining false positives.
- Heuristic quality scoring is config-driven and no-API: task-category `quality_signals` live in `configs/task_categories.yaml`, while generic-answer penalties and operational verbs live in `configs/quality.yaml`. Row status is driven by deterministic reject/review issue severity, plus dataset gates for dedupe and source balance; scores rank duplicate retention and source-balance review choices.
- Near-duplicate detection, source/category/difficulty/taxonomy audits, and manual spot-check sampling are implemented; tune scoring signals and dedupe/balance thresholds after reviewing the subset run.
- `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, `manual_spot_check_sample.jsonl`, and `quality_manifest.json` are implemented via `scripts/quality_filter.py`.
- Stage-level quality logs are implemented at INFO by default.
- Use AI-assisted judging and manual review for fuzzy quality issues such as weak reasoning or unsupported claims if time permits; for the current deadline, these concerns are carried forward through `quality_status` and `quality_issues`.

## Phase 5 Packaging

- Current status: complete for the shortened-timeline reduced subset.
- `scripts/package_dataset.py` packages Phase 4 filtered plus review rows into GLM-friendly local train/validation/test chat JSONL.
- Phase 4 rejected rows are excluded from all packaged splits.
- Splits are grouped by `source_doc_id` to avoid train/validation/test leakage.
- Canonical synthesis/quality rows retain `<reasoning>` and grounding annotations. The GLM v2 training view removes `[GENERAL KNOWLEDGE]`, converts reasoning rows to `<think>`, and strips reasoning from review rows.
- `data/packaged/glm47_dfir_v2/` has 5,517 records: 4,414 train, 552 validation, and 551 test, with no leaked annotations/canonical tags, no unbalanced `<think>` blocks, and no split overlap.
- `packaging_manifest.json` records package run ID, quality run ID, total records, response-style mix, split counts, and source-document overlap.
- Hugging Face upload work is intentionally not implemented for the current local training path.

## Phase 6 Training And Evaluation

- Current status: v1 training completed but its adapter/GGUF is invalid because it loops and does not emit EOS. The v2 package and runner fixes are complete; v2 training is pending. The uncalibrated base-model evaluation under `data/evaluation/glm47-flash-base/` completed 68/68 cases at 0.7588 and remains diagnostic only.
- `configs/evaluation.yaml` requires a separate local OpenAI-compatible judge endpoint. The former statistical evaluator modes and scorecard have been removed.
- `scripts/finetune.py` and `configs/finetune_glm47flash_v2.yaml` provide the active local DGX/Unsloth LoRA SFT path. Unsloth must import before TRL/Transformers so its fused-loss trainer patch is installed.
- Calibrate and freeze the judge, then run complete base and tuned evaluations. An `in_progress` or `uncalibrated` manifest does not satisfy the comparison gate.
- Do not evaluate or promote the v1 tuned artifact. Every training run saves a GGUF, but only an EOS-terminating adapter makes that GGUF eligible for promotion and calibrated comparison.
- Run post-training evaluation with the same benchmark and frozen judge, then compare with `scripts/compare_evaluations.py`.
- Integrate into Shepherd only if the reviewed judge scorecard improves without unacceptable task-level or critical-behavior regressions.

## Later

- Expand Phase 6 benchmark coverage after the initial reviewed benchmark is stable.
- Add tests for collectors and synthesis utilities.
- Keep `docs/` synchronized with code, durable project state docs, and generated manifests when pipeline architecture, commands, decisions, or artifact paths change.
- Update `docs/site.json` `baseUrl` if the GitHub Pages repository name or hosting shape changes from `/dfir-dataset`.
