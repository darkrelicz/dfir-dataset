<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Current Project State</h1>

This is the live handover snapshot for the repository as inspected on
2026-07-23. It records what exists, what is usable, and what must happen next.
Superseded snapshots and run histories are preserved in
[Revisions](revisions.md). Generated manifests remain authoritative for the
exact facts of an individual run.

# Project At A Glance

| Item | Current State |
|---|---|
| Purpose | Re-runnable factory for grounded DFIR instruction data for Shepherd |
| Runtime | Python 3.11+; setuptools project |
| Dataset scope | Core + Tier 1 + Tier 2; 16 collectors |
| Teacher model | `gemini-2.5-flash` through the direct Gemini API |
| Training target | `unsloth/GLM-4.7-Flash`, 4-bit base, LoRA SFT |
| Hosting | Local DGX storage; Hugging Face publishing deferred |
| Current usable dataset | `data/packaged/glm47_v3/` |
| Current usable model | None promoted; candidate selection and an enforcing promotion gate are pending |
| Current evaluation evidence | None suitable for release; complete compatible calibrated base and tuned results are pending |
| Release status | Blocked on an enforcing direct-adapter smoke gate and calibrated comparison |

The repository is a data pipeline, not a web API, model server, or Shepherd
application. The site under `docs/` is the maintainer documentation for that
pipeline.

# Phase Status

| Phase | Status | Canonical Input | Current Artifact |
|---|---|---|---|
| 1. Taxonomy and task design | Complete for current scope | Project plan and DFIR requirements | `docs/reference/taxonomy.md`, `configs/task_categories.yaml`, `configs/quality.yaml` |
| 2. Collection | Complete for 16 sources | `configs/collection.yaml` and public sources | `data/raw/collection_manifest.json` |
| 3. Synthesis | Complete for reduced subset | Phase 2 raw JSONL | `data/synthesized/gemini_subset_1/` |
| 4. Quality | Complete for reduced subset | Phase 3 `accepted.jsonl` | `data/quality/gemini_subset_1/` |
| 5. Packaging | Filtered-only GLM v3 view complete | Phase 4 `filtered.jsonl` | `data/packaged/glm47_v3/` |
| 6. Training | No promoted model; v5 or staged v6 candidate decision pending | Phase 5 GLM package | `configs/finetune_glm47flash_v5.yaml`, `configs/finetune_glm47flash_v6.yaml` |
| 6. Evaluation | No compatible calibrated release result | 68 held-out cases | `configs/evaluation.yaml`, `evaluation/benchmark/` |

# Implemented Pipeline

Run each command as a Python module from the repository root:

| Operation | Python Module Command |
|---|---|
| Collect | `python -m scripts.collect_all` |
| Synthesize | `python -m scripts.synthesize` |
| Quality filter | `python -m scripts.quality_filter` |
| Package | `python -m scripts.package_dataset` |
| Train | `python -m scripts.finetune` |
| Evaluate | `python -m scripts.run_evaluation` |
| Compare | `python -m scripts.compare_evaluations` |

The end-to-end operational commands are in the
[User Guide](../user/command-overview.md). Code-change instructions are in
the [Phase Maintenance Guide](../developer/phase-maintenance.md).

# Phase 1: Taxonomy And Task Design

The human-readable taxonomy has 57 artifact categories across Windows, Linux,
network, SIEM, cloud, file/storage, AI/LLM, mobile, anti-forensics, threat
intelligence, IoT/OT, virtualization, supply chain, and compliance domains.
Machine validation and coverage live in `configs/quality.yaml`.

Generation currently targets five model behaviors:

1. artifact analysis;
2. TTP identification;
3. triage and threat hunting;
4. detection engineering;
5. incident report generation.

Mobile, OT, deep file forensics, attribution, legal/compliance, and several
cloud categories remain intentionally weak or deferred. The taxonomy is broader
than the current source coverage so it can serve as an expansion roadmap.

# Phase 2: Raw Corpus

The current raw corpus contains 20,347 documents across 16 collectors.

