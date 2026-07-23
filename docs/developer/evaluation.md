<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Evaluation</h1>

Evaluation measures held-out DFIR behavior with a separately served local LLM
judge. This page owns benchmark design, judge calibration, generation and replay
contracts, checkpointing, comparison, and promotion decisions.

# Visual Overview

## Macro View

<puml src="../diagrams/evaluation-macro.puml" alt="Macro view of held-out evaluation and comparison" width="900" />

## Benchmark Case Detail

<puml src="../diagrams/evaluation-case-detail.puml" alt="Detailed benchmark case contract" width="650" />

## Scoring And Checkpoint Detail

<puml src="../diagrams/evaluation-checkpoint-detail.puml" alt="Detailed target scoring and checkpoint sequence" width="750" />

## Comparison Detail

<puml src="../diagrams/evaluation-comparison-detail.puml" alt="Detailed base and tuned comparison flow" width="550" />

# Release Evidence Flow

1. Build and manually review original held-out cases.
2. Calibrate and freeze the judge on a separate human-scored set.
3. Freeze the benchmark, target prompt, inference settings, endpoints, served
   model identity, judge settings, and calibration ID.
4. Run a complete base-model evaluation.
5. Train a candidate and pass the
   [direct-adapter gate](finetuning.md#direct-adapter-gate).
6. Run the tuned artifact with the same frozen evaluation inputs.
7. Compare compatible complete scorecards.
8. Review aggregate, task-level, and severe case regressions.
9. Record an explicit promotion or rejection decision and rollback path.

# Benchmark Case Contract

`evaluation/schemas.py` defines `BenchmarkCase`. Each JSONL case contains:

| Field | Rule |
|---|---|
| `case_id` | Stable unique ID |
| `task_type` / `difficulty` | Stratification labels |
| `prompt` / `context` | Target-visible task and self-contained evidence |
| `target_output.format` | `free_form`, `techniques_json`, `iocs_json`, or `ranked_actions_json` |
| `expected_answer` | Judge-only concepts, exclusions, variants, and gold labels |
| `scoring` | Positive maximum score and local-judge rubric |
| `tags` / reviewer notes | Coverage and human-review context |

The answer key is never sent to the target model.

Use atomic `required_concepts` with short aliases and a human description.
Use `forbidden_concepts` for important overclaims or errors. Keep
`must_include` and `must_not_include` as concise judge-facing cues, not prose
answers or substring rules. Store structured technique IDs, IOCs, and action
orders in `gold_labels`.

Each inner list in `acceptable_variants` is one complete independently valid
alternative. It is not an additional cumulative requirement.

Structured target formats help the judge inspect labels separately from prose:

- TTP: `{"techniques": [...], "answer": "..."}`
- IOC: `{"iocs": [{"type": "...", "value": "..."}], "answer": "..."}`
- Ranking: `{"ranked_actions": [...], "answer": "..."}`

The evaluator still produces an LLM-judge rubric score. It does not calculate
precision/recall, F1, DCG, or NDCG. Returned `criteria` are explanatory
metadata: names are free-form, values are only range-checked, and they are not
reconciled with the scalar verdict.

# Benchmark Coverage And Review

Cover at least:

- ATT&CK/ATLAS TTP identification;
- IOC extraction with benign lookalikes;
- triage and hunting prioritization;
- detection-rule interpretation across endpoint, Linux, cloud, and SaaS;
- artifact analysis with uncertainty and anti-forensics;
- incident report generation;
- grounding and overclaim stress tests;
- AI/LLM and agent-tool incidents.

Cases must be original, realistic, answerable from their included evidence, and
absent from training inputs. Include ambiguous, false-positive, incomplete-log,
and unsafe-action cases rather than only clean textbook examples.

Before freezing a benchmark:

1. validate every JSONL row and stable ID;
2. have a DFIR reviewer check prompt realism and answer-key correctness;
3. ensure aliases do not reward a wrong answer;
4. ensure forbidden concepts target material errors;
5. verify expected structured output and labels;
6. review task, platform, difficulty, and critical-behavior coverage;
7. record benchmark fingerprint, owner, review date, and freeze ID.

Benchmark coverage measures behavior, while quality/package coverage measures
training material. Review both independently.

# Evaluation Configuration

`configs/evaluation.yaml` owns:

- benchmark path and output base directory;
- target system message and context wrapper;
- `openai_compatible` generation or `prediction_file` replay;
- configured target model, sampling, token limit, timeout, and overrides;
- structured-output enablement;
- separately served judge model, inference settings, response format, retries,
  and `calibration_id`.

Both base URLs are API roots such as `http://127.0.0.1:8080/v1`; the client
appends `/chat/completions`. Put server-specific fields under
`request_overrides`. Overrides win over duplicated standard settings.

The complete judge mapping contributes to compatibility fingerprints. Target
prompt, endpoint, overrides, prediction file, and effective model reported by
the server are not all fingerprinted. Archive the full effective target and
judge configuration and server logs separately.

Configuration is untyped. Review retry counts, timeouts, token limits, sampling,
model labels, URLs, output paths, and calibration identity before running.

# Judge Calibration

Deterministic temperature is not calibration. Build a separate stratified set
of good, borderline, unsafe, incomplete, overconfident, and verbose answers
across every task. Have at least two DFIR reviewers score it independently,
then adjudicate disagreements.

Measure agreement with human labels using appropriate ordinal and ranking
statistics, and explicitly measure recall of critical errors. Test repeated
judgement, paraphrase stability, verbosity bias, answer-order bias,
prompt-injection resistance, and quantization sensitivity.

Tune judge prompt/rubric only on a calibration split. Freeze model,
quantization, chat template, prompt, sampling, request overrides, and server
build under a real versioned `calibration_id`, then report on an untouched
holdout. The benchmark used for base-versus-tuned comparison must not be the
judge-fitting set.

# Running And Replaying

Generate and judge a target:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <run_id> \
  --model-label <model_label>
```

Replay saved answers with exactly one row per selected case:

```json
{"case_id":"phase6-ai-atlas-001","prediction":"Candidate answer text"}
```

Duplicate IDs, missing selected cases, or historical aliases such as `response`
and `answer` are rejected.

After each successful verdict, the evaluator atomically replaces these files
one at a time:

| Output | Meaning |
|---|---|
| `predictions.jsonl` | Target text keyed by case ID |
| `scorecard/case_results.jsonl` | Validated verdict per completed case |
| `scorecard/scores.json` | Aggregate/task scores, identities, and progress |
| `evaluation_manifest.json` | Run identity, case progress, status, and scorecard paths |

The four writes are sequential, not one transaction. After interruption, treat
the manifest as the last commit marker and reconcile case IDs/counts across all
files. `in_progress` output is recoverable diagnostic evidence, not comparable
release evidence.

# Base And Tuned Comparison

Run the base and tuned artifacts with identical benchmark, target prompt,
generation settings, judge, calibration ID, and effective serving behavior.
Then:

```bash
python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

Comparison accepts only complete compatible scorecards. It writes
`passes_regression_gate` but currently returns exit code zero for either pass or
fail; automation must parse the field.

An aggregate improvement cannot override material task-level or critical DFIR
regressions. Review individual severe cases, termination behavior, grounding,
overclaiming, destructive recommendations, structured-output correctness, and
qualitative response usability.

# Changing Evaluation

For a benchmark change, create or modify cases, validate schemas, perform human
review, rerun coverage analysis, and assign a new benchmark identity. Do not
silently edit a frozen set used in a comparison claim.

For an evaluator or judge-policy change:

1. add focused client, parsing, checkpoint, and comparison tests;
2. recalibrate the changed judge configuration;
3. assign a new calibration identity;
4. run a small end-to-end case set including malformed judge output, empty
   target output, interruption, and replay;
5. confirm partial status and compatibility rejection;
6. rerun both baseline and tuned evaluations.

Use fresh run directories. Preserve exact benchmark, configs, logs, served-model
identity, predictions, verdicts, scorecards, and comparison output.

# Promotion Record

Retain candidate/config/package identity, environment and artifact hashes,
enforcing direct-adapter result, complete compatible base/tuned scorecards,
overall and task deltas, severe-case review, reviewer/date, decision rationale,
and rollback path. Update [Current State](../current-state/index.md) for the live
decision and [Revisions](../current-state/revisions.md) for superseded evidence.
