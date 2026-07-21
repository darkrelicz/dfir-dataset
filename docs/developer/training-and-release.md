<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Training And Release</h1>

# Purpose

Document the exact training and evaluation procedure used for Shepherd fine-tuning. This document should make the run reproducible and make before/after quality claims auditable.

# Current Training Summary

- Status: v3 and v4 training/export completed; neither has a durable passing promotion-gate record
- Completed configurations: `configs/finetune_glm47flash_v3.yaml` and `configs/finetune_glm47flash_v4.yaml`
- Newest staged configuration: `configs/finetune_glm47flash_v5.yaml`; no manifest or artifacts yet
- Dataset version: `package-20260717T040952Z`
- Dataset path: `data/packaged/glm47_v3/`
- V3 run: `train-20260717T042223Z` under `data/finetune/glm47_v3/`
- V4 run: `train-20260720T062603Z` under `data/finetune/glm47_v4/`
- V3/v4 hyperparameters: rank 16, alpha 32, dropout 0.05, attention-only targets, learning rate `2e-5`
- V5 change: dropout 0 with attention and MLP projection targets

The v3 package contains only the 4,152 filtered rows. Its GLM-only view derives
3,114 reasoning and 1,038 direct examples, removes literal
`[GENERAL KNOWLEDGE]` annotations, maps retained `<reasoning>` blocks to
`<think>`, and validates tag balance and nonempty responses. The trainer renders
once, appends EOS explicitly, rejects examples over 4,096 tokens, and removes
`messages` before TRL preprocessing. The dropout conversion is already `float`;
the earlier documented cast blocker has been fixed.

The repository does not define a single active training config. The smoke script
and evaluation config currently point at v4, while v5 is the newest experiment
file. Treat that as repository state, not evidence that either version passed
release gates.

# Historical V1 Run Summary

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
- Promotion status: rejected; direct-adapter and Web UI greeting tests looped and did not emit EOS

# Current Dataset Inputs

| Input | Path | Records | Notes |
|---|---|---:|---|
| Train | `data/packaged/glm47_v3/train.jsonl` | 3,322 | GLM-native view; grouped by `source_doc_id` |
| Validation | `data/packaged/glm47_v3/validation.jsonl` | 415 | No source-document overlap |
| Test | `data/packaged/glm47_v3/test.jsonl` | 415 | No source-document overlap |
| Packaging manifest | `data/packaged/glm47_v3/packaging_manifest.json` | 4,152 | `package-20260717T040952Z` |

# Historical V1 Dataset Inputs

| Input | Path | Records | Notes |
|---|---|---:|---|
| Train | `data/packaged/gemini_subset_1/train.jsonl` | 4,414 | Grouped by `source_doc_id` |
| Validation | `data/packaged/gemini_subset_1/validation.jsonl` | 552 | No source-document overlap |
| Test | `data/packaged/gemini_subset_1/test.jsonl` | 551 | No source-document overlap |
| Packaging manifest | `data/packaged/gemini_subset_1/packaging_manifest.json` | 5,517 | `package-20260708T071253Z` |

# Environment

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

# Baseline Evaluation

For future training runs, complete baseline evaluation before fine-tuning. The
first run (`train-20260714T025314Z`) completed before a calibrated baseline and
subsequently failed termination tests, so it is not eligible for retrospective
comparison. V2 completed but regressed in exploratory evaluation. Use only an
artifact that has passed the complete promotion gate for the next tuned
evaluation.

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

Every successful verdict individually atomically replaces `predictions.jsonl`,
`scorecard/case_results.jsonl`, `scorecard/scores.json`,
and `evaluation_manifest.json` in sequence. The group is not transactional, so
use the last-written manifest as the commit marker and reconcile case IDs after
an interruption. Do not treat an `in_progress` checkpoint as the
baseline gate. A scorecard labeled `uncalibrated` is exploratory even if its run
status is `complete`.

The comparison contract freezes benchmark content and judge configuration, not
the target prompt/generation configuration or effective served model. Preserve
those inputs and target-server logs separately. A configured model mismatch is
only warned, and response model/finish/usage metadata is not persisted.

The completed `glm47-flash-base` run is recorded below for diagnostics. These
are not calibrated baseline values. They also predate the current benchmark and
judge protocol: the saved fingerprint begins `09b197857e44` and protocol is
`phase6-judge-v2-acceptable-variants`, while current content fingerprints to
`b1fc02a447e4` and code uses `phase6-judge-v3-target-output`.

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

# Training Configuration

| Parameter | Value |
|---|---|
| Base model | GLM-4.7-Flash |
| Method | LoRA SFT |
| Framework | Unsloth |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| LoRA targets | `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Learning rate | 2e-5 |
| Epochs | 1 |
| Batch size | 1 per device |
| Gradient accumulation | 8 |
| Max sequence length | 4096 |
| Warmup | Ratio 0.1 |
| Scheduler | Cosine |
| Optimizer | `adamw_8bit` |
| Precision | BF16; 4-bit base-model loading |
| Seed | 1337 |

# Training Command

```bash
python -m scripts.finetune \
  --config configs/<intended_versioned_finetune_config>.yaml
