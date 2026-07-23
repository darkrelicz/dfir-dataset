<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Fine-tuning</h1>

Fine-tuning turns a validated package into a candidate adapter and export.
Training success does not imply promotion: the candidate must pass the direct
adapter gate here and the calibrated comparison in
[Evaluation](evaluation.md).

# Visual Overview

## Macro View

<puml src="../diagrams/finetuning-macro.puml" alt="Macro view of fine-tuning and candidate gating" width="900" />

## Training Run Detail

<puml src="../diagrams/finetuning-run-detail.puml" alt="Detailed fine-tuning run sequence" width="950" />

## Direct-Adapter Gate Detail

<puml src="../diagrams/finetuning-gate-detail.puml" alt="Detailed direct-adapter promotion gate" width="500" />

# Inputs And Configuration

Always pass an explicit versioned config:

```bash
python -m scripts.finetune \
  --config configs/<versioned_finetune_config>.yaml
```

There is no active-config pointer, and the CLI default is not an active
candidate. Every fine-tuning config identifies:

- package train, validation, test, and manifest paths;
- GLM-4.7-Flash base model and sequence length;
- LoRA target modules, rank, alpha, checkpointing, and seed;
- trainer arguments and checkpoint policy;
- adapter and GGUF destinations and GGUF quantization.

The runner is intentionally specific to 4-bit Unsloth LoRA SFT. It uses
response-only loss masking and always saves both the adapter and GGUF; GGUF
export cannot be disabled.

Configuration is untyped and values are cast at use sites. Keep booleans as
YAML booleans—a quoted `"false"` can become truthy—and review numeric ranges,
paths, LoRA targets, sequence length, and export settings before an expensive
run.

# Environment Record

Install the training extra only after installing the matching PyTorch CUDA
wheel described in `pyproject.toml`. Before a GPU run, capture:

```bash
python --version
nvidia-smi
pip freeze > training_freeze.txt
```

Record OS, CUDA, Python, Unsloth, Transformers, TRL, accelerator and memory,
package run ID, code commit, config hash, dataset hashes, and output paths. The
training manifest does not capture all effective runtime choices.

# Dataset Preflight

The runner checks that configured package paths exist, but it does not fully
validate every row or reconcile the package.

Before training:

1. parse all train, validation, and test rows;
2. reconcile their counts and paths with `packaging_manifest.json`;
3. confirm no `source_doc_id` overlap;
4. confirm intended reasoning/direct proportions and model transforms;
5. validate role order, non-empty assistant content, and balanced model tags;
6. render training text with the target tokenizer;
7. confirm tokenizer EOS termination and sequence-length fit;
8. verify provenance points to the intended filtered-only quality run;
9. verify held-out evaluation cases are absent from package inputs.

See [Packaging](packaging.md) for the row and split contract.

# Training And Artifacts

The runner:

- imports Unsloth before datasets, TRL, or Transformers so fused-loss patches
  are active;
- consumes train and validation while retaining test only for provenance;
- saves the direct LoRA adapter and configured GGUF export;
- does not automatically resume surviving checkpoints;
- writes `training_manifest.json` only after training and GGUF export complete.

A failure can therefore leave checkpoints or exports without a current
manifest. Use a fresh output directory per attempt and preserve
`trainer_state.json`, exact config, logs, environment freeze, hashes, and
failure reason.

The manifest copies raw model, LoRA, trainer, and export mappings, but it omits
some forced effective settings, structured validation metrics, code/environment
versions, selected checkpoint, actual GGUF filename, and direct-adapter gate
results. Record these in the candidate evidence packet.

# Direct-Adapter Gate

Test the direct LoRA adapter before serving a GGUF or spending evaluation
budget. Use bounded greeting and representative DFIR prompts and fail the
process on:

- failure to stop on a model-defined stop condition;
- repetition or looping;
- emitted role or chat-template delimiters;
- empty or unusable answers;
- severe base-behavior regression.

GLM-4.7-Flash uses a stop-token list:

| ID | Token | Boundary |
|---:|---|---|
| `154820` | `<\|endoftext\|>` | End of text |
| `154827` | `<\|user\|>` | Next user |
| `154829` | `<\|observation\|>` | Observation/tool |

Do not replace this list with scalar `tokenizer.eos_token_id`. Omit an override
or pass `model.generation_config.eos_token_id`. Record prompts, token bounds,
stop configuration, outputs, termination reason, repetition/template checks,
and enforcing pass/fail status.

# Changing The Training Recipe

When changing model, LoRA, trainer, tokenizer, or export behavior:

1. create a new versioned config and fresh artifact directory;
2. review package compatibility and rendered examples;
3. run configuration and dataset preflight before allocating the GPU;
4. run a bounded smoke training job;
5. inspect loss, validation behavior, checkpoints, adapter loading, and export;
6. run the complete direct-adapter gate;
7. retain the former candidate until the new one completes evaluation.

Add typed configuration validation before relying on a new field. If a new
model requires different response tags, implement them at packaging rather than
mutating canonical records.

# Candidate Evidence

For each candidate retain:

| Area | Required evidence |
|---|---|
| Identity | Candidate name, config, code commit, package ID |
| Environment | Package freeze, CUDA/runtime, hardware |
| Training | Manifest, trainer state, logs, metrics, selected checkpoint |
| Artifacts | Adapter/GGUF paths and hashes |
| Direct gate | Prompts, bounds, stop IDs, outputs, enforcing result |
| Evaluation handoff | Exact served artifact and model label |

After the direct gate passes, continue with
[Evaluation](evaluation.md#base-and-tuned-comparison). Active candidate status
belongs in [Current State](../current-state/index.md); superseded experiments
belong in [Revisions](../current-state/revisions.md).
