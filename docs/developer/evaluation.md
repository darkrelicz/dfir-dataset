<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Evaluation</h1>

Evaluation measures held-out DFIR behavior, records one independently judged
score per case, and compares complete base and tuned runs. This page explains
the evaluation architecture and traces it to the current implementation. It is
the starting point for changing benchmark cases, target inference, judge
policy, scoring, checkpoint artifacts, compatibility, or promotion thresholds.

## Architecture

Evaluation has two execution paths and one comparison path:

1. the **generation path** sends each held-out case to a served target model;
2. the **replay path** reads previously generated answers from JSONL;
3. both paths send the target answer and judge-only answer key to a separately
   served local LLM judge, checkpoint results, and produce the same scorecard;
4. comparison accepts two complete compatible scorecards and calculates overall
   and task-level deltas.

The target and judge are deliberately separate trust boundaries. The target
receives the task, context, system prompt, and requested output shape. It never
receives `expected_answer` or the scoring rubric. The judge receives the full
case, target prediction, answer key, and rubric.

<puml src="../diagrams/evaluation-macro.puml" alt="Macro view of held-out evaluation and comparison" width="900" />

### Component Ownership

| Component | Implementation responsibility |
|---|---|
| `scripts/run_evaluation.py` | CLI parsing, logging setup, and expected user-error exit code |
| `evaluation/runner.py` | Configuration resolution, case orchestration, fingerprints, prompt construction, and checkpoint writes |
| `evaluation/schemas.py` | Pydantic contracts for benchmark cases, verdicts, case scores, and manifests |
| `evaluation/model_clients.py` | Prediction replay and minimal OpenAI-compatible chat-completions transport |
| `evaluation/structured_output.py` | Target-format instructions and tolerant JSON-object extraction |
| `evaluation/judge.py` | Judge prompt, response validation, correction retries, and judge identity |
| `evaluation/scoring.py` | Per-case normalization and aggregate/task means |
| `evaluation/comparison.py` | Scorecard compatibility, regression thresholds, and comparison reports |
| `scripts/compare_evaluations.py` | Comparison CLI |
| `configs/evaluation.yaml` | Active benchmark, target prompt/inference, judge, calibration, and output policy |
| `evaluation/benchmark/*.jsonl` | Held-out cases and judge-only expected answers |

There is no plugin registry for targets, judges, metrics, or benchmark formats.
The runner selects one of two clients by the `generation.mode` string, and the
judge always uses `OpenAICompatibleClient`. Adding another backend is therefore
a code change in `model_clients.py` and its construction path, not only a YAML
change.

### Runtime Flow

`run_evaluation()` performs the following sequence:

1. loads untyped YAML from `--config`;
2. resolves CLI overrides for cases, output, run ID, mode, prediction file,
   requested model, and model label;
3. creates the target client and local judge client;
4. loads and validates the selected cases;
5. optionally slices the loaded list with `--max-cases`;
6. fingerprints that final selected case set;
7. constructs target messages for each case in sequence;
8. generates or replays one prediction;
9. asks the judge for one validated verdict;
10. builds and appends one normalized `CaseScore`;
11. rewrites all checkpoint artifacts after the successful verdict;
12. marks the last checkpoint `complete` and prints the aggregate score.

Cases are processed serially. Target requests, judge requests, and checkpoint
writes are not parallelized.

<puml src="../diagrams/evaluation-checkpoint-detail.puml" alt="Detailed target scoring and checkpoint sequence" width="750" />

### Trust And Reproducibility Boundaries

- Benchmark content determines what behavior is measured.
- Target prompt, inference settings, served artifact, and chat template
  determine the generated prediction.
- Judge prompt, model, quantization, inference settings, server behavior, and
  calibration determine the verdict.
- Scoring and comparison code determine how verdicts become a gate.

The implementation fingerprints benchmark content and the complete configured
judge mapping plus a hard-coded judge protocol version. It does **not**
fingerprint the target prompt, target endpoint, target overrides, prediction
file, target server build/chat template, code revision, or effective model
reported by either server. Preserve those separately for any release claim.

## Benchmark Implementation

### Case Loading And Validation

`evaluation.runner.load_cases()` accepts either one JSONL file or a directory.
For a directory it reads every top-level `*.jsonl` file in sorted filename
order, concatenates their rows, and validates each row as `BenchmarkCase`.
Subdirectories and non-JSONL files are ignored.