| Tier | Source | Documents |
|---|---|---:|
| Core | `mitre_attack` | 697 |
| Core | `sigma_rules` | 3,111 |
| Core | `atomic_red_team` | 1,811 |
| Core | `cisa_advisories` | 3,849 |
| Core | `volatility3_docs` | 194 |
| Core | `mitre_atlas` | 262 |
| Core | `cisa_kev` | 270 |
| Tier 1 | `kape_files` | 811 |
| Tier 1 | `hayabusa_rules` | 4,839 |
| Tier 1 | `lolbas_gtfobins` | 720 |
| Tier 1 | `forensic_artifacts` | 731 |
| Tier 2 | `velociraptor_artifacts` | 437 |
| Tier 2 | `hijacklibs` | 590 |
| Tier 2 | `loldrivers` | 656 |
| Tier 2 | `ossem_data_dicts` | 699 |
| Tier 2 | `cybersec_skills` | 670 |

Git-backed sources use shallow working copies under `data/raw/.repos/`.
Downloaded reference material uses `data/raw/.cache/`. Collectors emit the
shared `RawDocument` contract and preserve complete source content; prompt cost
reduction does not happen in collection.

# Phase 3: Synthesis Snapshot

The current synthesis run is `run-20260701T021807Z`.

| Field | Value |
|---|---:|
| Mode | `subset` |
| Model | `gemini-2.5-flash` |
| Prompt records | 6,494 |
| Accepted candidate pairs | 6,287 |
| Rejected prompt rows | 206 |
| Raw output rows | 7,779 |

Artifacts are `prompts.jsonl`, `raw_outputs.jsonl`, `accepted.jsonl`,
`rejected.jsonl`, and `generation_manifest.json` under
`data/synthesized/gemini_subset_1/`. `accepted.jsonl` contains candidates, not
training-ready data.

Generation is sequential and supports `--skip-present`. A prompt is skipped
only when a terminal accepted/rejected row matches both prompt hash and model.
The runner has API retry/backoff, one configured validation regeneration, and a
20% rejection-rate circuit breaker after 20 attempts in subset/full mode.

Source-specific prompt compactors are implemented for `cisa_advisories`,
`cisa_kev`, `mitre_attack`, `cybersec_skills`, `velociraptor_artifacts`,
`loldrivers`, and `hijacklibs`. Velociraptor VQL bodies are preserved. Full
corpus synthesis and alternate-teacher comparisons are deferred.

# Phase 4: Quality Snapshot

The current quality run is `quality-20260708T064057Z`.

| Status | Pairs |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total checked | 6,287 |

Phase 4 is deterministic and heuristic; it makes no model API calls. It checks
schema/provenance, taxonomy, ATT&CK/ATLAS identifiers, reasoning links,
grounding tags, concrete indicators, tools, source specificity, operational
value, duplicates, balance, and distribution. Outputs include the three status
files, a 100-row deterministic spot-check sample, and `quality_manifest.json`.

Only filtered rows are package-eligible in the active v3 policy. Review rows
remain available for adjudication but are excluded from training, as are all
rejected rows.

# Phase 5: Packaging Snapshot

The active training view is `package-20260717T040952Z`.

| Split | Records |
|---|---:|
| Train | 3,322 |
| Validation | 415 |
| Test | 415 |
| Total | 4,152 |

There is no `source_doc_id` overlap among splits. The response mix is:

| Style | Count | Fraction |
|---|---:|---:|
| GLM reasoning | 3,114 | 0.7500 |
| Direct answer | 1,038 | 0.2500 |

Canonical synthesis and quality records remain unchanged. Only the GLM export
view removes literal `[GENERAL KNOWLEDGE]` annotations, maps `<reasoning>` to
`<think>` for the seeded reasoning subset, and strips reasoning from the seeded
direct subset. Review rows are never loaded. Validation
found zero retained annotations/canonical tags, unbalanced `<think>` blocks,
empty responses, or cross-split source-document overlap.

# Phase 6: Training Snapshot

