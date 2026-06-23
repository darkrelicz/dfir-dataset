# TODO

## Immediate

- Rerun the full collector orchestrator so `data/raw/collection_manifest.json` reflects all 16 collectors, not just the latest single-source run.
- Validate all generated JSONL files against `RawDocument`.
- Check global `doc_id` uniqueness across all collected sources.
- Reconcile `configs/synthesis.yaml` source keys with actual collector/config source names before Phase 3.
- Decide whether to update `configs/synthesis.yaml` pair targets using current raw counts, since the collected corpus is larger than the plan estimate.

## Phase 3 Preparation

- Create a `synthesizers/` package for instruction-pair generation.
- Add strict schemas for synthesized instruction pairs and generation manifests.
- Add prompt templates by task category and source type.
- Build a pilot sampler that covers source type, document richness, taxonomy area, and known thin-source risks.
- Add dry-run prompt generation before any paid model calls.
- Require collection validation before full synthesis runs.
- Run the planned pilot across all source types and review 100% of pilot output before full generation.

## Later

- Implement automated quality filters for grounding, taxonomy validity, duplicate pairs, and scoring.
- Package filtered datasets for fine-tuning.
- Add evaluation fixtures and baseline evaluation before training.
- Add tests for collectors and synthesis utilities.
