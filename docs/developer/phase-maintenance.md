<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Phase Maintenance Guide</h1>

Use this guide when changing the pipeline. It follows the dependency order from
taxonomy through evaluation and states what to edit, what can break, how to
verify the change, and which UML view explains the phase.

# Change Discipline For Every Phase

Before editing:

1. Read `project_state/PROJECT_BRIEF.md`, `TODO.md`, `DECISIONS.md`, and
   `DESIGN_SYSTEM.md`.
2. Read the current phase section below and its linked specialist page.
3. Inspect the active input and output manifests. Never infer run counts from
   filenames alone.
4. Give experimental output a new directory. Preserve canonical and rejected
   diagnostic artifacts for provenance.

After editing:

1. run the smallest no-network check first, then a pilot/smoke run;
2. compare schemas, counts, distributions, and manifests with the previous run;
3. rebuild the docs if a command, contract, config, phase boundary, or output
   changes;
4. update current state and durable project state when status, direction,
   accepted risk, or remaining work changes.

<puml src="../diagrams/end-to-end-sequence.puml" alt="End-to-end phase sequence" width="1000" />

# Phase 1: Taxonomy And Task Design

## Responsibility

Phase 1 defines what the dataset covers and what behavior the model learns. It
has no standalone runner. Its outputs constrain planning, validation, quality
audits, documentation, and benchmark coverage.

## Files To Update

| Change | Required Files |
|---|---|
| Add or rename an artifact category | `docs/reference/taxonomy.md`, `configs/quality.yaml` |
| Change coverage strength | `configs/quality.yaml`, `docs/developer/coverage-map.md` |
| Add or rebalance a task category | `configs/task_categories.yaml`, corresponding `synthesizers/prompts/categories/*.md` |
| Change source/category eligibility | `configs/source_profiles.yaml` |
| Change quality signals for a task | `configs/task_categories.yaml` |
| Add held-out behavior coverage | `evaluation/benchmark/*.jsonl`, `docs/developer/benchmark-design.md` |

## Update Procedure

1. Define the human meaning, examples, exclusions, and neighboring categories
   in the taxonomy page.
2. Add the same stable ID to exactly one machine-readable domain in
   `configs/quality.yaml`; place it in one coverage bucket.
3. If the category should be generated now, map relevant sources/content types
   through `configs/source_profiles.yaml` and adjust task targets.
4. Update or add the task prompt. A new model behavior requires a category
   prompt; a taxonomy ID alone does not.
5. Review deterministic taxonomy assignment in `synthesizers/prompt_builder.py`
   and config parsing in `synthesizers/prompt_policy.py`.
6. Add benchmark cases only when they can remain held out from source-derived
   training data.

## Checks And Pitfalls

- IDs are public data contracts. Renaming one invalidates old synthesized and
  quality records; prefer adding a new ID and documenting migration.
- Category target fractions and difficulty target fractions must each sum to
  one.
- Do not mark coverage strong merely because a source mentions a topic; strong
  means sufficient operational examples for grounded generation.
- A task category describes model behavior; a taxonomy category describes DFIR
  subject matter. Do not collapse the two.
- Run prompt rendering after any taxonomy/profile/task change and inspect the
  planned category, difficulty, and taxonomy distributions before API use.

```bash
python -m scripts.synthesize render-prompts \
  --mode pilot \
  --limit 50 \
  --output-dir data/synthesized/taxonomy_change_preview
```

## UML

<puml src="../diagrams/phase1-taxonomy.puml" alt="Phase 1 taxonomy and policy relationships" width="950" />

See also [Taxonomy](../reference/taxonomy.md),
[Configuration](configuration.md), and [Coverage Map](coverage-map.md).

# Phase 2: Collection

## Responsibility

Phase 2 turns heterogeneous public sources into one `RawDocument` JSONL file
per source plus a combined collection manifest. The shared base handles output,
IDs, dates, Git helpers, errors, warnings, and manifest timing; concrete
collectors own source parsing.

## Files To Update

| Change | Required Files |
|---|---|
| Source URL/path/filter | `configs/collection.yaml` |
| Existing parser | `collectors/<source>.py` |
| Shared collector behavior | `collectors/base.py`, possibly `collectors/schemas.py` |
| Add source | collector module, config, `scripts/collect_all.py`, source profile, docs |
| Raw contract | `collectors/schemas.py` and every downstream reader |

## Update Procedure

