# Decisions

Durable choices only. Run status belongs in `PROJECT_BRIEF.md`, pending work in
`TODO.md`, implementation guidance in `docs/`, and run facts in manifests.

## Foundation

- Build a reproducible Python dataset pipeline with thin CLIs and domain-neutral shared utilities.
- Keep operational memory in `project_state/` and stable guidance in `docs/`.
- Keep datasets and models on local DGX storage; Hugging Face publishing remains deferred.
- Limit collection to the 16 Core, Tier 1, and Tier 2 sources; defer broader sources.

## Data Pipeline

- Preserve complete `RawDocument` content and provenance; reduce prompt cost only during synthesis.
- Use Gemini 2.5 Flash through the Google GenAI API as the canonical teacher; label alternate-teacher runs separately.
- Keep canonical responses model-neutral with linked `<reasoning>` and provenance; apply model-specific formats only at export.
- Treat synthesis output as candidate data; package only quality rows marked `filtered`.
- Split packages by `source_doc_id` to prevent train/validation/test leakage.
- Produce the GLM view deterministically as 75% reasoning and 25% direct without mutating upstream artifacts.
- Keep the implementation named `dataset_packaging/` to avoid shadowing Python's `packaging` module.

## Training And Release

- Train GLM-4.7-Flash with 4-bit Unsloth LoRA SFT; import Unsloth before TRL/Transformers.
- Preserve the model-defined stop-token list; never replace it with scalar `tokenizer.eos_token_id`.
- Require a bounded direct-adapter termination and behavior gate before promotion, serving, or evaluation.
- Keep benchmark cases separate from training data and manually review them.
- Use one separately served local LLM judge; calibrate and freeze it before comparison.
- Compare base and tuned models only with identical benchmark, target inputs, judge, inference settings, and a real calibration ID.
- Do not allow aggregate gains to override material task-level or severe DFIR regressions.
