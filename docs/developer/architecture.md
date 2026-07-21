<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Architecture</h1>

This repository is a Python dataset pipeline. It is not a product frontend, API
server, or model-serving runtime.

# Runtime

| Area | Current Implementation |
|---|---|
| Language | Python 3.11+ |
| Packaging | `pyproject.toml` with setuptools |
| CLI entrypoints | `dfir-collect`, `dfir-synthesize`, `dfir-quality`, `dfir-package`, `dfir-evaluate`, `dfir-compare-evals`, `dfir-train-lora` |
| Core libraries | `pydantic`, `pyyaml`, `jsonlines`, `google-genai`, `requests`, `gitpython`, `rich`, `tqdm`, `mitreattack-python`, `unsloth`, `transformers`, `trl` |

# Component View

<puml src="../diagrams/pipeline-component.puml" alt="Component diagram for the dataset factory" width="1000" />

# End-To-End Sequence

<puml src="../diagrams/end-to-end-sequence.puml" alt="End-to-end sequence diagram" width="1000" />

# Phase 6 Evaluation Sequence

<puml src="../diagrams/phase6-evaluation-sequence.puml" alt="Sequential Phase 6 target generation, judging, and checkpointing" width="1000" />

# Main Packages

| Path | Responsibility |
|---|---|
| `collectors/` | Phase 2 source-specific collection into `RawDocument` JSONL. |
| `scripts/collect_all.py` | CLI orchestrator for configured collectors. |
| `synthesizers/` | Phase 3 planning, prompt rendering, Gemini generation, run state, and generated-output validation. |
| `synthesizers/prompts/` | Base, category, source-type, content-type, and compactor prompt assets. |
| `validation/` | Pure reusable validation primitives shared by Phase 3 and Phase 4. |
| `quality/` | Phase 4 row gates, scoring, references, dataset audits, and output writing. |
| `dataset_packaging/` | Phase 5 local JSONL packaging for Unsloth/GLM SFT. |
| `evaluation/` | Phase 6 local LLM judging, structured-output parsing, sequential target/judge orchestration, scorecard manifests, and comparison gates. |
| `scripts/` | Thin CLI entrypoints that dispatch to package runners. |
| `utils/` | Low-level helpers for IO, text normalization, Markdown frontmatter, and git URLs. |
| `configs/` | Machine-readable policy and pipeline settings. |
| `project_state/` | Live product intent, decisions, TODOs, and presentation rules. |
| `docs/` | Canonical stable guidance and its MarkBind site source. |

# Pipeline Phases

## Phase 2 Collection

`scripts.collect_all` loads `configs/collection.yaml`, maps source keys to
collector classes, and runs selected collectors. Each collector writes one JSONL
file under `data/raw/<source>/` and returns a `CollectionManifest` entry. The
script combines these entries into `data/raw/collection_manifest.json`.

The collection command currently has important non-transactional behavior:

* collectors run sequentially and write directly to their canonical JSONL file;
* Git-backed collectors reuse any non-empty clone directory without fetching or
  verifying a newer upstream revision;
* the ATT&CK download similarly reuses its existing cache file;
* `--source <name>` replaces `collection_manifest.json` with a manifest for only
  that invocation; it does not merge the result with earlier entries;
* collector-reported errors and caught fatal exceptions do not produce a
  non-zero process exit status;
* a fatal exception handled by the CLI produces a reduced manifest row rather
  than a complete `CollectionManifest` record.

For these reasons, downstream work must validate the raw corpus and inspect the
manifest's `errors`, `warnings`, and source coverage. Process exit status alone
is not a collection success gate. An interrupted write may leave a partial
source JSONL because raw output replacement is not atomic.

## Phase 3 Synthesis

`scripts.synthesize` exposes three subcommands:

* `validate-raw`
* `render-prompts`
* `run`

`synthesizers.planner` selects documents and assigns category/difficulty.
`PromptBuilder` renders prompt records from config and templates. Prompt-time
compactors produce shorter source views without mutating raw documents.

`GeminiClient` uses the Google GenAI SDK `models.generate_content` path with
structured JSON response settings. The runner writes prompts, raw outputs,
accepted candidate rows, rejected rows, and a generation manifest.

Phase 3 output is append-oriented rather than one-directory-per-run enforced.
`prompts.jsonl` and the final manifest are replaced on each invocation, while
accepted, rejected, and raw-output streams are appended. `--skip-present` can
continue an unchanged plan, but the directory may then contain several run IDs
and its manifest describes only the latest invocation. Changed prompt hashes do
not remove earlier rows, so prompt or policy changes require a new output
directory.

The manifest is written only after the generation loop. Incremental rows can
survive an interruption without a current manifest, and a partial final JSONL
line is possible. Rejections are terminal for skip-present, including API
errors. A circuit-breaker stop returns exit code 2; ordinary rejected prompts do
not make the command fail.

