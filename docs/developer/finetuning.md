<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Fine-tuning</h1>

Fine-tuning turns a validated package into a candidate adapter and export.
Training success does not imply promotion: the candidate must pass the direct
adapter gate here and the calibrated comparison in
[Evaluation](evaluation.md).

## Architecture

<puml src="../diagrams/finetuning-macro.puml" alt="Macro view of fine-tuning and candidate gating" width="900" />

The implementation has two separate paths:

1. `scripts.finetune` performs dataset path checks, loads the base model,
   attaches LoRA, renders packaged conversations, trains with response-only
   loss, exports an adapter and GGUF, and writes a training manifest.
2. `scripts.test_lora` loads an adapter for direct inference. It is not invoked
   by the training runner and must become an enforcing behavior gate before a
   candidate is eligible for evaluation.

Training, export, direct behavior, and comparative evaluation are distinct
evidence boundaries. Success at an earlier boundary never implies success at a
later one.

### Training Flow

<puml src="../diagrams/finetuning-run-detail.puml" alt="Detailed fine-tuning run sequence" width="950" />

The training path is intentionally model-specific: 4-bit
`unsloth/GLM-4.7-Flash`, PEFT LoRA, TRL `SFTTrainer`, response-only masking,
adapter save, and GGUF export. There is no generic trainer registry, typed
configuration layer, dry-run mode, or resume CLI.

### Candidate Gate Flow

<puml src="../diagrams/finetuning-gate-detail.puml" alt="Detailed direct-adapter promotion gate" width="500" />

