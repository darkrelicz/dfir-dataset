<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Current Project State</h1>

This is the complete handover snapshot for the repository as inspected on
2026-07-16. It records what exists, what is usable, what was rejected, and what
must happen next. Generated manifests remain authoritative for the exact facts
of an individual run.

# Project At A Glance

| Item | Current State |
|---|---|
| Purpose | Re-runnable factory for grounded DFIR instruction data for Shepherd |
| Runtime | Python 3.11+; setuptools project |
| Dataset scope | Core + Tier 1 + Tier 2; 16 collectors |
| Teacher model | `gemini-2.5-flash` through the direct Gemini API |
| Training target | `unsloth/GLM-4.7-Flash`, 4-bit base, LoRA SFT |
| Hosting | Local DGX storage; Hugging Face publishing deferred |
| Current usable dataset | `data/packaged/glm47_dfir_v2/` |
| Current usable model | None; v1 is rejected and v2 is not trained |
| Current evaluation evidence | Exploratory only; the judge is uncalibrated |
| Release status | Blocked on v2 EOS smoke test and calibrated comparison |

The repository is a data pipeline, not a web API, model server, or Shepherd
application. The site under `docs/` is the maintainer documentation for that
pipeline.

# Phase Status

| Phase | Status | Canonical Input | Current Artifact |
|---|---|---|---|
| 1. Taxonomy and task design | Complete for current scope | Project plan and DFIR requirements | `docs/reference/taxonomy.md`, `configs/task_categories.yaml`, `configs/quality.yaml` |
| 2. Collection | Complete for 16 sources | `configs/collection.yaml` and public sources | `data/raw/collection_manifest.json` |
| 3. Synthesis | Complete for reduced subset | Phase 2 raw JSONL | `data/synthesized/gemini_subset_1/` |
| 4. Quality | Complete by time-boxed acceptance | Phase 3 `accepted.jsonl` | `data/quality/gemini_subset_1/` |
| 5. Packaging | GLM v2 view complete | Phase 4 filtered + review rows | `data/packaged/glm47_dfir_v2/` |
| 6. Training | V1 rejected; v2 prepared | Phase 5 GLM package | `configs/finetune_glm47flash_v2.yaml` |
| 6. Evaluation | Exploratory base run complete | 68 held-out cases | `data/evaluation/glm47-flash-base/` |

# Implemented Pipeline

The installed console scripts and their equivalent modules are:

| Operation | Console Script | Python Module |
|---|---|---|
| Collect | `dfir-collect` | `python -m scripts.collect_all` |
| Synthesize | `dfir-synthesize` | `python -m scripts.synthesize` |
| Quality filter | `dfir-quality` | `python -m scripts.quality_filter` |
| Package | `dfir-package` | `python -m scripts.package_dataset` |
| Train | `dfir-train-lora` | `python -m scripts.finetune` |
| Evaluate | `dfir-evaluate` | `python -m scripts.run_evaluation` |
| Compare | `dfir-compare-evals` | `python -m scripts.compare_evaluations` |

The end-to-end operational commands are in the
[User Guide](../user/running-the-pipeline.md). Code-change instructions are in
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

For the shortened deadline, filtered and review rows are package-eligible.
Review rows have **not** been fully adjudicated. Including them is an explicit
risk acceptance; all rejected rows remain ineligible.

# Phase 5: Packaging Snapshot

The active training view is `package-20260716T053818Z`.

| Split | Records |
|---|---:|
| Train | 4,414 |
| Validation | 552 |
| Test | 551 |
| Total | 5,517 |

There is no `source_doc_id` overlap among splits. The response mix is:

| Style | Count | Fraction |
|---|---:|---:|
| Canonical reasoning | 4,152 | 0.7526 |
| Direct answer | 1,365 | 0.2474 |

Canonical synthesis and quality records remain unchanged. Only the GLM export
view removes literal `[GENERAL KNOWLEDGE]` annotations, maps `<reasoning>` to
`<think>` for filtered rows, and removes reasoning from review rows. Preflight
found zero retained annotations/canonical tags, unbalanced `<think>` blocks,
empty responses, or cross-split source-document overlap.

# Phase 6: Training Snapshot

The preserved v1 run is `train-20260714T025314Z`.

| Field | Value |
|---|---|
| Base model | `unsloth/GLM-4.7-Flash` |
| Method | Unsloth LoRA SFT; 4-bit-loaded base |
| Train records | 4,414 |
| Epochs / steps | 1 / 552 |
| Final training loss | 0.95973044 |
| Runtime | 38,018.77 seconds |
| Adapter | `data/finetune/glm47_flash_subset1/lora_adapter` |
| GGUF | `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf` |

