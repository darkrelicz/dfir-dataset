<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Running The Pipeline</h1>

This page documents the existing command path. It does not introduce new
workflow policy beyond the current codebase and state docs.

# 1. Collect Sources

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

The manifest contains results from the current invocation only. In particular,
running one collector with `--source` replaces the existing manifest with a
one-entry manifest; it does not preserve or merge entries for the other raw
files. If complete-corpus manifest coverage matters, run all collectors before
the downstream validation step.

Collection exit status is not currently a reliable success signal: unknown
sources, collector-reported errors, and exceptions caught by the orchestrator do
not force a non-zero exit. Always inspect every manifest entry's `errors` and
`warnings`, confirm that the expected sources are present, and run raw-corpus
validation before synthesis.

Dry-run validates selection from the loaded YAML only. It does not apply a
configuration schema, instantiate collectors, inspect local caches, or test
upstream access.

# 2. Validate Raw Corpus

```bash
python -m scripts.synthesize validate-raw --raw-dir data/raw
```

This validates every raw JSONL row against `collectors.schemas.RawDocument`,
checks duplicate `doc_id` values, and reports source counts.

# 3. Render Prompts Without API Calls

```bash
python -m scripts.synthesize render-prompts \
  --mode subset \
  --raw-dir data/raw \
  --output-dir data/synthesized/dry_run
```

Add `--write-prompt-files` for one Markdown file per prompt.

`--limit` truncates the already assembled plan; it does not preserve
cross-source stratification. With the current configuration, using pilot mode
with a limit of 10 renders ten `mitre_attack` prompts. Run the full pilot when
reviewing representation across sources.

Prompt rendering uses:

* `configs/synthesis.yaml`
* `configs/task_categories.yaml`
* `configs/source_profiles.yaml`
* prompt templates under `synthesizers/prompts/`
* prompt-time compactors under `synthesizers/prompts/compactors/`

# 4. Run Gemini Synthesis

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

Rejected prompts are terminal for this check, including transient API failures.
To retry those prompts without mixing run state, use a new output directory.

Use a new output directory for a new prompt, profile, task-policy, source-corpus,
or model revision. The runner replaces `prompts.jsonl` and the final manifest,
but appends accepted, rejected, and raw-output rows. Reusing a directory after a
prompt change retains stale rows alongside regenerated rows; rerunning without
`--skip-present` appends duplicate work.

For an unchanged plan, `--skip-present` can continue the directory, and output
rows may then carry multiple run IDs. The manifest represents only the latest
invocation. Because it is written at the end, an interrupted directory can
contain useful appended rows without a current manifest or with a partial final
JSONL line. Validate JSONL integrity before continuing.

The `output` mapping in `configs/synthesis.yaml` does not control the current
runner. `--output-dir` selects the destination; JSONL and manifest output are
always written.

# 5. Run Phase 4 Quality

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

Use a fresh output directory and verify the input and raw paths first. Without
`--append`, Phase 4 clears existing filtered/review/rejected files before opening
the input; a later failure can leave an old manifest beside empty row outputs.

`--append` is not an aggregate-resume mode. It appends row files, but gates only
the current input and replaces the manifest and sample with current-batch-only
results. Do not pass an append-mode directory to packaging without rebuilding it
as one complete batch.

Near-duplicate and source-balance gates may move rows. Category, difficulty, and
taxonomy checks only report audit results. The command returns success after a
completed pass even for empty/all-rejected inputs or failed distribution audits,
so inspect manifest counts, final source shares, reference counts, and audit
flags before continuing.

Reference counts exist only in the run log, not the manifest. Keep that log for
release provenance. Treat scores as lexical ranking signals rather than proof of
correctness, and inspect issue codes alongside them. The duplicate gate does not
compare pairs with fewer than eight distinctive tokens, so separately inspect
short outputs. Phase 4 also does not range-check quality configuration values;
review weights, thresholds, tolerances, limits, and sample sizes before running.

# 6. Package Dataset

```bash
python -m scripts.package_dataset \
  --config configs/packaging_glm47_v3.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_v3
```

The current packager consumes only `filtered.jsonl`, rejects any row whose
embedded status is not `filtered`, assigns the configured reasoning/direct mix,
and then splits by `source_doc_id`.

Output:

```text
data/packaged/glm47_v3/train.jsonl
data/packaged/glm47_v3/validation.jsonl
data/packaged/glm47_v3/test.jsonl
data/packaged/glm47_v3/packaging_manifest.json
```

This model-specific view removes literal `[GENERAL KNOWLEDGE]` annotations,
maps canonical `<reasoning>` blocks to `<think>`, and runs response/tag
validation. Canonical synthesis and quality data is not modified.

# 7. Phase 6

Phase 6 has a working local training runner, a judge-only evaluator, and guarded
base-versus-tuned comparison. The first LoRA run completed but failed the
termination smoke gate and is rejected. V2 completed but regressed in
exploratory evaluation. V3, its isolated v4 rerun, and v5 completed training and
export, but the repository has no durable passing promotion-gate record. V6 is
staged but unrun. Calibrated evaluation is still pending.

First finalize a held-out benchmark:

```bash
evaluation/benchmark/
```

For the next candidate cycle, calibrate and freeze the judge before producing the comparison
scorecards. Existing base and v2 scorecards are uncalibrated diagnostics; do not
reuse them as final baseline or tuned evidence.

