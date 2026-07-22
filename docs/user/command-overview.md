<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Command Overview</h1>

> This page documents the available commands. Read to find out about the different configurations available.

## Data Collection

Run every configured data collector:

```bash
python3 -m scripts.collect_all
```

| Option | Default | Purpose |
|---|---|---|
| `--list` | NIL | List available collectors |
| `--source SOURCE` | NIL, must specify a source | Run a specific collector |

#### Details

##### Output directories

* Collector output is formatted and written to `data/raw/<source>/<source>.jsonl`.
* The cloned data and repositories are stored under `data/raw/.cache` and `data/raw/.repos` respectively.
* The combined collection manifest is `data/raw/collection_manifest.json`.

##### Metadata specifics

The manifest contains results from the latest invocation only. In particular, running one collector with `--source` replaces the existing manifest with a one-entry manifest; it does not preserve or merge entries for the other raw files. If complete-corpus manifest coverage matters, run all collectors before the downstream validation step.

Always inspect every manifest entry's `errors` and `warnings`, confirm that the expected sources are present, and run raw-corpus validation before moving to synthesis.

## Raw Corpus Validation

Validate the complete raw corpus without rendering prompts or calling a model:

```bash
python3 -m scripts.synthesize validate-raw \
  --raw-dir data/raw
```

| Option | Default | Purpose |
|---|---|---|
| `--raw-dir DIR` | `data/raw` | Directory containing `<source>/*.jsonl` |

#### Details

The command validates every JSONL row against `collectors.schemas.RawDocument`, detects duplicate `doc_id` values, and reports file, document, issue, and per-source counts. It exits with status 1 when validation fails.

## Prompt Rendering

Render the prompt plan without making model API calls:

```bash
python -m scripts.synthesize render-prompts \
  --mode pilot \
  --raw-dir data/raw \
  --output-dir data/synthesized/prompt_preview \
  --write-prompt-files
```

| Option | Default | Purpose |
|---|---|---|
| `--raw-dir DIR` | `data/raw` | Raw corpus to load |
| `--synthesis-config FILE` | `configs/synthesis.yaml` | Load synthesis and source profile configuations |
| `--task-config FILE` | `configs/task_categories.yaml` | Load task-category definitions and target distribution |
| `--output-dir DIR` | `data/synthesized/dry_run` | Output destination for the rendered prompts |
| `--mode {pilot,subset,full}` | `pilot` | Select the configured pilot sample, subset sample, or full corpus |
| `--limit N` | no limit | Keep only the first `N` documents after selection |
| `--write-prompt-files` | off | Also write one Markdown file per prompt |

#### Details 

Prompt rendering uses `configs/source_profiles.yaml`, the templates below `synthesizers/prompts/`, and prompt-time compactors below `synthesizers/prompts/compactors/` in addition to the two explicit config
arguments.

##### Output directories

| Output | Meaning |
|---|---|
| `prompts.jsonl` | Structured prompt records, including stable prompt IDs and hashes. |
| `generation_manifest.json` | API-free render metadata with model set to `none`. |
| `prompts/*.md` | Optional human-readable prompt files. |

## Gemini Synthesis

Set `GEMINI_API_KEY` in `.env` or the environment, then generate candidate instruction pairs:

```bash
python -m scripts.synthesize run \
  --mode subset \
  --raw-dir data/raw \
  --output-dir data/synthesized/gemini_subset_1 \
  --skip-present
```

| Option | Default | Purpose |
|---|---|---|
| `--raw-dir DIR` | `data/raw` | Raw corpus to validate and synthesize |
| `--synthesis-config FILE` | `configs/synthesis.yaml` | Model, generation, retry, and source-profile settings |
| `--task-config FILE` | `configs/task_categories.yaml` | Task-category definitions and targets |
| `--quality-config FILE` | `configs/quality.yaml` | Taxonomy references used by inline validation |
| `--output-dir DIR` | `data/synthesized/gemini_run` | Destination for generation artifacts |
| `--mode {pilot,subset,full}` | `pilot` | Select the pilot sample, subset sample, or full corpus |
| `--limit N` | no limit | Keep only the first `N` documents after selection |
| `--env-file FILE` | `.env` | Environment file from which to load the API key |
| `--max-rejection-rate RATE` | `0.20` | Stop subset/full generation when the current-run rejection rate reaches this value |
| `--min-rejection-check N` | `20` | Minimum current-run attempts before checking the rejection rate |
| `--disable-rejection-circuit-breaker` | off | Disable rejection-rate early stopping |
| `--skip-present` | off | Skip terminal prompt IDs whose saved prompt hash and model match |