`validate_cases()` currently enforces only:

- the selected benchmark is non-empty;
- `case_id` values are unique across the selected files.

Pydantic enforces field types, the supported `target_output.format` values, and
positive `scoring.max_points`. It does not enforce non-empty IDs/prompts,
controlled task or difficulty vocabularies, globally unique concept IDs,
benchmark/train separation, or coverage targets. Those remain authoring and
review responsibilities.

`--max-cases N` slices the concatenated list before validation and
fingerprinting. A smoke subset therefore has its own fingerprint and cannot be
compared with a complete benchmark run.

### Benchmark Case Contract

<puml src="../diagrams/evaluation-case-detail.puml" alt="Detailed benchmark case contract" width="650" />

| Field | Runtime use |
|---|---|
| `case_id` | Stable prediction key, score key, duplicate check, and compatibility identity |
| `task_type` | Logging and task-level aggregation |
| `difficulty` | Coverage metadata; not used in scoring |
| `prompt` / `context` | Target-visible question and evidence |
| `target_output.format` | Selects an optional target-facing format instruction |
| `expected_answer` | Judge-only concepts, exclusions, acceptable variants, and gold labels |
| `scoring.max_points` | Judge range and per-case normalization denominator |
| `scoring.rubric` | Judge-visible free-form rubric |
| `tags` / reviewer notes | Review metadata; not used at runtime |

Supported output formats are `free_form`, `techniques_json`, `iocs_json`, and
`ranked_actions_json`. Structured cases receive a natural-language JSON
instruction when `generation.structured_outputs.enabled` is true:

- TTP: `{"techniques": [...], "answer": "..."}`
- IOC: `{"iocs": [{"type": "...", "value": "..."}], "answer": "..."}`
- ranking: `{"ranked_actions": [...], "answer": "..."}`

This is a prompt contract, not an output validator. The target response remains
a raw string; the evaluator does not parse its JSON, calculate label
precision/recall, or reject a malformed structured answer before judging.

Use atomic `required_concepts` and `forbidden_concepts`, with short aliases and
an optional human description. Each inner list in `acceptable_variants` is one
complete independently valid alternative. `must_include` and
`must_not_include` are judge-facing cues, not substring checks. Structured
labels belong in `gold_labels`.

### Fingerprinting

`fingerprint_cases()` sorts validated cases by `case_id`, serializes their full
Pydantic representation as canonical JSON, and calculates SHA-256. Consequently
the fingerprint includes target-visible content, answer keys, rubric, tags,
review notes, and Pydantic defaults; it is independent of source-file ordering.
Any of those content changes creates a different comparison identity.

### Coverage And Freeze Review

Cover TTP identification, IOC extraction, prioritization, detection
interpretation, artifact analysis, reporting, uncertainty/overclaim behavior,
and AI/LLM or agent-tool incidents. Include ambiguous evidence, benign
lookalikes, incomplete logs, false positives, and unsafe-action traps.

Before freezing a benchmark:

1. validate every row and stable ID;
2. have a DFIR reviewer check realism and answer-key correctness;
3. verify aliases cannot reward an incorrect answer;
4. verify forbidden concepts identify material errors;
5. review the expected output contract and structured labels;
6. inspect task, platform, difficulty, and critical-behavior coverage;
7. prove benchmark cases are absent from collection and training inputs;
8. record the full fingerprint, owner, review date, and freeze ID.

Benchmark coverage measures model behavior. Quality and package coverage measure
training material; neither substitutes for the other.

## Configuration And CLI

Run target generation and judging with an explicit config and run ID:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <run_id> \
  --model-label <model_label>
```

The CLI defaults `--config` to `configs/evaluation.yaml`. CLI values override
the corresponding benchmark/generation/output values, and the resolved
`--model` is written back into the generation mapping before the client is
built.

| Config section | Current consumers |
|---|---|
| `benchmark.cases_path` | Default case file or directory |
| `output.base_dir` | Parent for generated run IDs |
| `prompt.system_message` | Optional target system message |
| `prompt.include_context_heading` | Whether target context is prefixed with `Context:` |
| `generation.mode` / `predictions_path` | Target client selection and replay input |
| `generation.model` / `model_label` | Request model and human-facing candidate label |
| `generation.base_url` / sampling / token / timeout settings | Target HTTP request |
| `generation.response_format` / `request_overrides` | Optional target server request fields |
| `generation.structured_outputs.enabled` | Target-facing JSON instructions |
| `scoring.judge` | Judge transport, inference, retries, fingerprint, and calibration identity |

Both base URLs are API roots such as `http://127.0.0.1:8080/v1`; the client
appends `/chat/completions`. `request_overrides` is merged last and can override
temperature, `top_p`, token limits, response format, and other non-reserved
fields. It may not replace `messages` or `model`.

