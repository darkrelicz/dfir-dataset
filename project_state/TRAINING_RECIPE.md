# Training Recipe

## Purpose

Document the exact training and evaluation procedure used for Shepherd fine-tuning. This document should make the run reproducible and make before/after quality claims auditable.

## Current Run Summary

- Run ID: `train-20260714T025314Z`
- Date: 2026-07-14
- Owner:
- Training machine: DGX Sparks; exact host details were not recorded in the manifest
- Base model: `unsloth/GLM-4.7-Flash`
- Dataset version: `package-20260708T071253Z`
- Code commit: not recorded in the manifest
- Baseline evaluation run: `glm47-flash-base` (exploratory only; rerun after calibration)
- Judge model/quantization: `gemma-4-31B-it-Q4_K_M.gguf`
- Judge protocol/config fingerprint: `phase6-judge-v2-acceptable-variants` / `52b3f0be829335ea19c43d8558f01c335c2a077ba8591a3b4db7d3a1238fa4d0`
- Judge calibration ID: `uncalibrated`
- Output adapter path: `data/finetune/glm47_flash_subset1/lora_adapter`
- GGUF/export path: `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf`

## Dataset Inputs

| Input | Path | Records | Notes |
|---|---|---:|---|
| Train | `data/packaged/gemini_subset_1/train.jsonl` | 4,414 | Grouped by `source_doc_id` |
| Validation | `data/packaged/gemini_subset_1/validation.jsonl` | 552 | No source-document overlap |
| Test | `data/packaged/gemini_subset_1/test.jsonl` | 551 | No source-document overlap |
| Dataset card | `project_state/DATASET_CARD.md` |  | Reusable template; run-specific card not yet filled |
| Packaging manifest | `data/packaged/gemini_subset_1/packaging_manifest.json` | 5,517 | `package-20260708T071253Z` |

## Environment

```bash
python --version
nvidia-smi
pip freeze > training_freeze.txt
```

Record:

- OS:
- CUDA version:
- Python version:
- Unsloth version:
- Transformers version:
- GPU/accelerator:
- Available memory:

## Baseline Evaluation

For future training runs, complete baseline evaluation before fine-tuning. The
first run (`train-20260714T025314Z`) completed before a calibrated baseline, so
its base and tuned artifacts require retrospective evaluation with the same
frozen calibrated judge before any improvement claim.

Default command for generating and judging through the configured local
OpenAI-compatible endpoints:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <baseline_run> \
  --model-label glm47_flash_base
```

The evaluator always uses the separately configured local judge under
`scoring.judge`. To score an existing prediction JSONL instead, use
`--mode prediction_file --predictions <path>`. Freeze the judge model,
quantization, prompt, inference settings, and non-placeholder `calibration_id`
before producing baseline and tuned scorecards; the comparison command rejects
drift in these fields.

Every successful verdict atomically refreshes `predictions.jsonl`,
`scorecards/llm_judge/case_results.jsonl`, `scorecards/llm_judge/scores.json`,
and `evaluation_manifest.json`. Do not treat an `in_progress` checkpoint as the
baseline gate. A scorecard labeled `uncalibrated` is exploratory even if its run
status is `complete`.

The completed `glm47-flash-base` run is recorded below for diagnostics. These
are not calibrated baseline values.

| Benchmark | Cases | Metric | Exploratory Score | Notes |
|---|---:|---|---:|---|
| TTP identification | 10 | LLM judge: label selection and evidence | 0.5100 | Uncalibrated |
| IOC extraction | 10 | LLM judge: indicator correctness/completeness | 0.7000 | Uncalibrated |
| Triage ranking | 8 | LLM judge: ranking and rationale | 0.8750 | Uncalibrated |
| Detection interpretation | 10 | LLM judge: rubric accuracy | 0.9600 | Uncalibrated |
| Forensic artifact analysis | 8 | LLM judge: rubric accuracy | 0.8750 | Uncalibrated |
| Report quality | 6 | LLM judge: report rubric | 1.0000 | Uncalibrated |
| Reasoning quality | 8 | LLM judge: grounding rubric | 0.6250 | Uncalibrated |
| AI/LLM ATLAS cases | 8 | LLM judge: mixed rubric | 0.6125 | Uncalibrated |
| **Overall** | **68** | Mean normalized score | **0.7588** | Diagnostic only |

## Training Configuration

| Parameter | Value |
|---|---|
| Base model | GLM-4.7-Flash |
| Method | LoRA SFT |
| Framework | Unsloth |
| LoRA rank | 32 |
| LoRA alpha | 64 |
| LoRA dropout | 0 |
| Learning rate | 2e-4 |
| Epochs | 1 |
| Batch size | 1 per device |
| Gradient accumulation | 8 |
| Max sequence length | 4096 |
| Warmup | Ratio 0.1 |
| Scheduler | Cosine |
| Optimizer | `adamw_8bit` |
| Precision | BF16; 4-bit base-model loading |
| Seed | 1337 |

## Training Command

```bash
python -m scripts.finetune \
  --config configs/finetune_glm47flash.yaml
```

## Training Results

| Metric | Value | Notes |
|---|---:|---|
| Training loss final | 0.95973044 | From `training_manifest.json` |
| Validation loss final | Not recorded | Trainer state has no best metric |
| Best checkpoint | Not selected | Final checkpoint is `checkpoint-552` |
| Training duration | 38,018.77 seconds | About 10 hours 33 minutes |
| Peak memory | Not recorded | Capture on the next run |

## Post-Training Evaluation

Use the same benchmark as the baseline.

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode prediction_file \
  --predictions data/evaluation/glm47_flash_dfir_lora_predictions.jsonl \
  --run-id <tuned_run> \
  --model-label glm47_flash_dfir_lora

python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

| Benchmark | Baseline | Fine-Tuned | Delta | Decision |
|---|---:|---:|---:|---|
| TTP identification |  |  |  |  |
| IOC extraction |  |  |  |  |
| Triage ranking |  |  |  |  |
| Detection interpretation |  |  |  |  |
| Report quality |  |  |  |  |
| Reasoning quality |  |  |  |  |
| AI/LLM ATLAS cases |  |  |  |  |

## Qualitative Review

Record representative wins and failures.

### Improved Examples

| Case ID | Improvement | Notes |
|---|---|---|
|  |  |  |

### Regressions

| Case ID | Regression | Severity | Notes |
|---|---|---|---|
|  |  |  |  |

## Deployment Decision

- [ ] Fine-tuned model improves over baseline.
- [ ] No severe regressions on critical DFIR behavior.
- [ ] Reasoning format remains usable for Shepherd.
- [ ] Integration test passes.
- [ ] Rollback path is documented.

Decision:

Rationale:

## Export

| Artifact | Path | Notes |
|---|---|---|
| LoRA adapter | `data/finetune/glm47_flash_subset1/lora_adapter` | Exported |
| Merged checkpoint |  |  |
| GGUF export | `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf` | Q4_K_M |
| Evaluation report | `data/evaluation/glm47-flash-base/` | Complete but uncalibrated base run |

## Integration Notes

- Shepherd branch/commit:
- Model path configured:
- Runtime settings:
- Known limitations:
- Rollback instructions:

## Follow-Up Experiments

| Experiment | Reason | Priority |
|---|---|---|
| LoRA rank sweep | Tune capacity vs overfitting |  |
| Lower source imbalance | Check whether CISA-heavy data skews behavior |  |
| Add cloud/SaaS eval cases | Expose known coverage gaps |  |
| Add verifier pass | Improve grounding quality |  |
