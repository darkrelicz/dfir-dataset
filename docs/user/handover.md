<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Handover Guide</h1>

# Purpose

Use this guide to hand the dataset factory to a successor. This file is an operating guide, not the canonical current-state record.

For run-specific status, read generated manifests and the state files named in `PROJECT_BRIEF.md`:

- `project_state/PROJECT_BRIEF.md`
- `docs/developer/architecture.md`
- `project_state/TODO.md`
- `project_state/DECISIONS.md`
- generated manifests under `data/raw/`, `data/synthesized/`, `data/quality/`, `data/packaged/`, `data/evaluation/`, and `data/finetune/`

# Handover Packet Checklist

Before handing over the project, make sure the successor can find:

- The current phase and next actions in `project_state/TODO.md`.
- Architecture and implementation notes in `docs/developer/architecture.md`.
- Durable decisions in `project_state/DECISIONS.md`.
- Raw collection outputs and `data/raw/collection_manifest.json`.
- Synthesis outputs and the relevant `generation_manifest.json`.
- Quality outputs and the relevant `quality_manifest.json`.
- Packaging outputs and the relevant `packaging_manifest.json`, if packaging exists.
- Evaluation manifests, predictions, and LLM-judge scorecards under `data/evaluation/`.
- The rejected v1 `train-20260714T025314Z` outputs for failure analysis, the v2 package manifest under `data/packaged/glm47_dfir_v2/`, and any completed v2 training manifest under `data/finetune/glm47_flash_lora_dfir_v2/`.

# Successor Orientation

Explain these points during handover:

- Phase 3 `accepted.jsonl` is candidate synthesis output, not final training data.
- Phase 4 `filtered.jsonl` is the first dataset eligible for packaging.
- `review_queue.jsonl` is included in the current Phase 5 package by explicit time-boxed risk acceptance and transformed into direct-answer examples. Rejected rows remain excluded.
- Splits must be by `source_doc_id` to avoid leakage.
- Canonical responses use `<reasoning>`, not `<think>`.
- Model-specific exporters may transform formatting only at packaging time. The GLM v2 view removes `[GENERAL KNOWLEDGE]` and maps `<reasoning>` to `<think>` without mutating canonical synthesis/quality data.
- A completed training loop is not a release gate. The direct adapter must emit EOS on bounded smoke prompts before GGUF promotion or evaluation.
- Import Unsloth before datasets/TRL/Transformers in the training process so the fused-loss trainer patch is installed.
- Full-corpus generation should be treated as a separate budget decision.
- Phase 6 has one evaluator: the separately served local LLM judge. There is no statistical or combined evaluator mode.
- Evaluation is sequential and checkpoints every artifact after each successful verdict. An `in_progress` checkpoint is recoverable evidence, not a comparable final scorecard.
- A matching judge fingerprint prevents accidental configuration drift, but final claims also require a genuinely calibrated, non-placeholder `calibration_id` and human review.

# Reproduction Commands

## Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Collect Raw Sources

```bash
python -m scripts.collect_all
```

## Validate Raw Corpus

```bash
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
```

## Render Prompts

```bash
.venv/bin/python -m scripts.synthesize render-prompts --mode <pilot|subset|full> --output-dir data/synthesized/<run>
```

## Run Synthesis

```bash
.venv/bin/python -m scripts.synthesize run --mode <pilot|subset|full> --output-dir data/synthesized/<run>
```

## Run Phase 4 Quality Filter

```bash
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/<run>/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/<run> \
  --log-level INFO
```

## Package Phase 5 Dataset

```bash
.venv/bin/python -m scripts.package_dataset \
  --config configs/packaging.yaml \
  --quality-dir data/quality/<run> \
  --output-dir data/packaged/<run>
```

For the current GLM v2 view:

```bash
.venv/bin/python -m scripts.package_dataset \
  --config configs/packaging_glm47_v2.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_dfir_v2
```

## Run Phase 6 Evaluation

Use `configs/evaluation.yaml` for the target and judge endpoints:

```bash
.venv/bin/python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <evaluation_run> \
  --model-label <model_label>
```

For prediction replay, add `--mode prediction_file --predictions <path>`.

## Train And Compare

```bash
.venv/bin/python -m scripts.finetune \
  --config configs/finetune_glm47flash_v2.yaml

.venv/bin/python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

# Critical Gates

Before packaging:

- [ ] Phase 4 deterministic and heuristic validation has run.
- [ ] Review queue has been adjudicated, explicitly risk-accepted, or excluded.
- [ ] Near-duplicate audit has been reviewed.
- [ ] Distribution audit has been reviewed.
- [ ] Manual spot-check sample has been reviewed.

Before training:

- [ ] Train/validation/test split is by `source_doc_id`.
- [ ] Dataset package loads locally.
- [ ] GLM training view contains no `[GENERAL KNOWLEDGE]` or `<reasoning>` tokens and has balanced `<think>` blocks.
- [ ] Rendered training text ends with tokenizer EOS and fits the configured sequence length.
- [ ] Dataset card is filled from the packaged run.
- [ ] Held-out baseline evaluation set is finalized and verified absent from training inputs.
- [ ] Judge calibration set is adjudicated and `calibration_id` is not `uncalibrated`.
- [ ] Baseline evaluation manifest and scorecard are `complete`.
- [ ] Baseline model scores and judge fingerprint are recorded.

Before Shepherd integration:

- [ ] Direct LoRA adapter passes bounded EOS/termination smoke tests.
- [ ] Fine-tuned model passes the calibrated local-judge comparison gate.
- [ ] No critical DFIR task or safety behavior has an unacceptable regression.
- [ ] No severe regressions on critical DFIR behavior.
- [ ] Reasoning format remains usable for Shepherd.
- [ ] Rollback path is documented.

# Artifact Inventory Template

Fill this table for a specific handover or release:

| Artifact | Path | Status | Notes |
|---|---|---|---|
| Raw manifest |  |  |  |
| Synthesis output |  |  |  |
| Quality output |  |  |  |
| Packaged dataset |  |  |  |
| Evaluation manifest |  |  |  |
| LLM-judge scorecard |  |  |  |
| Training artifacts |  |  |  |

# Risk Review Template

| Risk | Status | Mitigation | Owner |
|---|---|---|---|
| Source imbalance |  |  |  |
| Thin sources cause padded answers |  |  |  |
| Prompt compaction removes useful evidence |  |  |  |
| Untagged general knowledge passes as source-only |  |  |  |
| Review queue is too large |  |  |  |
| Fine-tuning does not improve baseline |  |  |  |
| Judge remains uncalibrated or drifts between runs |  |  |  |
| Partial evaluation is mistaken for a final scorecard |  |  |  |
| Training manifest omits effective hyperparameters or export paths |  |  |  |

# Credentials And Secrets

Do not commit real secrets.

- `GEMINI_API_KEY`: stored in `.env` or the environment
- DGX access: document outside the repository or in an approved secret store
- Local dataset storage path: repository-local `data/` unless changed

# Maintenance Rule

Update this guide only when the handover process changes. Do not use it as the current project status page.