Configuration is loaded as an untyped mapping. Client constructors convert
selected values with `str`, `int`, and `float`, but there is no complete config
schema or preflight. Review booleans, URLs, retry counts, timeouts, model names,
output paths, and calibration identity before a long run.

The runner derives a default run ID as
`eval-<UTC timestamp>-<slugged model label>`. It does not reject an existing
output directory. Reusing a run ID can overwrite artifacts and mix identities;
use a fresh directory for every run.

## Target Generation And Replay

### Prompt Construction

`build_messages()` adds the configured system message when non-empty, then one
user message containing:

1. optional context, with a `Context:` heading by default;
2. the case prompt under `Question:`;
3. the structured-output instruction when enabled and applicable.

The target never receives `expected_answer`, `scoring`, difficulty, tags, or
reviewer notes. Message formatting here is separate from the chat template
applied by the serving stack; both must be frozen for a controlled comparison.

### OpenAI-Compatible Client

`OpenAICompatibleClient.generate()` sends a synchronous
`POST <base_url>/chat/completions` with model, messages, temperature, `top_p`,
and `max_tokens`. It optionally adds:

- `Authorization: Bearer ...` from `api_key_env`, which defaults to
  `OPENAI_API_KEY`;
- normalized `response_format`;
- server-specific `request_overrides`.

It calls `raise_for_status()`, then reads only `choices[0].message.content`.
String and OpenAI-style multipart text content are supported. Reasoning fields,
finish reason, response model, and usage are logged but are not stored in
`predictions.jsonl`. A served-model mismatch produces a warning only.

Empty target `content` also produces only a warning and is passed to the judge.
There is no target HTTP retry, empty-response retry, content-length check,
finish-reason gate, or structured-output validation. Transport, JSON-shape, or
missing-choice errors stop the run.

### Prediction Replay

Replay input uses one JSON object per line:

```json
{"case_id":"phase6-ai-atlas-001","prediction":"Candidate answer text"}
```

`load_prediction_file()` rejects a missing file, missing `case_id`, duplicate
ID, or missing `prediction`. It converts predictions to strings. Historical
keys such as `response` and `answer` are not accepted.

Every selected case must have a prediction; that check occurs when the case is
processed. Extra prediction IDs are accepted and ignored. The evaluator still
contacts the configured judge and creates a new scorecard:

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --mode prediction_file \
  --predictions <predictions.jsonl> \
  --run-id <replay_run_id>
