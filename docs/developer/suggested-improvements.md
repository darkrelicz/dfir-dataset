<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Suggested Improvements

This page intentionally separates future recommendations from current
implementation facts.

## Highest Priority

### Finalize Phase 6 Benchmark

The evaluator and training scaffolding now exist. Finalize and manually review
the held-out benchmark cases before fine-tuning.

Suggested coverage:

* TTP identification;
* IOC extraction;
* triage ranking;
* detection interpretation;
* report quality;
* reasoning quality;
* AI/LLM ATLAS cases.

Run baseline scoring, post-training scoring, and comparison with the Phase 6
commands. Record results in `project_state/TRAINING_RECIPE.md` and update
`project_state/TODO.md`.

### Calibrate And Freeze The Local Judge

Do not treat deterministic temperature as calibration. Build a separate,
stratified calibration set containing good, borderline, unsafe, incomplete,
overconfident, and deliberately verbose answers across every task type. Have at
least two DFIR reviewers score it independently against the same rubrics, then
adjudicate disagreements into reference labels.

Measure judge agreement with human labels using mean absolute error and weighted
Cohen's kappa for ordinal scores, Spearman correlation for ranking, and a
confusion matrix plus critical-error recall for any pass/fail deployment gate.
Also run repeated-judgement and perturbation tests for paraphrase stability,
verbosity bias, answer-order bias, prompt-injection resistance, and sensitivity
to judge quantization.

Tune the rubric wording and judge prompt only on a calibration split. Freeze a
versioned prompt, judge model/quantization, chat template, temperature, and
server settings, assign that release a `calibration_id` in
`configs/evaluation.yaml`, then report metrics on an untouched holdout split. If
enough human labels exist, fit a monotonic ordinal or isotonic score mapping on
the calibration split; never fit that mapping on the benchmark used for the
base-versus-tuned claim. Keep periodic human audits because a calibrated judge
is still a measurement model, not ground truth.

### Expand Tests

Focused judge-response, sequential-runner, and scorecard-comparison tests now
exist. Continue with tests for:

* shared validation primitives;
* `PromptBuilder` taxonomy-ref and pair-cap behavior;
* prompt policy preflight failures;
* Phase 4 row validators;
* packaging split leakage checks.

### Resolve Review Queue

The current package includes review rows by time-boxed decision. Future quality
hardening should adjudicate `review_queue.jsonl`, especially:

* invented indicators;
* mapping inconsistencies;
* unknown tool names;
* overlong reasoning.

## Pipeline Hardening

### Improve Collector Regression Checks

Add smoke fixtures for collectors that parse unstable upstream formats:

* Volatility AST plugin extraction;
* ATLAS v6 parser loading;
* Velociraptor embedded YAML extraction;
* OSSEM event dictionary candidate selection;
* LOLBAS/GTFOBins shape differences.

### Add Manifest Consistency Checks

Add a command that compares:

* raw JSONL counts versus `collection_manifest.json`;
* `prompts.jsonl` count versus `generation_manifest.json`;
* accepted/rejected counts versus quality input;
* package split counts versus `packaging_manifest.json`.

### Add Safer Resume Reporting

`--skip-present` already checks prompt hash and model. A future enhancement
could print a compact resume summary by accepted/rejected/pending prompt counts
before generation starts.

## Dataset Quality

### Add AI-Assisted Judging As Optional Phase 4+

Keep deterministic Phase 4 as the default. Add an optional post-filter judging
stage for fuzzy claims such as weak reasoning, unsupported forensic inference,
and low operational value.

This should write separate outputs so deterministic status remains auditable.

### Improve Source-Balance Controls

Current source balance moves overrepresented filtered rows to review by
low-score order. Future work could make source-balance targets source-aware
instead of using one global maximum share.

### Expand Coverage

Known weak areas:

* cloud compute, network, detections, SaaS;
* file storage and data access;
* Linux memory and containers;
* PCAP/Zeek/web traffic/email;
* mobile;
* OT/ICS;
* virtualization;
* legal/chain-of-custody;
* richer AI/LLM incident sources.

## Training And Release

### Generate A Run-Specific Dataset Card

`project_state/DATASET_CARD.md` is currently a template. Generate or fill a
run-specific card from:

* raw collection manifest;
* generation manifest;
* quality manifest;
* packaging manifest.

### Add Hugging Face Export Only If Hosting Decision Changes

Current hosting is local-only on DGX Sparks storage. Do not add Hugging Face
upload logic unless `project_state/DECISIONS.md` changes.

### Add Model-Specific Export Adapters

The canonical dataset uses `<reasoning>`. If a training target requires a
different tag such as `<think>`, implement that as an export adapter rather than
changing canonical synthesis outputs.
