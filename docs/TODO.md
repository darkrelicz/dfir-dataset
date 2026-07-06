# TODO

## Immediate

- Review `data/quality/gemini_subset_1/review_queue.jsonl` before packaging, prioritizing unsupported claims, invented indicators, mapping inconsistencies, weak source specificity, and low operational value.
- Review the 100-row manual sample at `data/quality/gemini_subset_1/manual_spot_check_sample.jsonl` and record pass/fail notes.
- Tune Phase 4 scoring signals, generic penalties, operational verbs, and dedupe/balance thresholds only after reviewing concrete false positives and false negatives from the current subset.
- Rerun Phase 4 quality filtering after the current heuristic scoring changes so `quality_score`, duplicate retention ranking, source-balance review ranking, and `quality_manifest.json` reflect the new config-driven policy.
- Start Phase 5 packaging from Phase 4 `filtered.jsonl`, never from Phase 3 `accepted.jsonl`.
- Prepare the Phase 6 baseline evaluation set before LoRA SFT.

## Phase 3 Synthesis

- Current status: complete for the shortened-timeline reduced subset.
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

- Keep Phase 4 independent as a stage while sharing pure validation primitives from `validation/`. Implemented in `quality/` with separate Phase 4 policy wrappers.
- Deterministic checks for schema, source provenance, taxonomy validity, reasoning-link integrity, ATT&CK/ATLAS ID validity, tool names, invented indicators, and final-answer consistency are implemented. Review/tune them only after examining false positives.
- Heuristic quality scoring is config-driven and no-API: task-category `quality_signals` live in `configs/task_categories.yaml`, while generic-answer penalties and operational verbs live in `configs/quality.yaml`. Row status is driven by deterministic reject/review issue severity, plus dataset gates for dedupe and source balance; scores rank duplicate retention and source-balance review choices.
- Review unsupported-claim cases manually or with an AI judge where a response appears to use domain knowledge without sufficient source support.
- Near-duplicate detection, source/category/difficulty/taxonomy audits, and manual spot-check sampling are implemented; tune scoring signals and dedupe/balance thresholds after reviewing the subset run.
- `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, `manual_spot_check_sample.jsonl`, and `quality_manifest.json` are implemented via `scripts/quality_filter.py`.
- Stage-level quality logs are implemented at INFO by default.
- Use AI-assisted judging and manual review for fuzzy quality issues such as weak reasoning or unsupported claims, not as the only quality gate.

## Phase 5 Packaging

- Split by `source_doc_id` to avoid leakage.
- Package Phase 4 filtered pairs into GLM-friendly train/validation/test JSONL.
- Keep canonical `<reasoning>` and add a GLM-specific `<think>` exporter only if the training recipe requires it.
- Write packaging manifests with source, category, difficulty, and taxonomy distributions.

## Phase 6 Training And Evaluation

- Run baseline evaluation before fine-tuning.
- Fine-tune GLM-4.7-Flash with LoRA SFT via Unsloth.
- Run post-training evaluation and compare against baseline.
- Integrate into Shepherd only if evaluation shows improvement.

## Later

- Add evaluation fixtures and baseline evaluation before training.
- Add tests for collectors and synthesis utilities.