```

Replay isolates judging from target generation, but the prediction-file
contents are not included in compatibility metadata. Hash and archive the
input file.

## Judge And Scoring Implementation

### Judge Boundary

`LocalLLMJudge` always wraps a second `OpenAICompatibleClient` using the entire
`scoring.judge` mapping. Its system prompt tells the judge to treat target
content and incident context as untrusted data and to return JSON only. The
user message includes:

- question and context;
- raw candidate answer;
- complete expected-answer key;
- target output contract;
- scoring maximum and rubric.

The judge must return `score`, a non-empty `reason`, a `criteria` mapping, and
an optional zero-based `matched_acceptable_variant`.

### Verdict Parsing And Retries

`parse_json_object()` accepts a complete JSON object, an object inside a JSON
code fence, or the first decodable object embedded in other text.
`parse_judge_verdict()` then enforces:

- the Pydantic `JudgeVerdict` shape;
- `score` within `0..max_points`;
- every free-form criterion value within the same range;
- a matched variant index within the available variants;
- a non-empty reason.

When validation fails, the judge receives its invalid response plus a
correction message. `validation_retries: 1` means one initial attempt and one
correction attempt. These retries cover parse/schema/range failures only; HTTP
and response-envelope failures are not retried. Exhaustion raises `ValueError`
and leaves the previous successful checkpoint in place.

Criterion names and values are explanatory metadata. They are neither required
to match the case rubric nor reconciled with the scalar verdict.

### Score Calculation

`build_case_score()` defensively clamps the judge score into the valid range,
rounds it to four decimals, and stores:

```text
normalized_score = round(score / max_points, 4)
```

`aggregate_scores()` calculates:

- each task score as the unweighted mean of its cases' rounded normalized
  scores;
- overall score as the unweighted mean of **all cases**, not the mean of task
  means;
- sorted case IDs and the benchmark fingerprint.

Difficulty, tags, task rarity, rubric entries, and criticality do not alter the
weight. The current evaluator does not compute precision, recall, F1, DCG,
NDCG, confidence intervals, inter-run variance, or deterministic rule-based
checks.

### Judge Identity And Calibration

`judge_reproducibility_metadata()` hashes canonical JSON containing:

- `JUDGE_PROTOCOL_VERSION`, currently
  `phase6-judge-v3-target-output`;
- the complete raw `scoring.judge` configuration.

It also records `judge_calibration_id`, defaulting to `uncalibrated`. Changing
any judge mapping value or the protocol version makes scorecards incompatible.
The fingerprint proves configured equality, not that the same server binary,
weights, quantization, or chat template actually served both runs.

Deterministic temperature is not calibration. Create a separate, stratified
human-scored calibration set with good, borderline, unsafe, incomplete,
overconfident, and verbose answers. Use at least two DFIR reviewers and
adjudicate disagreements. Measure ordinal agreement, critical-error recall,
repeated-judgement stability, paraphrase and verbosity bias, answer-order bias,
prompt-injection resistance, and quantization sensitivity.

Tune only on a calibration split. Freeze the model, artifact hash,
quantization, chat template, judge prompt/protocol, inference mapping, server
build, and a real versioned `calibration_id`; report agreement on an untouched
holdout. Do not use the base-versus-tuned benchmark to fit the judge.

## Checkpoints And Run Artifacts

After each successfully judged case, `write_evaluation_checkpoint()` replaces
four artifacts in this order:

| Write order | Output | Contents |
|---:|---|---|
| 1 | `predictions.jsonl` | Completed raw target texts and configured model identities |
| 2 | `scorecard/case_results.jsonl` | Completed validated `CaseScore` rows |
| 3 | `scorecard/scores.json` | Aggregate/task scores, progress, benchmark identity, and judge identity |
| 4 | `evaluation_manifest.json` | Run metadata, case IDs/count, status, and scorecard summary/paths |

Each file uses a sibling `.tmp` followed by `Path.replace()`, so each individual
replacement is atomic on the same filesystem. The four-file sequence is not a
transaction. Treat the manifest, written last, as the checkpoint commit marker
and reconcile all case IDs and counts after interruption.

The manifest status is `in_progress` until the final selected case succeeds.
Partial artifacts are diagnostic evidence and comparison rejects them.

The current runner does **not** resume from a checkpoint. A restart initializes
empty prediction and score lists and begins at the first case; when it reaches
its first successful verdict it overwrites the existing artifacts. Preserve or
move an interrupted directory, then start a fresh run or replay its saved
predictions explicitly.

The manifest stores configured model identity but not the effective response
model, prompts, generation settings, target endpoint, finish reasons, token
usage, server logs, source revision, or artifact hashes. Archive those alongside
the run.

## Base And Tuned Comparison

Serve and evaluate the base and tuned artifacts with the same benchmark, target
prompt, target settings, judge, calibration ID, and effective serving behavior:

```bash
python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline_run> \
  --tuned-dir data/evaluation/<tuned_run> \
  --output-dir data/evaluation/comparisons/<comparison_name>