No model is promoted. V5 and staged v6 are the candidates under consideration;
their preceding configurations and run outcomes are in
[Training Revisions](revisions.md#training-revisions).

The immediate blocker is the direct-adapter promotion gate.
`scripts/test_lora.py` currently points at v5 and preserves
`model.generation_config.eos_token_id`, but it remains advisory: it runs only
`hello`, does not enforce failure, and its stop-token report mistakenly treats
every generated token as a stop token. It must be parameterized and made to
enforce bounded termination, repetition, and template-leakage checks across
greeting and DFIR prompts before any candidate is promoted or evaluated.

# Phase 6: Evaluation Snapshot

The held-out benchmark has 68 cases across eight tasks. There is no complete
compatible calibrated base-versus-tuned result suitable for a release claim.
Earlier scores and partial runs are preserved under
[Evaluation Revisions](revisions.md#evaluation-revisions).

The evaluator runs target generation and judging sequentially and individually
atomically replaces predictions, case results, aggregate scores, and the manifest
after each verdict. The four-file update is not transactional; reconcile files
against the last-written manifest after interruption. It preserves crash output
but does not resume it: a new invocation starts again at case one. Empty target
`content` is warned about and judged
rather than retried. Comparison checks compatible complete scorecards and equal
calibration metadata, but does not yet reject the literal placeholder
`uncalibrated`.

The current benchmark fingerprint is `b1fc02a447e4...` and current judge
protocol is `phase6-judge-v3-target-output`. Existing scorecards do not provide
a complete compatible result under those inputs.

Comparison compatibility covers benchmark and judge identity but not target
prompt/generation settings, endpoint, prediction-file identity, or actual served
model. A failed regression gate is reported in JSON but the command still exits
0, so release automation must enforce the field itself.

# Active Configuration

| Concern | Current File |
|---|---|
| Sources and paths | `configs/collection.yaml` |
| Source profiles and generation caps | `configs/source_profiles.yaml` |
| Teacher model and retry policy | `configs/synthesis.yaml` |
| Task mix and quality signals | `configs/task_categories.yaml` |
| Taxonomy, scoring, dedupe, balance | `configs/quality.yaml` |
| Active GLM packaging transform | `configs/packaging_glm47_v3.yaml` |
| Candidate LoRA configuration | `configs/finetune_glm47flash_v5.yaml` |
| Staged LoRA experiment | `configs/finetune_glm47flash_v6.yaml` |
| Benchmark, target, and judge | `configs/evaluation.yaml` |

`GEMINI_API_KEY` is the only project API secret and is required only for Phase
3 generation. It belongs in `.env` or the process environment, never in Git.
Phase 6 target and judge endpoints are local OpenAI-compatible servers.

# Immediate Work And Release Gates

In order:

1. Fix the v5 smoke script's stop-ID reporting and turn it into a parameterized,
   enforcing gate covering bounded greeting and DFIR prompts, termination,
   repetition, and template leakage. Preserve the model's complete stop list.
2. Rerun that gate against the v5 final adapter and checkpoint 250 and record the
   result before promotion or evaluation.
3. Decide whether v5 or the staged aggressive v6 experiment is the next
   candidate; always pass its versioned config explicitly because the CLI
   default is not an active configuration.
4. Record candidate paths, versions, hashes, validation metrics, and selected
   checkpoint.
5. Finish manual review of all 68 benchmark cases and record owner/date.
6. Build and adjudicate a stratified human-scored judge calibration set; assign
   a real calibration ID and freeze the judge configuration.
7. Run complete calibrated base and tuned evaluations with the same
   benchmark and judge.
8. Compare them and review task-level and severe DFIR regressions before any
   Shepherd integration.

Code hardening still due: reject placeholder calibration IDs in comparison,
fingerprint target-generation inputs, return nonzero for a failed regression
gate, make checkpoint-set consistency recoverable, add fingerprint-safe
evaluation resume, and add configurable retry/failure for empty target responses.

# Deferred Work

Full-corpus synthesis, alternate-teacher comparison, full review-queue
adjudication, manual spot-check completion, broader test coverage, Tier 3 and
unstructured sources, CRAFT/RAFT, and Hugging Face publishing are deferred.
Shepherd integration remains blocked until a candidate's termination and calibrated
evaluation gates both pass.

# Sources Of Truth

Use the following precedence when facts disagree:

1. generated run manifests for run-specific counts, paths, IDs, and status;
2. `project_state/PROJECT_BRIEF.md`, `TODO.md`, and `DECISIONS.md` for live
   direction, risks, and next work;
3. this page for the consolidated handover snapshot;
4. stable developer and user pages for operating and maintenance procedures;
5. [Revisions](revisions.md) for superseded snapshots and run history.

Update this page whenever a phase status, active artifact, accepted risk,
blocker, or immediate next action changes.