The diagram shows the required promotion boundary, not the behavior currently
enforced by `scripts.test_lora.py`. The current implementation gap is detailed
under [Direct-Adapter Gate](#direct-adapter-gate).

### Component Ownership

| Component | Responsibility |
|---|---|
| `scripts/finetune.py` | CLI, input checks, chat rendering, model/LoRA construction, SFT, export, and manifest |
| `scripts/test_lora.py` | Current direct-adapter diagnostic; future enforcing gate |
| `configs/finetune*.yaml` | Dataset paths, base model, LoRA, trainer, output, and export settings |
| `dataset_packaging/` | Upstream message, model-tag, response-style, and split contract |
| Unsloth | 4-bit model loading, PEFT attachment, response-only masking, inference, and GGUF export |
| TRL | `SFTConfig` and `SFTTrainer` |
| Hugging Face Datasets | Train/validation JSON loading and batched rendered-text mapping |

### Contracts And Trust Boundaries

Training config and `training_manifest.json` are untyped dictionaries; there is
no Pydantic training contract. Packaged rows are also not reparsed into a
training-specific schema. The runner trusts the configured files after checking
that they exist.

The tokenizer-rendered `text` field is the actual trainer input. That rendered
text—not merely the upstream `messages` JSON—is the final data boundary before
loss masking and tokenization by TRL.

---

## CLI And Runner

Always pass an explicit versioned config:

```bash
python -m scripts.finetune \
  --config configs/<versioned_finetune_config>.yaml
```

The CLI default is `configs/finetune_glm47flash.yaml`; it is a historical
configuration, not an active-candidate pointer.

### Runner Sequence

`run_training`:

1. loads YAML as an untyped mapping and creates a time-based run ID;
2. creates `finetune.output_dir`;
3. checks configured train, validation, test, and packaging-manifest paths;
4. copies selected packaging-manifest fields into an in-memory training
   manifest;
5. loads the 4-bit base model and tokenizer;
6. attaches configured LoRA modules;
7. loads train and validation JSON datasets;
8. renders every message list through the tokenizer chat template, appends EOS,
   and rejects examples over `max_seq_length`;
9. builds `SFTConfig` and `SFTTrainer`;
10. applies response-only loss masking;
11. runs `trainer.train()` without automatic checkpoint resume;
12. saves adapter and tokenizer;
13. exports GGUF;
14. stores stringified trainer statistics and writes
    `training_manifest.json`.

The test split is required to exist and recorded for provenance, but it is not
loaded or evaluated by the trainer.

---

## Inputs And Configuration

Every fine-tuning config identifies:

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

| Config section | Consumed behavior |
|---|---|
| `run.seed` | Forced TRL training seed |
| `dataset` | Train/validation/test and packaging-manifest paths |
| `model` | Base model and maximum rendered sequence length |
| `lora` | Rank, alpha, dropout, bias, targets, checkpointing, and PEFT random state |
| `finetune` | Trainer output/checkpoints, batch sizes, accumulation, optimizer, schedule, epochs, eval/save/logging, workers, and BF16 |
| `export` | Adapter path, GGUF directory, and quantization method |

The code also forces `load_in_4bit=True`, `trust_remote_code=True`,
`dataset_text_field="text"`, `report_to="none"`, and GGUF export. These effective
settings are not independently configurable.

---

## Environment And Dataset Boundary

### Environment Record

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

### Dataset Preflight

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

### Chat Rendering

`render_training_dataset` maps train and validation rows in batches:

1. `tokenizer.apply_chat_template(..., tokenize=False,
   add_generation_prompt=False)` renders each `messages` list;
2. `tokenizer.eos_token` is appended when the rendered text does not already end
   with it;
3. the complete batch is tokenized without truncation;
4. any example above `model.max_seq_length` fails the run;
5. the original `messages` column is removed and the rendered `text` column is
   retained.

Removing `messages` is required. If both conversational messages and rendered
text remain, TRL may detect the row as conversational and apply the chat
template a second time.

The runner does not validate message roles, GLM tags, response-style counts,
split overlap, or packaging-manifest counts before loading the model. Those
checks remain an external preflight responsibility.

---

## Training Implementation

### Model And LoRA Construction

`FastLanguageModel.from_pretrained` loads the configured base model with 4-bit
weights, the configured maximum sequence length, and remote model code enabled.
`FastLanguageModel.get_peft_model` then attaches LoRA to the configured target
modules with rank, alpha, dropout, bias, gradient checkpointing, and random
state from YAML.

Invalid target module names or incompatible model settings fail only when the
model/PEFT layer consumes them; there is no earlier model-aware config
validation.

### Dataset And Trainer

Hugging Face `load_dataset("json")` loads only train and validation. After chat
rendering, `build_sft_config` maps the configured batch, accumulation, learning
rate, epochs, scheduler, optimizer, weight decay, logging, evaluation,
checkpoint, BF16, warmup, and seed values into TRL `SFTConfig`.

`SFTTrainer` consumes `text`, then
`unsloth.chat_templates.train_on_responses_only` masks non-response tokens.
The runner calls `trainer.train()` without a resume checkpoint argument and
does not select a best checkpoint explicitly.

### Export And Artifacts

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

`trainer_stats` is stored as `str(stats)` rather than structured metrics. The
adapter and tokenizer are saved to `export.adapter_dir`; GGUF is saved separately
to `export.gguf_dir`. These paths can differ from `finetune.output_dir`, so a
candidate's artifacts may span several directories.

---

## Direct-Adapter Gate

### Current `test_lora.py` Implementation

The current script is a diagnostic, not an enforcing gate. It:

- uses hard-coded adapter path, sequence length, token bound, and one `"hello"`
  prompt;
- requires CUDA, loads the adapter in 4-bit mode, and enables Unsloth inference;
- renders the user prompt with `enable_thinking=False`;
- generates deterministically with `max_new_tokens=256`;
- passes `model.generation_config.eos_token_id` to generation;
- prints raw output, token count, unique generated token values, scalar tokenizer
  EOS presence, duration, and speed.

Its `"Stop token generated"` value is currently `bool(set(generated_token_ids))`,
which means only that at least one token was generated. The printed `"Stop
tokens"` are all unique generated tokens, not the intersection with configured
stop IDs. The script does not check the actual termination reason, repetition,
template leakage, empty/useless output, or multiple DFIR prompts, and it does not
exit nonzero on a behavior failure or write a gate artifact.

Do not use its current output as promotion evidence.

### Required Enforcing Behavior

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

---

## Changing The Training Recipe

Start with the narrowest owner:

| Intended change | Primary owner | Coupled review |
|---|---|---|
| Package or split input | Versioned `dataset` config | Packaging manifest, rendered rows, provenance, overlap |
| Base model or context length | `model` config and `FastLanguageModel.from_pretrained` | Packaging tags, tokenizer template, sequence preflight, gate stops |
| LoRA rank/targets/dropout | `lora` config and `get_peft_model` | Model module names, memory, former candidate comparison |
| Chat rendering or EOS | `format_messages_for_training`, `render_training_dataset` | Double templating, max length, response masking |
| Trainer hyperparameters | `finetune` config and `build_sft_config` | Effective batch size, eval/save cadence, resume expectations |
| Loss masking | `train_on_responses_only` call | Rendered template boundaries and supervised-token inspection |
| Checkpoint resume/selection | `trainer.train` and trainer configuration | Manifest, selected artifact, evaluation identity |
| Adapter or GGUF export | `train_with_unsloth`, `export` config | Artifact paths/hashes, serving compatibility |
| Training manifest | `run_training` | Structured metrics, code/environment/package identity |
| Direct-adapter gate | `scripts/test_lora.py` | Parameterization, stop IDs, checks, persisted evidence, nonzero failure |

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

---

## Candidate Evidence

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