1. Decide the logical document boundary. One row should contain one coherent
   unit; for example, Atomic Red Team emits one row per atomic test.
2. Keep network location, local cache/clone path, output path, and source
   filters in `configs/collection.yaml`.
3. Extend `BaseCollector`; produce complete `RawDocument` objects with stable
   `doc_id`, source URL, collection/publish dates, content type, Markdown, and
   source-specific metadata.
4. Write through `_write_documents`; do not create a competing output format.
5. Register the collector in `scripts/collect_all.py`. A config entry alone is
   not discoverable by the CLI.
6. Add its synthesis profile and document its tier, purpose, thin/rich behavior,
   and expected content types.

## Checks And Pitfalls

- Run `--source` before all collectors. Inspect errors and warnings as well as
  document count.
- Run the same collector twice and check stable IDs and sensible count drift.
- Git repositories belong under `data/raw/.repos/`; downloaded references
  belong under `.cache/`.
- Preserve full source content. Truncation and compaction belong in Phase 3.
- Use safe YAML parsing. Avoid adding a heavy translator when metadata parsing
  is enough.
- Changes to `RawDocument` cascade through prompt planning, quality source
  lookup, contracts, and old raw files.

```bash
python -m scripts.collect_all --source <source>
python -m scripts.synthesize validate-raw --raw-dir data/raw
```

Compare the new collector entry and total in
`data/raw/collection_manifest.json`. A single-source run rewrites the combined
manifest with only that invocation's results, so do not mistake it for a
full-corpus manifest.

## UML

<puml src="../diagrams/collector-inheritance.puml" alt="Collector class hierarchy" width="950" />

See [Collectors](collectors.md) and [Adding Sources](adding-sources.md).

# Phase 3: Synthesis

## Responsibility

Phase 3 selects raw documents, assigns task category/difficulty/taxonomy hints,
compacts a prompt-only source view, renders prompts, calls Gemini sequentially,
and validates structured candidate pairs inline.

## Files To Update

| Concern | Files |
|---|---|
| Model, pair caps, retries, source length | `configs/synthesis.yaml` |
| Source eligibility/richness/content overrides | `configs/source_profiles.yaml` |
| Task distribution/signals | `configs/task_categories.yaml` |
| Selection and balancing | `synthesizers/planner.py`, `synthesizers/sampler.py` |
| Prompt composition | `synthesizers/prompt_builder.py`, `synthesizers/prompt_policy.py` |
| Prompt language | `synthesizers/prompts/base.md` and targeted category/source/content templates |
| Prompt compaction | `synthesizers/prompts/compactors/` |
| Teacher API | `synthesizers/clients/gemini.py` |
| Run/resume behavior | `synthesizers/runner.py`, `synthesizers/run_state.py`, `synthesizers/io.py` |
| Inline validation | `synthesizers/validators.py`, shared `validation/` primitives |

## Update Procedure

1. Change policy in YAML or prompt assets when possible; keep the CLI thin.
2. If changing selection, preserve source-aware pilot sampling and explicit
   category/difficulty assignment before `PromptBuilder`.
3. Add a content-type prompt only when its behavior differs materially from
   its broad source type.
4. Add a source compactor as
   `synthesizers/prompts/compactors/<source>_compactor.py` exposing
   `compact_for_prompt(doc, content)`; register it through shared dispatch.
5. Preserve evidence-bearing fields. In particular, never truncate
   Velociraptor VQL bodies.
6. If changing the `InstructionPair` or prompt record schema, update structured
   Gemini output, serializers, validators, Phase 4 candidate parsing, and the
   data-contract documentation together.

## Required Validation Ladder

```bash
# 1. Entire raw corpus must still parse
python -m scripts.synthesize validate-raw --raw-dir data/raw

# 2. Render without spending API budget
python -m scripts.synthesize render-prompts \
  --mode pilot --limit 20 \
  --output-dir data/synthesized/change_preview \
  --write-prompt-files

# 3. Run a new, one-prompt API smoke directory
python -m scripts.synthesize run \
  --mode pilot --limit 1 \
  --output-dir data/synthesized/change_smoke

# 4. Run and manually review a larger pilot before subset/full generation
python -m scripts.synthesize run \
  --mode pilot \
  --output-dir data/synthesized/change_pilot
```

## Checks And Pitfalls

- `accepted.jsonl` is candidate data, never direct training input.
- Keep canonical `<reasoning>` and `[GENERAL KNOWLEDGE]` provenance behavior;
  GLM-specific conversions belong in Phase 5.