The evaluator always writes one local-judge scorecard. It can replay an existing
prediction JSONL keyed by `case_id`:

```json
{"case_id":"phase6-ai-atlas-001","prediction":"Candidate answer text"}
```

Use one row per selected benchmark case. The loader requires `prediction` and
rejects duplicate case IDs; `response`, `output`, and `answer` are not aliases.

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode prediction_file \
  --predictions data/evaluation/<predictions>.jsonl \
  --run-id <run_id> \
  --model-label glm47_flash_base
```

Configure the target endpoint under `generation` and the separate judge endpoint
under `scoring.judge` to call both local model servers directly:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <run_id> \
  --model-label glm47_flash_base
```

Set `generation.base_url` to the OpenAI API root, for example
`http://127.0.0.1:8080/v1`, not the full `/chat/completions` route. The client
appends `/chat/completions`. Configure a different API root under
`scoring.judge.base_url`; target and judge are separate clients and model
servers.

The runner processes cases sequentially. It generates one target response,
sends that response to the judge, checkpoints every output artifact, and
advances only after the verdict and checkpoint succeed. An interrupted run
therefore retains all fully evaluated cases with `in_progress` status. The final
case changes the scorecard and manifest status to `complete`.

Checkpointing is crash preservation, not resume support. A rerun does not load
completed cases from the existing output directory; reusing the same run ID can
replace the saved files starting with the first new checkpoint. Use a new run
ID, or deliberately replay a preserved prediction file, until explicit resume
logic is implemented.

Each checkpoint atomically replaces each of these files in sequence:

```text
predictions.jsonl
scorecard/case_results.jsonl
scorecard/scores.json
evaluation_manifest.json
```

The directory update is not transactional as a whole. A crash between file
replacements can leave different case counts across artifacts. The manifest is
written last; after interruption, treat it as the commit marker and reconcile
its case IDs/count with predictions, case results, and aggregate scores.

`openai_compatible` and `prediction_file` are the only accepted generation mode
names. Historical aliases such as `replay` and `predictions` are not accepted.

There is no statistical scorer and no parallel case runner. Each case declares
`target_output.format`; TTP, IOC, and ranking prompts request structured target
JSON for inspectability, while the local judge evaluates both content and
format. These formats do not calculate or claim F1 or NDCG. The judge receives
the full answer key, rubric, and `acceptable_variants`; each inner variant is a
complete independently valid alternative. Invalid judge JSON is retried
according to `scoring.judge.validation_retries`.

The target client logs an empty `content` response but does not retry or fail
the case; the judge will score the empty candidate. Inspect target
`finish_reason`, content length, and token limits in logs, especially for models
that can spend their full token budget in `reasoning_content`.

The client also discards response-model identity, finish reason, usage, and
reasoning content after logging them. A server model mismatch is a warning, not
a failure, and saved predictions contain the configured model name rather than
proof of the served model.

The dropout conversion is already fixed. Always select a versioned config
explicitly because the CLI default remains the historical v1 configuration:

```bash
python -m scripts.finetune \
  --config configs/<intended_versioned_finetune_config>.yaml
```

Use a fresh output directory. Preflight checks path existence but does not
validate package rows, reconcile counts, or verify split separation. Test JSONL
is not consumed by training. Check those contracts independently. Checkpoints
are not resumed, and the manifest is written only after adapter and GGUF export;
partial artifacts may therefore exist without current manifest metadata.

After training, load the direct adapter and run bounded greeting and DFIR
prompts. Every successful run already saves the adapter and GGUF; require a
model-defined stop token before promoting or serving that GGUF. Preserve
`model.generation_config.eos_token_id`: GLM uses a list, including `<|user|>`
and `<|observation|>` as generation boundaries. Do not reduce it to scalar
`tokenizer.eos_token_id`.

The current smoke script points at v5 and preserves the model stop list, but it
runs only `hello`, prints rather than enforces success, and currently reports
all generated IDs as though they were stop IDs. A zero exit code is not a
passing release gate; correct that report, add the documented DFIR, repetition,
and template-leakage checks, and record their result.

Then rerun the same evaluator against the fine-tuned model and compare:

```bash
python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

The comparison accepts only complete scorecards and rejects a changed judge
protocol/configuration fingerprint or calibration ID. Qualitatively review
critical regressions before deployment.

It does not fingerprint target prompts, sampling/token settings, structured
output policy, request overrides, endpoint, prediction file, or served model.
Archive and compare those inputs separately for both runs. Judge `criteria` are
free-form explanations; only their numeric ranges are checked, not their names,
sum, or agreement with the scalar score.

The current comparison code does not reject the literal calibration ID
`uncalibrated`; it only requires the two IDs to be present and equal. Treat the
non-placeholder calibration requirement as a release policy until that check is
enforced in code.

The comparison command also exits 0 when its JSON reports
`passes_regression_gate: false`. CI and release scripts must parse that field and
fail explicitly.

The current `data/evaluation/glm47-flash-base/` run is complete at `0.7588`, but
its calibration ID is `uncalibrated`. Do not compare it as a final baseline.
Calibrate and freeze the judge, then produce new complete base and tuned runs.

Record the exact training configuration, checkpoint paths, and results in
[Training And Release](../developer/training-and-release.md), the generated training
manifest, and `project_state/TODO.md`.