## Shared Validation

`validation/` holds pure primitives:

* reasoning block parsing and link validation;
* grounding field and `[GENERAL KNOWLEDGE]` tag consistency;
* concrete indicator extraction and invention checks;
* ATT&CK/ATLAS ID regexes;
* taxonomy ref extraction from config.

Phase 3 and Phase 4 call these primitives through separate policy wrappers.

## Phase 4 Quality

`quality.runner` loads configs, raw docs, and references; validates every Phase 3
candidate row; scores candidates; applies dataset gates; writes filtered,
review, rejected, spot-check, and manifest outputs.

Phase 4 is a batch replacement workflow by default, but output preparation is
not transactional. The runner removes the three existing row-output JSONL files
before loading raw documents or opening the candidate input. A missing input or
later preflight failure can therefore leave emptied row outputs beside an older
spot-check sample and manifest. Use a new output directory when input readiness
has not already been verified.

`--append` appends only the three row-output streams. Dataset gates still inspect
the current input batch, while the spot-check sample and manifest are replaced
and describe only that batch. Append mode does not create an aggregate-consistent
quality directory and should not be used for an artifact intended for packaging.

Near-duplicate detection and source-balance movement can change row status.
Category balance, difficulty balance, and taxonomy coverage are reporting audits
only: an out-of-tolerance value does not change rows or fail the command. The
runner also returns success after ordinary row rejection, an empty input, or a
batch in which every row is rejected.

Scoring is a coarse lexical ranking mechanism, not semantic adjudication. It can
leave factual or reasoning dimensions at 5 for review-severity problems and can
reward an ungrounded concrete artifact for specificity. Those scores influence
duplicate retention and source balancing. The duplicate gate also skips
comparison for candidates with fewer than eight distinctive tokens, so exact
short pairs can survive.

Quality configuration is loaded without a typed schema or range checks. The
manifest records current-invocation results but not config fingerprints,
reference-cache identities, or loaded reference counts; those counts exist only
in the run log. Preserve logs and independently version configuration/cache
inputs when reproducible release provenance is required.

Phase 4 deliberately does not call Phase 3's generated-output validators.

## Phase 5 Packaging

`dataset_packaging.runner` reads only Phase 4 `filtered.jsonl`, verifies every
row is marked `quality_status: filtered`, builds chat-style message records,
splits by `source_doc_id`, writes train/validation/test JSONL, and creates a
packaging manifest. The package name is
`dataset_packaging/` to avoid shadowing Python's third-party `packaging` module.
The GLM v3 configuration deterministically assigns a 75% reasoning / 25%
direct-response mix, removes grounding annotations, converts retained canonical
reasoning tags to native thinking tags, and validates the resulting GLM tag
contract without mutating canonical inputs.

## Phase 6 Evaluation And Training

`evaluation.runner` loads held-out benchmark cases and calls either a local
OpenAI-compatible model endpoint or a prediction JSONL file. A separately
configured local judge is mandatory, and the runner writes one scorecard under
`scorecard/`. Cases are processed sequentially: the target response
is generated, that response is judged, and only then does the runner advance to
the next case. After every verdict, predictions, case results, aggregate scores,
and the run manifest are each written through a temporary file and atomically
replaced. The four-file checkpoint is not a transaction: a process failure
between replacements can leave artifacts with different completed-case counts.
Treat the manifest as the last commit marker and reconcile all case IDs before
using a recovered checkpoint. Partial checkpoints are marked
`in_progress`; comparison accepts only `complete` scorecards. Each benchmark
case declares an explicit target-output format. TTP, IOC, and ranking cases
request structured JSON for inspectability, but the judge evaluates both
formatting and content without claiming a mathematical F1 or NDCG calculation.

These checkpoints do not implement resume. A new invocation starts the case
loop from the beginning and does not hydrate prior predictions or scores.

The judge receives the answer key, scoring rubric, and `acceptable_variants`.
Each variant is a complete independently valid alternative. Its structured
verdict includes a bounded score, concise reason, optional criterion scores, and
a range-validated matched-variant index.

Criterion keys and values are not reconciled with the case rubric or scalar
score. Keys may be arbitrary, and each value is checked only against the case's
overall 0-to-maximum range. Treat criteria as judge-supplied explanation, not an
independently calculated rubric breakdown.

`evaluation.comparison` accepts complete scorecards and requires matching
benchmark fingerprint, case IDs, task types, judge protocol/configuration
fingerprint, and calibration ID. Per-task regression gates prevent a headline
improvement from hiding a material task regression in the generated report.
They do not change process exit status. `calibration_id` is
reproducibility metadata, not an implemented calibration procedure. The
comparison currently checks that IDs are present and equal but does not reject
the placeholder value `uncalibrated`; release policy must enforce a real ID
until code does.

