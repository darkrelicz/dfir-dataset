# TODO

## Immediate

- Decide whether to update `configs/synthesis.yaml` pair targets using current raw counts, since the collected corpus is larger than the plan estimate.

## Phase 3 Preparation

- Review dry-run pilot prompts for prompt quality, source truncation behavior, and category fit.
- Review the first content-type prompt overrides for `atomic_test`, LOLBAS/GTFOBins, Hayabusa, event dictionaries, tool modules/plugins, and Velociraptor artifacts.
- Add model client abstraction for direct Gemini API access through `google-genai` and `GEMINI_API_KEY`.
- Make any Claude or alternate-model comparison run as a separate labeled job, not an automatic fallback.
- Integrate generated-pair rejection gates into the model runner before writing `data/synthesized/`.
- Add retry, rate-limit, batch checkpoint, and generation manifest handling for real synthesis runs.
- Extend pilot sampling if manual review shows gaps in taxonomy/category coverage.
- Make full synthesis refuse to run unless raw corpus validation passes.
- Run the planned pilot across all source types and review 100% of pilot output before full generation.

## Later

- Implement automated quality filters for grounding, taxonomy validity, reasoning-link integrity, duplicate pairs, and scoring.
- Package filtered datasets for fine-tuning.
- Add evaluation fixtures and baseline evaluation before training.
- Add tests for collectors and synthesis utilities.