#### Details

* `run` validates the complete raw corpus before it loads the model client. 
* The rejection circuit breaker applies only to `subset` and `full`; an early stop returns status 2. Argument, corpus, or credential failures return status 1.

##### Output directories

| Output | Meaning |
|---|---|
| `prompts.jsonl` | The current prompt plan |
| `raw_outputs.jsonl` | Raw model responses and request metadata |
| `accepted.jsonl` | Candidate pairs that passed validation |
| `rejected.jsonl` | API failures or responses that exhausted validation retries |
| `generation_manifest.json` | Metadata for the latest invocation |

The generated pairs are validated for invented indicators and for misaligned output formats. 

Accepted, rejected, and raw-output streams are append-oriented, while the prompt plan and manifest are replaced. 

Use a fresh output directory when the policies, models, or raw data field changes. For an unchanged plan, `--skip-present` can continue a directory, but rejected API calls also count as terminal. Use a new output directory when those prompts must be retried.

## Quality Filtering

Run quality checks against the accepted synthesis candidates:

```bash
python -m scripts.quality_filter \
  --input data/synthesized/gemini_subset_1/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/gemini_subset_1
```

| Option | Default | Purpose |
|---|---|---|
| `--input FILE` | `data/synthesized/gemini_subset_1/accepted.jsonl` | Candidate JSONL documents |
| `--raw-dir DIR` | `data/raw` | Raw corpus used for source-grounding checks |
| `--quality-config FILE` | `configs/quality.yaml` | Gates, score weights, thresholds, references, and sampling settings |
| `--task-config FILE` | `configs/task_categories.yaml` | Valid categories and distribution targets |
| `--output-dir DIR` | `data/quality/gemini_subset_1` | Destination for quality artifacts |
| `--append` | off | Append row outputs instead of replacing them |

#### Details

##### Output directories

| Output | Meaning |
|---|---|
| `filtered.jsonl` | Rows accepted by row-level and dataset-level gates. |
| `review_queue.jsonl` | Rows requiring review without a reject-severity issue. |
| `rejected.jsonl` | Rows with reject-severity issues. |
| `manual_spot_check_sample.jsonl` | Deterministic sample of filtered rows. |
| `quality_manifest.json` | Counts, distributions, configuration paths, and audit results. |

<box type="warning" seamless header="">
<md>
With `--append`, row files accumulate but the manifest, sample, and dataset-level gates describe only the current input batch. Always aim for a fresh quality run.
</md>
</box>

<box type="info" seamless header="">
<md>
Inspect the manifest counts, issue codes, source shares, and audit flags before packaging.
</md>
</box>

## Dataset Packaging

Package only the rows that passed the quality filtering stage:

```bash
python -m scripts.package_dataset \
  --config configs/packaging_glm47_v3.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_v3
```

| Option | Default | Purpose |
|---|---|---|
| `--config FILE` | `configs/packaging.yaml` | Split, format, response-style, and model-transform settings |
| `--quality-dir DIR` | `data/quality/gemini_subset_1` | Directory containing `filtered.jsonl` and `quality_manifest.json` |
| `--output-dir DIR` | `data/packaged/gemini_subset_1` | Destination for packaged splits |

#### Details 

The packager rejects empty inputs and non-`filtered` rows, assigns the configured reasoning/direct response mix, validates model-specific response transforms, and splits records by `source_doc_id` to prevent source-document leakage across splits.

Generated outputs:

```text
train.jsonl
validation.jsonl
test.jsonl
packaging_manifest.json
```

## Fine-Tuning

Fine-tune with an explicit versioned configuration in the DGX Sparks Unsloth environment:

```bash
python -m scripts.finetune \
  --config configs/finetune_glm47flash_v6.yaml
```