Compatibility does not fingerprint the target-side system prompt, context
wrapper, sampling/token settings, structured-output switch, request overrides,
endpoint, prediction file, or effective served model. The target client warns
when the server reports a different model but continues, and saved predictions
omit the response model, finish reason, usage, and reasoning-content metadata.
Freeze and record target settings separately before comparing runs.

The comparison is a reporting gate, not a process-exit gate. It writes
`passes_regression_gate` but returns exit code 0 even when that value is false.
Automation must parse `comparison.json` and fail explicitly.

The evaluator exposes exactly two target-input modes: `openai_compatible` calls
the target server, while `prediction_file` replays saved target answers. There
are no alternate mode aliases or evaluator-selection fields. Existing
uncalibrated runs under the former `scorecards/llm_judge/` layout are historical
diagnostics and are not inputs to the current comparison command.

`scripts.finetune` launches local Unsloth LoRA SFT. It renders conversations
once, appends EOS explicitly, rejects oversized examples, removes `messages`
before TRL can reapply the chat template, and imports Unsloth before TRL so
fused-loss patches are installed. The CLI default still points to the historical
v1 config, so every real run must pass an explicit versioned `--config`.

Training preflight is intentionally shallow in the current implementation. It
checks that train, validation, test, and packaging-manifest paths exist and
copies selected manifest fields into the training manifest. It does not parse or
validate all package rows, reconcile file counts, verify split separation, or
fail when the packaging manifest is malformed. Only train and validation are
loaded by the trainer; test is an existence/provenance input for later
evaluation.

The runner has no resume or output-directory isolation semantics. Checkpoints
may survive a failed run, but `trainer.train()` is not passed a resume checkpoint.
The training manifest is written only after training, adapter save, and GGUF
conversion all finish, so a failure can leave partial artifacts with no current
manifest or beside an older one.

# Current Generated State

The active GLM training package is:

```text
data/packaged/glm47_v3/
```

It contains 4,152 filtered-only records split into 3,322 train, 415 validation,
and 415 test rows. It has 3,114 reasoning and 1,038 direct examples, with no
`source_doc_id` overlap.

The first training run, `train-20260714T025314Z`, completed one epoch and 552
steps but is rejected: direct-adapter and Web UI tests looped, emitted template
tokens, and did not emit EOS. V2 training completed, but its exploratory tuned
evaluation scored 0.6831 versus the base model's 0.7588. V3 completed as
`train-20260717T042223Z`, and the equivalent isolated v4 rerun completed as
`train-20260720T062603Z`; both produced adapters and GGUFs. The repository does
not contain a durable passing smoke-gate record for either. The newer v5 config
changes dropout and target modules, but `data/finetune/glm47_v5/` currently has
no manifest or artifacts.

`scripts/test_lora.py` currently points at the v4 adapter and prints the EOS
result for one `hello` prompt. It does not exit nonzero when EOS is absent and
does not test DFIR prompts, repetition, or template leakage, so it is a manual
diagnostic rather than an enforcing release gate.

The exploratory base evaluation `data/evaluation/glm47-flash-base/` completed
68/68 cases with overall normalized judge score `0.7588`. Its calibration ID is
`uncalibrated`, so the result verifies the runner and provides diagnostic cases
but is not a final baseline. Calibrated base and tuned runs remain outstanding.

It is also historical relative to the current evaluator: its benchmark
fingerprint is `09b197857e44...` and its judge protocol is
`phase6-judge-v2-acceptable-variants`, while the current 68 cases fingerprint to
`b1fc02a447e4...` and current code uses `phase6-judge-v3-target-output`. No
checked-in scorecard is a complete compatible result for the current benchmark
and protocol.

An interrupted uncalibrated v3 tuned evaluation contains 9 of 68 cases. It is
diagnostic crash output, not a completed comparison or promotion decision.

# Important Architectural Decisions

* Raw documents remain complete. Prompt-cost reduction happens only during
  Phase 3 prompt rendering.
* Config files own policy; Python modules own mechanics.
* Canonical responses use `<reasoning>`, not `<think>`.
* Model-specific training views may convert tags and remove provenance markers
  without mutating canonical synthesis/quality records.
* A direct adapter must pass bounded EOS termination tests before GGUF promotion
  or benchmark evaluation.
* Gemini 2.5 Flash is the primary teacher model for canonical generation.
* Alternate teacher models must run as separate labeled jobs.
* Phase 3 `accepted.jsonl` is candidate data, not final training data.
* Phase 5 packages only filtered rows; review and rejected rows are excluded.
* Phase 6 benchmark cases are held out from synthesis/training and must be
  manually reviewed before baseline scoring.
* A complete evaluation checkpoint is not necessarily calibrated evidence;
  comparison claims require the same frozen, non-placeholder calibration ID.