- `grounding=source_only` forbids general-knowledge tags;
  `source_plus_general` requires them when non-source claims are used.
- Taxonomy and provenance fields are normalized from deterministic prompt data
  before pair validation. Do not make model spelling authoritative.
- `--skip-present` is safe only for matching prompt hash and model terminal
  rows. Raw output alone is not terminal.
- An alternate teacher is a separate labeled run, never an automatic fallback.
- Review prompt count and expected spend before subset/full generation. Keep the
  rejection circuit breaker unless a documented experiment requires otherwise.

## UML

<puml src="../diagrams/synthesis-sequence.puml" alt="Phase 3 synthesis sequence" width="1000" />

See [Synthesis](synthesis.md) and [Prompt Guide](prompt-guide.md).

# Shared Validation Boundary

`validation/` contains pure reasoning, grounding, indicator, mapping, and
taxonomy primitives. Phase 3 and Phase 4 intentionally have separate policy
wrappers. When changing a primitive:

1. keep it free of stage-specific IO and status decisions;
2. check both `synthesizers/validators.py` and `quality/validators.py` callers;
3. test known-valid, known-invalid, missing, and malformed values;
4. document whether the failure is Phase 3 reject, Phase 4 reject, or review.

# Phase 4: Quality

## Responsibility

Phase 4 reloads source evidence, applies independent row gates, produces a
transparent heuristic score, detects duplicates and balance problems, and
routes rows to filtered, review, or rejected outputs.

## Files To Update

| Concern | Files |
|---|---|
| Row policy | `quality/validators.py` |
| Score formula/feature extraction | `quality/runner.py`, `configs/quality.yaml`, `configs/task_categories.yaml` |
| ATT&CK/ATLAS/tool references | `quality/references.py`, `configs/quality.yaml` |
| Dedupe/distribution gates | `quality/dataset.py`, `configs/quality.yaml` |
| Candidate/decision schemas | `quality/schemas.py` |
| Stage orchestration/output | `quality/runner.py` |

## Update Procedure

1. Classify every new issue as reject, review, or informational. Hard-invalid
   data should not be rescued by a high heuristic score.
2. Put thresholds, weights, allowlists, penalty terms, and sampling seeds in
   configuration.
3. Keep all scoring no-API unless the project explicitly adopts a Phase 4+
   judge and records its provenance separately.
4. When changing duplicate logic, preserve deterministic retention and audit
   how the retained member is chosen.
5. When changing balance gates, inspect category, difficulty, source, and
   taxonomy distributions together; improving one can distort another.
6. Preserve quality issues and status in downstream metadata.

## Checks And Pitfalls

```bash
python -m scripts.quality_filter \
  --input data/synthesized/<pilot>/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/<new_run>
```

- Use a new output directory. `--append` can duplicate or mix policies and
  should be reserved for deliberate compatible continuation.
- Inspect `quality_manifest.json`, samples from every status, near-duplicate
  decisions, balance issues, and `manual_spot_check_sample.jsonl`.
- Local ATT&CK and ATLAS caches support reproducible ID validation; missing or
  stale caches can change reference behavior.
- Heuristic scores rank quality; they do not prove factual correctness.
- Review rows are not eligible for active packaging until they are adjudicated
  into filtered output.

## UML

<puml src="../diagrams/quality-activity.puml" alt="Phase 4 quality activity" width="950" />

See [Validation And Quality](validation-quality.md) and
[Quality Rubric](quality-rubric.md).

# Phase 5: Packaging

## Responsibility

Phase 5 converts package-eligible quality rows into chat records, applies
model-specific assistant transformations, and creates leakage-safe
train/validation/test splits grouped by `source_doc_id`.

## Files To Update

| Concern | Files |
|---|---|
| Split/system/response policy | `configs/packaging*.yaml` |
| Record/schema/transforms/preflight | `dataset_packaging/runner.py`, `dataset_packaging/schemas.py` |
| CLI arguments | `scripts/package_dataset.py` |
| Training consumer | relevant `configs/finetune*.yaml`, `scripts/finetune.py` |

## Update Procedure

1. Create a new model-specific config rather than changing canonical quality
   rows in place.
2. Define the reasoning/direct fractions for filtered rows; they must sum to
   1.0.
3. Make transforms one-way at export time and retain original provenance in
   metadata.