This model is rejected. Web UI and direct-adapter greeting tests repeated
content, emitted role/template delimiters, and did not emit EOS within 256 new
tokens. It must not be evaluated, promoted, or integrated.

V2 keeps the same LoRA/trainer hyperparameters but uses the cleaned GLM package,
single chat-template rendering, explicit EOS, a 4,096-token length preflight,
correct manifest serialization, and isolated output paths. Its active config is
`configs/finetune_glm47flash_v2.yaml`; training has not completed.

# Phase 6: Evaluation Snapshot

The held-out benchmark has 68 cases across eight tasks. The exploratory
`glm47-flash-base` run completed all cases with a local
`gemma-4-31B-it-Q4_K_M.gguf` judge.

| Task | Cases | Exploratory Mean |
|---|---:|---:|
| AI/LLM ATLAS incident | 8 | 0.6125 |
| Detection interpretation | 10 | 0.9600 |
| Forensic artifact analysis | 8 | 0.8750 |
| Incident report generation | 6 | 1.0000 |
| IOC extraction | 10 | 0.7000 |
| Reasoning, uncertainty, and grounding | 8 | 0.6250 |
| Triage prioritization | 8 | 0.8750 |
| TTP identification | 10 | 0.5100 |
| **Overall** | **68** | **0.7588** |

This is diagnostic evidence only. The scorecard uses
`judge_calibration_id: uncalibrated`, and all cases remain flagged for manual
review. `complete` means every case was checkpointed; it does not mean the judge
is calibrated or the model is releasable.

The evaluator runs target generation and judging sequentially and atomically
rewrites predictions, case results, aggregate scores, and the manifest after
each verdict. It preserves crash output but does not resume it: a new invocation
starts again at case one. Empty target `content` is warned about and judged
rather than retried. Comparison checks compatible complete scorecards and equal
calibration metadata, but does not yet reject the literal placeholder
`uncalibrated`.

# Active Configuration

| Concern | Current File |
|---|---|
| Sources and paths | `configs/collection.yaml` |
| Source profiles and generation caps | `configs/source_profiles.yaml` |
| Teacher model and retry policy | `configs/synthesis.yaml` |
| Task mix and quality signals | `configs/task_categories.yaml` |
| Taxonomy, scoring, dedupe, balance | `configs/quality.yaml` |
| Active GLM packaging transform | `configs/packaging_glm47_v2.yaml` |
| Active v2 LoRA run | `configs/finetune_glm47flash_v2.yaml` |
| Benchmark, target, and judge | `configs/evaluation.yaml` |

`GEMINI_API_KEY` is the only project API secret and is required only for Phase
3 generation. It belongs in `.env` or the process environment, never in Git.
Phase 6 target and judge endpoints are local OpenAI-compatible servers.

# Immediate Work And Release Gates

In order:

1. Finish manual review of all 68 benchmark cases and record owner/date.
2. Build and adjudicate a stratified human-scored judge calibration set; assign
   a real calibration ID and freeze the judge configuration.
3. Complete v2 training with `configs/finetune_glm47flash_v2.yaml`.
4. Run a bounded direct-adapter greeting smoke test. Require
   `EOS generated: True` before GGUF promotion or evaluation.
5. Record v2 paths, versions, hashes, validation metrics, and selected
   checkpoint.
6. Run complete calibrated base and v2 tuned evaluations with the same
   benchmark and judge.
7. Compare them and review task-level and severe DFIR regressions before any
   Shepherd integration.

Code hardening still due: reject placeholder calibration IDs in comparison,
add fingerprint-safe evaluation resume, and add configurable retry/failure for
empty target responses.

# Deferred Work

Full-corpus synthesis, alternate-teacher comparison, full review-queue
adjudication, manual spot-check completion, broader test coverage, Tier 3 and
unstructured sources, CRAFT/RAFT, and Hugging Face publishing are deferred.
Shepherd integration remains blocked until the v2 termination and calibrated
evaluation gates both pass.

# Sources Of Truth

Use the following precedence when facts disagree:

1. generated run manifests for run-specific counts, paths, IDs, and status;
2. `project_state/PROJECT_BRIEF.md`, `TODO.md`, and `DECISIONS.md` for live
   direction, risks, and next work;
3. this page for the consolidated handover snapshot;
4. stable developer and user pages for operating and maintenance procedures.

Update this page whenever a phase status, active artifact, accepted risk,
blocker, or immediate next action changes.