| Option | Default | Purpose |
|---|---|---|
| `--config FILE` | `configs/finetune_glm47flash.yaml` | Dataset paths, base model, LoRA, training, output, and export settings |

#### Details

The selected config determines the output directory. The runner checks that the configured train, validation, and test paths exist, trains on the train and validation files, saves the LoRA adapter, exports the configured GGUF, and writes `training_manifest.json`. The test split is checked but is not consumed for training.

### Adapter Smoke Test

Run the repository's fixed-path adapter smoke script in the same environment:

```bash
python -m scripts.test_lora
```

#### Details 

The script has no command-line options. Its adapter path and token limits are constants in `scripts/test_lora.py`; review them before running it. It is a diagnostic generation script, not an enforced promotion gate.


## Evaluation

Evaluation is done using a separate local judge configured under `scoring.judge` in `configs/evaluation.yaml`.

### Evaluate an OpenAI-Compatible Target

Configure `generation.base_url` as the API root, such as `http://127.0.0.1:8080/v1`, and configure the judge at a different API root. Then run:

```bash
python -m scripts.run_evaluation \
  --mode openai_compatible \
  --model-label glm47_flash_base \
  --run-id base_calibrated_1
```

### Evaluate Saved Predictions

Provide one JSON object per selected benchmark case:

```json
{"case_id":"phase6-ai-atlas-001","prediction":"Candidate answer text"}
```

Then run:

```bash
python -m scripts.run_evaluation \
  --mode prediction_file \
  --predictions data/evaluation/input_predictions.jsonl \
  --model-label glm47_flash_base \
  --run-id base_replay_1
```

### Evaluation Options

| Option | Default | Purpose |
|---|---|---|
| `--config FILE` | `configs/evaluation.yaml` | Benchmark, target, judge, prompt, and output settings |
| `--cases PATH` | `benchmark.cases_path` | Benchmark case file or directory |
| `--output-dir DIR` | `<output.base_dir>/<run-id>` | Override the complete run directory |
| `--run-id ID` | timestamp plus model label | Stable label used in metadata and the default output path |
| `--mode {openai_compatible,prediction_file}` | `generation.mode` | Generate through an endpoint or replay a prediction JSONL |
| `--predictions FILE` | `generation.predictions_path` | Prediction input required by `prediction_file` mode |
| `--model NAME` | `generation.model` | Override the target model name |
| `--model-label LABEL` | `generation.model_label`, then `model` | Human-facing model label used in artifacts |
| `--max-cases N` | all cases | Evaluate only the first `N` loaded cases |
| `--log-level LEVEL` | `INFO` | Python logging level, such as `DEBUG` or `WARNING` |

#### Details 

The evaluator processes cases sequentially and checkpoints after each judged case. It atomically replaces each artifact individually:

```text
predictions.jsonl
scorecard/case_results.jsonl
scorecard/scores.json
evaluation_manifest.json
```

Checkpointing preserves completed work but does not implement resume; rerunning the same output directory starts replacement from the first new checkpoint.


## Evaluation Comparison

Compare complete, compatible baseline and tuned scorecards:

```bash
python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/base_calibrated_1 \
  --tuned-dir data/evaluation/tuned_calibrated_1 \
  --output-dir data/evaluation/comparisons/base_vs_tuned
```

| Option | Default | Purpose |
|---|---|---|
| `--baseline-dir DIR` | required | Complete baseline evaluation directory |
| `--tuned-dir DIR` | required | Complete tuned evaluation directory |
| `--output-dir DIR` | required | Destination for comparison artifacts |
| `--minimum-overall-delta VALUE` | `0.0` | Minimum acceptable tuned-minus-baseline overall score change |
| `--max-task-regression VALUE` | `0.05` | Largest permitted normalized regression for any task type |
| `--log-level LEVEL` | `INFO` | Python logging level |

#### Details 

Comparison requires matching benchmark and judge reproducibility metadata and complete scorecards. It writes `comparison.json` and `comparison.md`.


## Recommended Command Order

```text
1. collect_all
2. synthesize validate-raw
3. synthesize render-prompts
4. synthesize run
5. quality_filter
6. package_dataset
7. finetune
8. run_evaluation (baseline and tuned)
9. compare_evaluations
```
