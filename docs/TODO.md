# TODO

## Immediate

- Review `data/quality/gemini_subset_1/review_queue.jsonl` before packaging, prioritizing unsupported claims, invented indicators, mapping inconsistencies, weak source specificity, and low operational value.
- Review the 100-row manual sample at `data/quality/gemini_subset_1/manual_spot_check_sample.jsonl` and record pass/fail notes.
- Tune Phase 4 thresholds in `configs/quality.yaml` only after reviewing concrete false positives and false negatives from the current subset.
- Rerun Phase 4 quality filtering with `--log-level INFO` only after threshold or code changes.
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

- Keep Phase 4 independent from Phase 3 generated-output validators. Implemented in `quality/`.
- Deterministic checks for schema, source provenance, taxonomy validity, reasoning-link integrity, ATT&CK/ATLAS ID validity, tool names, invented indicators, and final-answer consistency are implemented. Review/tune them only after examining false positives.
- Heuristic quality scoring for grounding, specificity, reasoning strength, caveat quality, operational usefulness, source balance, difficulty balance, and taxonomy coverage is implemented. Tune thresholds after reviewing the subset run.
- Review unsupported-claim cases where a response claims `source_only` but uses domain knowledge without an explicit `[GENERAL KNOWLEDGE]` tag. Current code sends broad claim terms absent from the source to `review_queue.jsonl`.
- Near-duplicate detection, source/category/difficulty/tactic/taxonomy audits, and manual spot-check sampling are implemented; tune thresholds in `configs/quality.yaml` after reviewing the subset run.
- `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, `manual_spot_check_sample.jsonl`, and `quality_manifest.json` are implemented via `scripts/quality_filter.py`.
- Stage-level quality logs are implemented; keep `--log-level INFO` for long runs unless quiet output is explicitly needed.
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
