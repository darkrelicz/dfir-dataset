# TODO

## Immediate

- Regenerate `data/synthesized/dry_run/prompts.jsonl` after prompt compactor and taxonomy-ref changes.
- Inspect dry-run prompts for CISA advisories and confirm compacted source views still preserve enough evidence for grounded answers.
- Inspect large Velociraptor prompts separately; query bodies intentionally bypass shared source truncation, so cost control should come from sampling or pair caps rather than capping VQL.
- Decide the next source compactors based on prompt-size outliers. Current high-value candidates are selected large rule/artifact sources.
- Decide whether to update `configs/synthesis.yaml` pair targets using current raw counts, since the collected corpus is larger than the plan estimate.
- Complete or rerun `data/synthesized/gemini_pilot_8/` after the latest grounding/tag validator update, then compare rejection categories against pilot 7.

## Phase 3 Pilot

- Review dry-run pilot prompts for prompt quality, prompt-time compaction behavior, source truncation behavior, taxonomy refs, and category fit.
- Review the CISA advisory compactor output before using pilot prompt size as a full-synthesis cost estimate.
- Review the first content-type prompt overrides for `atomic_test`, LOLBAS/GTFOBins, Hayabusa, event dictionaries, tool modules/plugins, and Velociraptor artifacts.
- Run a one-prompt Gemini smoke test and inspect `accepted.jsonl`, `rejected.jsonl`, and `raw_outputs.jsonl`.
- Confirm the rejection-rate circuit breaker threshold is appropriate for the pilot before full generation.
- Run the planned Gemini pilot across all source types and review 100% of pilot output before full generation.
- During pilot review, explicitly sample `source_only` answers for untagged general-knowledge claims that deterministic validators cannot prove.
- Make any Claude or alternate-model comparison run as a separate labeled job, not an automatic fallback.
- Add broader rate-limit orchestration or concurrency only after the sequential Gemini pilot is healthy.
- Extend pilot sampling if manual review shows gaps in taxonomy/category coverage.

## Phase 3 Full Generation

- Start full Gemini generation only after the pilot has acceptable validator pass rate and manual quality.
- Treat Phase 3 `accepted.jsonl` as candidate synthesis output, not final training data.
- Preserve `prompts.jsonl`, `raw_outputs.jsonl`, `rejected.jsonl`, and `generation_manifest.json` for audit and retry analysis.
- Use `--skip-present` when resuming interrupted or high-demand Gemini runs, since raw output alone is not terminal and accepted/rejected rows are keyed by prompt hash and model.

## Phase 4 Quality

- Reuse Phase 3 validator logic where appropriate, then implement Phase 4 dataset-level deterministic checks for schema, source provenance, taxonomy validity, reasoning-link integrity, ATT&CK/ATLAS ID format, invented indicators, and final-answer consistency.
- Add heuristic quality scoring for grounding, specificity, reasoning strength, caveat quality, operational usefulness, source balance, difficulty balance, and taxonomy coverage.
- Add unsupported-claim review for cases where a response claims `source_only` but uses domain knowledge without an explicit `[GENERAL KNOWLEDGE]` tag.
- Add near-duplicate detection and overrepresented-source/category audits.
- Create `filtered.jsonl`, `review_queue.jsonl`, `rejected.jsonl`, and `quality_manifest.json`.
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