```

Never omit `--config`: the default is the historical v1 configuration. Use a
fresh output directory for each attempt. The runner writes checkpoints but does
not resume them, and it writes `training_manifest.json` only after adapter and
GGUF export both succeed.

Unsloth must be imported before datasets/TRL/Transformers. The runner enforces
this order because TRL's entropy metric cannot consume Unsloth fused-loss empty
logits when the patch is missed.

Every successful training run saves both the direct LoRA adapter and a GGUF
artifact using the configured `gguf_dir` and `gguf_quantization`. There is no
switch to skip GGUF creation. The post-training smoke test controls whether the
generated GGUF may be promoted, served, or evaluated; it does not control
whether the file is created.

# Runner Boundaries

The built-in preflight checks only that train, validation, test, and packaging
manifest paths exist. It copies selected manifest fields but does not parse all
rows, reconcile counts, verify role order or split overlap, or reject a malformed
manifest. The trainer consumes train and validation; the test path is checked
but not loaded. Complete the package checks manually before training.

The manifest is a completion summary, not a durable lifecycle ledger. It has no
in-progress/failed status and omits hashes, code and package versions, structured
evaluation metrics, selected checkpoint, actual GGUF filename, and smoke-test
results. Preserve `trainer_state.json`, the exact config, environment freeze,
logs, artifact hashes, and promotion decision alongside it.

Fine-tuning YAML has no schema or range validation. Use real YAML booleans rather
than quoted strings and review every numeric value before starting a GPU run.

# Completed V3 And V4 Training Results

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Release state |
|---|---:|---:|---:|---:|---|
| `train-20260717T042223Z` (v3) | 416 | 1.23066088 | 1.15106297 | 17,271.22 s | Not proven promotable |
| `train-20260720T062603Z` (v4) | 416 | 1.23110431 | 1.15160668 | 18,002.76 s | Not proven promotable |

Both runs saved adapters and Q4_K_M GGUFs. Neither trainer selected a best
checkpoint, and the single intermediate evaluation metric is stored in the
checkpoint trainer state rather than the training manifest.

# Historical V1 Training Results

| Metric | Value | Notes |
|---|---:|---|
| Training loss final | 0.95973044 | From `training_manifest.json` |
| Validation loss final | Not recorded | Trainer state has no best metric |
| Best checkpoint | Not selected | Final checkpoint is `checkpoint-552` |
| Training duration | 38,018.77 seconds | About 10 hours 33 minutes |
| Peak memory | Not recorded | Capture on the next run |

# Post-Training Evaluation

Before benchmark evaluation, load the intended direct adapter and run bounded greeting
and DFIR prompts. Require a concise completion and an emitted EOS token. Do not
export, serve, or evaluate a checkpoint that reaches the token cap or emits
`<|user|>`/template delimiters. After this smoke gate, use the same benchmark as
the baseline.

`scripts/test_lora.py` is currently hard-coded to v4 and runs only `hello`. It
prints `EOS generated` but does not exit nonzero when EOS is missing, and it does
not detect repetition or template leakage. Treat it as one manual observation,
not the promotion decision; record results from the complete prompt set.

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

Comparison writes `passes_regression_gate` but exits 0 for both pass and fail.
Treat the JSON field—not command success—as the machine-readable gate.

| Benchmark | Baseline | Fine-Tuned | Delta | Decision |
|---|---:|---:|---:|---|
| TTP identification |  |  |  |  |
| IOC extraction |  |  |  |  |
| Triage ranking |  |  |  |  |
| Detection interpretation |  |  |  |  |
| Report quality |  |  |  |  |
| Reasoning quality |  |  |  |  |
| AI/LLM ATLAS cases |  |  |  |  |

# Qualitative Review

Record representative wins and failures.

## Improved Examples

| Case ID | Improvement | Notes |
|---|---|---|
|  |  |  |

## Regressions

| Case ID | Regression | Severity | Notes |
|---|---|---|---|
|  |  |  |  |

# Deployment Decision

- [ ] Fine-tuned model improves over baseline.
- [ ] No severe regressions on critical DFIR behavior.
- [ ] Reasoning format remains usable for Shepherd.
- [ ] Integration test passes.
- [ ] Rollback path is documented.

Decision:

Rationale:

# Historical V1 Export

| Artifact | Path | Notes |
|---|---|---|
| LoRA adapter | `data/finetune/glm47_flash_subset1/lora_adapter` | Exported |
| Merged checkpoint |  |  |
| GGUF export | `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf` | Q4_K_M |
| Evaluation report | `data/evaluation/glm47-flash-base/` | Complete but uncalibrated base run |

# Integration Notes

- Shepherd branch/commit:
- Model path configured:
- Runtime settings:
- Known limitations:
- Rollback instructions:

# Follow-Up Experiments

| Experiment | Reason | Priority |
|---|---|---|
| LoRA rank sweep | Tune capacity vs overfitting |  |
| Lower source imbalance | Check whether CISA-heavy data skews behavior |  |
| Add cloud/SaaS eval cases | Expose known coverage gaps |  |
| Add verifier pass | Improve grounding quality |  |