```

<puml src="../diagrams/evaluation-comparison-detail.puml" alt="Detailed base and tuned comparison flow" width="550" />

### Compatibility Checks

`validate_compatible_scorecards()` loads only each run's
`scorecard/scores.json` and requires:

- both `run_status` values are `complete`;
- equal non-empty benchmark fingerprints;
- identical sorted case-ID lists;
- identical task-type key sets;
- matching judge protocol versions;
- matching judge-config fingerprints;
- matching calibration IDs.

It does not verify target prompts/settings, target or judge server identity,
model artifact hashes, code revision, per-case task assignments, case-result
rows, or manifest consistency. Operational review must establish those
additional equivalences.

### Regression Gate

For every task:

```text
task_delta = tuned_task_mean - baseline_task_mean
severe regression when task_delta < -max_task_regression
```

The overall gate is:

```text
overall_delta > minimum_overall_delta AND no severe task regressions
```

Both comparisons are strict. With defaults, an exactly zero overall delta
fails, while an exactly `-0.05` task delta passes the `0.05` regression limit.

The comparison writes `comparison.json` and `comparison.md`. It reports only
aggregate and task-level changes; it does not calculate paired per-case deltas
or identify severe individual cases. Human review must inspect
`case_results.jsonl` and predictions for grounding, overclaiming, destructive
advice, termination, structured-output correctness, and usability.

`compare_evaluations()` returns exit code zero whether
`passes_regression_gate` is true or false. CI and release automation must parse
that field and fail explicitly. The output is quantitative gate evidence, not
by itself a promotion decision.

## Changing Evaluation

Use this ownership map before editing:

| Desired change | Primary edit location | Also reconsider |
|---|---|---|
| Add or revise held-out behavior | `evaluation/benchmark/*.jsonl` | Human review, leakage check, fingerprint/freeze ID, rerun both models |
| Add a benchmark field or output format | `evaluation/schemas.py` | Prompt construction, judge payload, fingerprint, existing cases |
| Change target prompt assembly | `evaluation/runner.py::build_messages` | Target compatibility metadata and both base/tuned runs |
| Add target output instructions | `evaluation/structured_output.py` | Target parser/validator if enforcement is required |
| Add a target backend | `evaluation/model_clients.py` | `build_client`, CLI/config validation, reproducibility metadata |
| Change HTTP request or response parsing | `evaluation/model_clients.py` | Judge also uses this client; add target and judge tests |
| Change judge policy or payload | `evaluation/judge.py` | Protocol version, recalibration, both base/tuned runs |
| Change verdict schema | `evaluation/schemas.py`, `evaluation/judge.py` | Retry behavior, stored case results, protocol version |
| Add deterministic metrics | `evaluation/scoring.py` | Case schema/gold labels, scorecard schema, comparison |
| Change weighting or aggregates | `evaluation/scoring.py` | Scorecard compatibility/versioning and gate thresholds |
| Change checkpoint/resume behavior | `evaluation/runner.py` | Cross-file consistency, collision handling, interruption tests |
| Change compatibility or gates | `evaluation/comparison.py` | Comparison report, CI exit behavior, prior scorecards |
| Change active endpoints/policy | `configs/evaluation.yaml` | Calibration identity, secrets, archived effective config |

For any evaluator or judge-policy change:

1. add focused schema, client, prompt, parser, scoring, checkpoint, and
   comparison tests;
2. increment the judge protocol when verdict semantics or judge instructions
   change;
3. recalibrate any changed judge configuration or protocol;
4. test malformed judge JSON, out-of-range scores, retry exhaustion, empty
   target content, HTTP failure, duplicate/missing replay rows, and interruption;
5. confirm partial scorecards are rejected and incompatible identities fail;
6. run both baseline and tuned evaluations from fresh directories.

There is currently no evaluation test suite in the repository. Implementation
changes therefore require adding tests rather than relying only on a full
68-case run against live servers.

## Release Evidence

A release-quality sequence is:

1. build, validate, and manually review original held-out cases;
2. calibrate and freeze the judge on separate human-scored data;
3. freeze benchmark, target prompt/settings, serving stack, judge, and code;
4. run a complete base-model evaluation;
5. train the candidate and pass the
   [direct-adapter gate](finetuning.md#direct-adapter-gate);
6. run the tuned artifact under the same effective evaluation conditions;
7. compare complete compatible scorecards;
8. review aggregate, task, and paired severe-case behavior;
9. record an explicit promotion or rejection decision and rollback path.

Retain candidate/package identity, environment and model hashes, effective
target and judge configuration, server logs, calibration evidence, benchmark
fingerprint, direct-adapter result, both complete run directories, comparison
outputs, severe-case review, reviewer/date, rationale, and rollback path.

Update [Current State](../current-state/index.md) for the live decision and
[Revisions](../current-state/revisions.md) for superseded evidence.
