# TODO

## Immediate

- Finalize and manually review the tracked benchmark files under `evaluation/benchmark/` before any baseline or tuned-model scoring.
- Run independent statistical and local-judge baseline scorecards with `scripts/run_evaluation.py --evaluator both` before LoRA SFT.
- Use `data/packaged/gemini_subset_1/train.jsonl`, `validation.jsonl`, and `test.jsonl` as the current local Unsloth SFT inputs.
- Record the exact Unsloth/GLM training configuration, checkpoint paths, and evaluation results once training starts.
- Treat full review-queue adjudication and manual spot-check completion as deferred quality hardening unless the timeline expands.

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
- Filtered rows keep canonical `<reasoning>` responses; review rows are transformed into direct-answer examples by stripping the reasoning block.
- The current package has 5,517 records: 4,414 train, 552 validation, and 551 test.
- `packaging_manifest.json` records package run ID, quality run ID, total records, response-style mix, split counts, and source-document overlap.
- Hugging Face dataset-card and upload work are intentionally not implemented for the current local training path.

## Phase 6 Training And Evaluation

- Current status: evaluator implementation complete pending reviewed baseline execution. `evaluation/` implements typed deterministic metrics, local LLM judging, structured outputs for objective tasks, prediction replay, independent scorecards, benchmark fingerprints, and guarded baseline-vs-tuned comparison.
- `configs/evaluation.yaml` keeps `statistical` as the default evaluator and configures an optional separate local OpenAI-compatible judge endpoint. `both` writes independent scorecards without a composite score.
- `scripts/finetune.py` and `configs/finetune_glm47flash.yaml` provide the local DGX/Unsloth LoRA SFT runner.
- Run baseline evaluation before fine-tuning.
- Fine-tune GLM-4.7-Flash with LoRA SFT via Unsloth after the baseline manifest exists.
- Run post-training evaluation with the same benchmark and compare each scorecard independently with `scripts/compare_evaluations.py --evaluator <name>`.
- Integrate into Shepherd only if both reviewed scorecards improve without unacceptable task-level or critical-behavior regressions.

## Later

- Expand Phase 6 benchmark coverage after the initial reviewed benchmark is stable.
- Add tests for collectors and synthesis utilities.
- Keep `docs/` synchronized with code, durable project state docs, and generated manifests when pipeline architecture, commands, decisions, or artifact paths change.
- Update `docs/site.json` `baseUrl` if the GitHub Pages repository name or hosting shape changes from `/dfir-dataset`.