4. Split groups, not individual rows. Every row derived from one
   `source_doc_id` must remain in one split.
5. Add preflight checks for every model-specific tag/annotation invariant.
6. Point a new training config at the new package and its exact manifest.

```bash
python -m scripts.package_dataset \
  --config configs/<packaging_config>.yaml \
  --quality-dir data/quality/<quality_run> \
  --output-dir data/packaged/<new_package>
```

## Checks And Pitfalls

- Confirm input quality run ID, eligible count, response-style counts, split
  counts, and zero `source_doc_id` overlap in `packaging_manifest.json`.
- Parse every output line and verify roles are system/user/assistant in order.
- Check empty responses, balanced tags, forbidden annotations, and stable IDs.
- The packager reads only `filtered.jsonl`; any embedded status other than
  `filtered` is a validation failure.
- Keep this package named `dataset_packaging/`; renaming it to `packaging/`
  would shadow the common third-party library.

## UML

<puml src="../diagrams/packaging-sequence.puml" alt="Phase 5 packaging sequence" width="950" />

See [Packaging](packaging.md).

# Phase 6A: Training And Export

## Responsibility

Training validates the Phase 5 inputs, renders each conversation exactly once,
appends EOS, rejects overlength rows, performs Unsloth LoRA SFT, and saves both
the LoRA adapter and its configured GGUF quantization. These two artifacts are
mandatory outputs of every successful training run.

Here, “validates” is limited to path existence plus selected packaging-manifest
metadata. The runner does not reconcile JSONL counts or roles with the manifest,
verify split overlap, or consume the test split during SFT. Perform the package
checks from Phase 5 independently before spending GPU time.

## Files To Update

| Concern | Files |
|---|---|
| Dataset/model/LoRA/trainer/export policy | `configs/finetune*.yaml` |
| Input validation/rendering/trainer integration | `scripts/finetune.py` |
| Direct adapter smoke | `scripts/test_lora.py` |
| Dependency/CUDA pins | `pyproject.toml` |

## Update Procedure

1. Copy the last config to a new versioned file and isolate all output paths.
2. Pin the exact package manifest and split files.
3. Change one coherent factor at a time: data view, template/EOS handling,
   LoRA parameters, optimizer schedule, or GGUF quantization.
4. Keep `unsloth` imported before datasets/TRL/Transformers inside the training
   path so its fused-loss patches install first.
5. Preserve one-time chat rendering: after producing the text field, remove
   `messages` so TRL does not silently apply the template again.
6. Write training manifest/configuration before treating artifacts as
   reproducible; add versions, hashes, metrics, and checkpoint selection to the
   handover record.

Always pass `--config`: the CLI default is not an active candidate. Use a fresh
output directory. Checkpoints do not imply resume support, and a failure before
the final manifest write can leave partial outputs without current run metadata.

```bash
python -m scripts.finetune --config configs/<new_finetune_config>.yaml
```

## Mandatory Promotion Checks

1. Review train/evaluation loss and saved checkpoints.
2. Load the **direct adapter**, not only GGUF, and run a bounded `hello` prompt.
3. Preserve `model.generation_config.eos_token_id` and require termination on
   one of those IDs before `max_new_tokens`; reject repeated content or leaked
   thinking/template delimiters. For GLM, `<|user|>` and `<|observation|>` are
   role tokens that are also configured stop conditions.
4. Run several representative DFIR prompts and inspect grounding, termination,
   and formatting.
5. Only then promote or serve the generated GGUF and proceed to evaluation.

The current `scripts/test_lora.py` has a hard-coded v5 adapter path, exercises
only a `hello` prompt, and prints rather than enforces its result. It now passes
the complete model stop list, but its stop-report calculation incorrectly uses
all generated token IDs rather than intersecting them with that list. Correct
and parameterize it for the artifact under review, then run the additional
DFIR/repetition/template-leakage checks above. A zero process exit is not proof
that the smoke gate passed.

## UML

<puml src="../diagrams/phase6-training-sequence.puml" alt="Phase 6 training and promotion sequence" width="1000" />

See [Training And Release](training-and-release.md).

# Phase 6B: Benchmark And Evaluation

## Responsibility

Evaluation loads held-out cases, generates or replays one target prediction,
obtains a structured verdict from a separate local judge, and checkpoints the
completed prefix after every successful case. Each artifact replacement is
atomic, but the set is not transactional. Comparison reports whether compatible
complete baseline/tuned scorecards pass overall and task regression gates; its
process exit status does not enforce that decision.

