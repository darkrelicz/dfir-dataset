<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Training and Release</h1>

This page defines the reproducible fine-tuning, evaluation, and promotion
procedure. Active candidates, completed runs, scores, blockers, and next actions
belong in [Current State](../current-state/index.md#phase-6-training-snapshot).

# Release Flow

<puml src="../diagrams/phase6-training-sequence.puml" alt="Training and promotion sequence" width="1000" />

A candidate is releasable only after all of these stages complete:

1. validate the packaged dataset and capture its manifest;
2. run a frozen base-model evaluation;
3. train with an explicit versioned configuration;
4. preserve the adapter, export, manifest, logs, and environment;
5. pass bounded direct-adapter termination and behavior checks;
6. run the tuned model against the same benchmark and calibrated judge;
7. pass overall, task-level, and severe-regression review;
8. record an explicit promotion or rejection decision.

# Environment Record

Before a GPU run, capture:

```bash
python --version
nvidia-smi
pip freeze > training_freeze.txt
```

Record the OS, CUDA version, Python version, Unsloth/Transformers/TRL versions,
accelerator and memory, package run ID, code commit, and artifact hashes. The
training manifest does not capture all of this information.

Install the project with the training extra only after installing the matching
PyTorch CUDA wheel described in `pyproject.toml`.

# Dataset Preflight

The built-in runner only checks that train, validation, test, and packaging
manifest paths exist. It does not parse every row, reconcile counts, validate
role order, prove split separation, or reject every malformed manifest.

Before training, verify:

- all paths and counts match the packaging manifest;
- train, validation, and test have no `source_doc_id` overlap;
- the intended reasoning/direct mixture and model transforms are present;
- assistant messages are nonempty and have balanced model-native tags;
- provenance points to the intended filtered-only quality run.

See [Packaging](packaging.md) for the package contract.

# Baseline Evaluation

Freeze the benchmark, target prompt and generation settings, served model,
judge model and quantization, judge prompt, inference settings, and a real
non-placeholder `calibration_id` before scoring either model.

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <baseline_run> \
  --model-label <base_model_label>
```

The evaluator checkpoints each verdict by replacing predictions, case results,
aggregate scores, and the manifest in sequence. Those four writes are not one
transaction. After interruption, use the last-written manifest as the commit
marker and reconcile case IDs. An `in_progress` or `uncalibrated` scorecard is
diagnostic, not baseline evidence.

Compatibility checks freeze benchmark and judge identity, but do not capture
every target-serving parameter or prove the effective served model. Preserve
target configuration and server logs separately.

# Training

Always pass the intended versioned configuration explicitly:

```bash
python -m scripts.finetune \
  --config configs/<versioned_finetune_config>.yaml
```

The CLI default is historical and must not select a real run. Use a fresh output
directory for each attempt. Fine-tuning YAML has no typed schema or range
validation, so review booleans, numeric values, paths, LoRA targets, and model
settings before starting.

The runner:

- imports Unsloth before TRL/Transformers so fused-loss patches are active;
- consumes train and validation while retaining test only for provenance;
- saves the direct LoRA adapter and configured GGUF export;
- does not resume surviving checkpoints automatically;
- writes `training_manifest.json` only after training and export complete.

A failed run can therefore leave checkpoints or exports without a current
manifest. Preserve `trainer_state.json`, the exact config, environment freeze,
logs, hashes, and failure reason.

# Direct-Adapter Promotion Gate

Test the direct adapter before serving the GGUF or spending benchmark budget.
Use bounded greeting and representative DFIR prompts and fail on:

- failure to stop on a model-defined EOS condition;
- repetition or looping;
- emitted role or chat-template delimiters;
- empty or unusable answers;
- severe regression from base-model behavior.

GLM-4.7-Flash defines a list of stop IDs rather than one scalar tokenizer EOS:

| ID | Token | Meaning |
|---:|---|---|
| `154820` | `<\|endoftext\|>` | End of text |
| `154827` | `<\|user\|>` | Next-user boundary |
| `154829` | `<\|observation\|>` | Observation/tool boundary |

Do not replace that list with `tokenizer.eos_token_id`. Omit the override or
pass `model.generation_config.eos_token_id`. Record the prompts, bounds, stop
configuration, outputs, and pass/fail result; an advisory smoke script without
enforcing exit status is not a promotion gate.

# Tuned Evaluation and Comparison

Generate tuned predictions with the same frozen inputs as the baseline, or
score a preserved prediction file:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode prediction_file \
  --predictions <tuned_predictions.jsonl> \
  --run-id <tuned_run> \
  --model-label <tuned_model_label>

python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

Comparison writes `passes_regression_gate` but returns exit code zero for both
pass and fail. Automation must read that JSON field. Review task-level deltas and
individual severe cases even when the overall mean improves.

# Release Record

Keep one decision record with:

| Field | Required evidence |
|---|---|
| Candidate | Config, code commit, package ID, adapter/export paths and hashes |
| Environment | Package freeze, CUDA/runtime details, hardware |
| Training | Manifest, trainer state, logs, selected checkpoint |
| Smoke gate | Prompts, bounds, stop IDs, outputs, enforcing result |
| Evaluation | Compatible complete baseline and tuned scorecards |
| Review | Overall and per-task deltas, severe regressions, qualitative examples |
| Decision | Promoted or rejected, owner, date, rationale, rollback path |

Promotion requires a passing direct-adapter gate, calibrated compatible
evaluation, no unacceptable DFIR regression, successful integration testing,
and a documented rollback path. Update [Current
State](../current-state/index.md) after every completed or rejected candidate.
