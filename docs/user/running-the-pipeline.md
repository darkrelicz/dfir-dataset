<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Running The Pipeline

This page documents the existing command path. It does not introduce new
workflow policy beyond the current codebase and state docs.

## 1. Collect Sources

Run every configured collector:

```bash
python -m scripts.collect_all
```

Run one collector:

```bash
python -m scripts.collect_all --source mitre_attack
```

List available collectors:

```bash
python -m scripts.collect_all --list
```

Dry-run config selection without collecting:

```bash
python -m scripts.collect_all --dry-run
```

Collector output is written to `data/raw/<source>/<source>.jsonl`. The combined
collection manifest is `data/raw/collection_manifest.json`.

## 2. Validate Raw Corpus

```bash
python -m scripts.synthesize validate-raw --raw-dir data/raw
```

This validates every raw JSONL row against `collectors.schemas.RawDocument`,
checks duplicate `doc_id` values, and reports source counts.

## 3. Render Prompts Without API Calls

```bash
python -m scripts.synthesize render-prompts \
  --mode subset \
  --raw-dir data/raw \
  --output-dir data/synthesized/dry_run
```

Add `--write-prompt-files` for one Markdown file per prompt.

Prompt rendering uses:

* `configs/synthesis.yaml`
* `configs/task_categories.yaml`
* `configs/source_profiles.yaml`
* prompt templates under `synthesizers/prompts/`
* prompt-time compactors under `synthesizers/prompts/compactors/`

## 4. Run Gemini Synthesis

Set `GEMINI_API_KEY` in `.env` or the shell environment.

```bash
python -m scripts.synthesize run \
  --mode subset \
  --raw-dir data/raw \
  --output-dir data/synthesized/gemini_subset_1 \
  --skip-present
```

The runner writes:

| Output | Meaning |
|---|---|
| `prompts.jsonl` | Prompt records with hashes |
| `raw_outputs.jsonl` | Raw model outputs and metadata |
| `accepted.jsonl` | Candidate pairs that pass Phase 3 validation |
| `rejected.jsonl` | API or validation failures |
| `generation_manifest.json` | Run metadata and notes |

`--skip-present` skips terminal accepted/rejected prompt IDs only when prompt
hash and model match the current plan.

## 5. Run Phase 4 Quality

```bash
python -m scripts.quality_filter \
  --input data/synthesized/gemini_subset_1/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/gemini_subset_1
```

The quality runner logs major stages at INFO level and writes:

| Output | Meaning |
|---|---|
| `filtered.jsonl` | Rows accepted by row and dataset gates |
| `review_queue.jsonl` | Rows needing review but not hard-rejected |
| `rejected.jsonl` | Rows with reject-severity issues |
| `manual_spot_check_sample.jsonl` | Deterministic filtered sample |
| `quality_manifest.json` | Counts, distributions, and audits |

## 6. Package Dataset

```bash
python -m scripts.package_dataset \
  --config configs/packaging.yaml
```

The current packager consumes `filtered.jsonl` plus `review_queue.jsonl`, then
splits by `source_doc_id`.

Output:

```text
data/packaged/gemini_subset_1/train.jsonl
data/packaged/gemini_subset_1/validation.jsonl
data/packaged/gemini_subset_1/test.jsonl
data/packaged/gemini_subset_1/packaging_manifest.json
```

## 7. Phase 6

Phase 6 now has evaluator and training scaffolding.

First finalize a held-out benchmark:

```bash
evaluation/benchmark/
```

Run baseline evaluation before fine-tuning. The evaluator always writes one
local-judge scorecard. It can score an existing prediction JSONL:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --predictions data/evaluation/glm47_flash_base_predictions.jsonl \
  --model-label glm47_flash_base
```

Configure the target endpoint under `generation` and the separate judge endpoint
under `scoring.judge` to call both local model servers directly:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --model-label glm47_flash_base
```

The runner processes cases sequentially. It generates one target response,
sends that response to the judge, checkpoints every output artifact, and
advances only after the verdict and checkpoint succeed. An interrupted run
therefore retains all fully evaluated cases with `in_progress` status. The final
case changes the scorecard and manifest status to `complete`.

Launch training only after the baseline manifest exists:

```bash
python -m scripts.finetune \
  --config configs/finetune_glm47flash.yaml
```

Then rerun the same evaluator against the fine-tuned model and compare:

```bash
python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

The comparison accepts only LLM-judge scorecards and rejects a changed judge
protocol/configuration fingerprint or calibration ID. Qualitatively review
critical regressions before deployment.

Record the exact training configuration, checkpoint paths, and results in
`project_state/TRAINING_RECIPE.md` and `project_state/TODO.md`.