## Files To Update

| Concern | Files |
|---|---|
| Cases and answer keys | `evaluation/benchmark/*.jsonl` |
| Benchmark schema | `evaluation/schemas.py` |
| Prompt construction/client mode/checkpoints | `evaluation/runner.py`, `evaluation/model_clients.py` |
| Structured-output instructions and judge JSON parsing | `evaluation/structured_output.py` |
| Judge protocol | `evaluation/judge.py`, `evaluation/scoring.py` |
| Compatibility/release gates | `evaluation/comparison.py` |
| Endpoint and decoding policy | `configs/evaluation.yaml` |

## Benchmark Update Procedure

1. Keep every case outside collection/synthesis/training data.
2. Give the case a stable ID, task, prompt/context, answer key, rubric, and any
   complete independently acceptable variants.
3. Manually review it and record reviewer/date before scoring claims.
4. Validate all JSONL and inspect the changed benchmark fingerprint.
5. If cases change, rerun both baseline and tuned models; old and new
   fingerprints cannot be compared.

## Evaluator Update Procedure

1. Keep target and judge as separate clients/endpoints.
2. Preserve sequential generate-then-judge ordering unless capacity and failure
   semantics are deliberately redesigned.
3. Validate bounded judge scores, concise reason, criterion scores, and variant
   indices before checkpointing.
4. Preserve per-file atomic writes and `in_progress`/`complete` distinction.
   The checkpoint files are not one transaction; keep the manifest last and
   reconcile case IDs/counts when recovering an interrupted directory.
5. Update protocol/config fingerprints whenever judge-visible behavior changes.
6. Calibrate against a human-scored stratified set and assign a non-placeholder
   calibration ID before final runs.

```bash
python -m scripts.run_evaluation \
  --config configs/evaluation.yaml \
  --cases evaluation/benchmark \
  --mode openai_compatible \
  --run-id <new_run> \
  --model-label <label>

python -m scripts.compare_evaluations \
  --baseline-dir data/evaluation/<baseline> \
  --tuned-dir data/evaluation/<tuned> \
  --output-dir data/evaluation/comparisons/<name>
```

## Checks And Pitfalls

- `base_url` is the API root ending in `/v1`; the client adds the completion
  route.
- Objective tasks may request structured target JSON, but the judge scores both
  form and content.
- Every inner `acceptable_variants` list is one complete alternative, not a
  menu of fragments.
- A crash leaves useful checkpoints, but the current runner does not resume;
  reusing a run ID can overwrite it from case one.
- Empty target content is currently warned and judged. Inspect finish reasons
  and token use, especially when reasoning consumes the output budget.
- Target response model, finish reason, usage, and reasoning content are logged
  but not saved. A configured/served model mismatch is only a warning.
- `complete` is necessary but not sufficient. Require matching benchmark/case
  IDs, judge protocol/configuration, inference configuration, and a real shared
  calibration ID.
- Comparison does not verify target prompts, generation settings, endpoints,
  overrides, prediction-file identity, or served model. Freeze and compare those
  inputs outside the current scorecard contract.
- Comparison code currently accepts `uncalibrated` when both sides match. Until
  fixed, enforce the non-placeholder gate procedurally.
- Comparison returns exit code 0 even when `passes_regression_gate` is false.
  Automation must inspect `comparison.json` and set its own failing status.
- Judge criterion names and totals are not reconciled with the declared rubric;
  treat them as explanatory metadata and review the scalar verdict.
- Aggregate gain never overrides a severe behavioral or unacceptable task-level
  regression.

## UML

<puml src="../diagrams/phase6-evaluation-sequence.puml" alt="Phase 6 sequential evaluation and checkpointing" width="1000" />

See [Benchmark Design](benchmark-design.md) and
[Architecture](architecture.md#pipeline-boundaries).

# Documentation And UML Maintenance

The diagrams are executable documentation: MarkBind compiles every `.puml`
because `plantumlCheck` is enabled. When changing a phase boundary, component,
contract, or call order:

1. update the closest phase diagram;
2. update `pipeline-component.puml` for ownership/dependency changes;
3. update `end-to-end-sequence.puml` for cross-phase workflow changes;
4. render the [Diagrams](diagrams.md) page and run the full docs build.

```bash
cd docs
npm run build
```

Do not put planned components in current-implementation diagrams. Record future
work in [Suggested Improvements](suggested-improvements.md).
