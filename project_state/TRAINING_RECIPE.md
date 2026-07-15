# Training Recipe

## Purpose

Document the exact training and evaluation procedure used for Shepherd fine-tuning. This document should make the run reproducible and make before/after quality claims auditable.

## Run Summary

- Run ID:
- Date:
- Owner:
- Training machine:
- Base model:
- Dataset version:
- Code commit:
- Output adapter path:
- GGUF/export path:

## Dataset Inputs

| Input | Path | Records | Notes |
|---|---|---:|---|
| Train |  |  |  |
| Validation |  |  |  |
| Test |  |  |  |
| Dataset card | `docs/DATASET_CARD.md` |  |  |
| Packaging manifest |  |  |  |

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

Run baseline evaluation before fine-tuning.

Default command for scoring an existing prediction JSONL:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --predictions data/evaluation/glm47_flash_base_predictions.jsonl \
  --model-label glm47_flash_base
```

Statistical scoring is the default. To produce both independent statistical and
local-judge scorecards from the same predictions, add `--evaluator both` and
configure `scoring.judge` in `configs/evaluation.yaml`. To generate predictions
through a local OpenAI-compatible model server, add `--mode openai_compatible`.

| Benchmark | Cases | Metric | Baseline Score | Notes |
|---|---:|---|---:|---|
| TTP identification |  | F1 |  |  |
| IOC extraction |  | Precision/recall |  |  |
| Triage ranking |  | NDCG@5 |  |  |
| Detection interpretation |  | Accuracy |  |  |
| Report quality |  | LLM-as-judge 1-5 |  |  |
| Reasoning quality |  | LLM-as-judge 1-5 |  |  |
| AI/LLM ATLAS cases |  | Mixed |  |  |

## Training Configuration

| Parameter | Value |
|---|---|
| Base model | GLM-4.7-Flash |
| Method | LoRA SFT |
| Framework | Unsloth |
| LoRA rank |  |
| LoRA alpha |  |
| LoRA dropout |  |
| Learning rate |  |
| Epochs |  |
| Batch size |  |
| Gradient accumulation |  |
| Max sequence length |  |
| Warmup |  |
| Scheduler |  |
| Optimizer |  |
| Precision |  |
| Seed |  |

## Training Command

```bash
python -m scripts.finetune \
  --config configs/finetune_glm47flash.yaml
```

## Training Results

| Metric | Value | Notes |
|---|---:|---|
| Training loss final |  |  |
| Validation loss final |  |  |
| Best checkpoint |  |  |
| Training duration |  |  |
| Peak memory |  |  |

## Post-Training Evaluation

Use the same benchmark as the baseline.

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --predictions data/evaluation/glm47_flash_dfir_lora_predictions.jsonl \
  --model-label glm47_flash_dfir_lora

python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name> \
  --evaluator statistical

python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name> \
  --evaluator llm_judge
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
| LoRA adapter |  |  |
| Merged checkpoint |  |  |
| GGUF export |  |  |
| Evaluation report |  |  |

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
