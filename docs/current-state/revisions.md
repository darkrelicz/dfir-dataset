<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Revisions</h1>

This page preserves superseded project snapshots, dataset/package variants,
training attempts, and evaluation evidence. It is historical context, not an
active configuration selector or release record. For the live snapshot, use
[Current Project State](index.md). Generated manifests remain authoritative for
the exact facts of an individual run.

# State Snapshot Revisions

The source revisions below are every checked-in revision of the Current Project
State page through its separation from this history page. Several revisions
changed structure or links without changing project status; those are retained
so the sequence is complete.

| Source revision | Snapshot date | Revision recorded at the time |
|---|---|---|
| `e8fcc9c` | 2026-07-07 | The first Current State page recorded collection, reduced synthesis, time-boxed quality, and local packaging as complete. Phase 6 was not implemented in the repository. |
| `d5d9571` | 2026-07-14 | The evaluator and initial fine-tuning configuration existed; baseline review, real training, tuned scoring, and integration remained next actions. |
| `5fa4bde` | 2026-07-16 | The first LoRA run and exploratory 68-case base evaluation were recorded. Manifest reproducibility defects and judge calibration blocked release use. |
| `4beb421` | 2026-07-16 | The first run was marked rejected, the GLM v2 view became current, and v2 retraining was prepared. |
| `8a287f2` | 2026-07-16 | Stable reference material moved from `project_state/` into the documentation site; project status was materially unchanged. |
| `5002d11` | 2026-07-16 | The handover snapshot expanded to include the implemented pipeline, active configuration, release gates, deferred work, and sources of truth. Project status was materially unchanged. |
| `03eb2e2` | 2026-07-17 | Packaging moved to filtered-only `data/packaged/glm47_v3/`. The v2 tuned evaluation showed a regression, and the v3 training configuration was pending a runner fix. |
| `15ed5c1` | 2026-07-21 | V3 and v4 training/export had completed without a durable passing promotion record. V5 was staged, and the v3 tuned evaluation had stopped after 9 of 68 cases. |
| `6debe4c` | 2026-07-22 | V5 training/export completed and v6 became the newest staged experiment. Initial v5 termination observations were later found invalid because the model stop list had been replaced with one scalar EOS ID. |
| `72fe975` | 2026-07-22 | User-guide links and operating guidance were revised; the Current State facts were materially unchanged. |
| `fe2f653` | 2026-07-23 | The developer guide was consolidated around canonical phase-maintenance and training/release procedures. The active release blocker remained an enforcing adapter gate followed by calibrated comparison. |

# Quality Revisions

`quality-20260707T024506Z` was the first recorded quality snapshot. It was
superseded by `quality-20260708T064057Z`; both snapshots reported 4,152
filtered, 1,365 review, and 770 rejected rows from 6,287 candidates. The later
run remains the input associated with the active filtered-only package.

# Dataset And Packaging Revisions

## Filtered-Plus-Review Views

`package-20260707T075641Z` and `package-20260708T071253Z` each contained 5,517
rows: 4,414 train, 552 validation, and 551 test. Under the time-boxed policy,
4,152 filtered rows retained canonical reasoning and 1,365 unadjudicated review
rows were converted to direct answers. This risk acceptance was superseded by
the filtered-only policy.

## GLM v2 View

`data/packaged/glm47_dfir_v2/`, run `package-20260716T053818Z`, applied the GLM
format to the same 5,517-row filtered-plus-review selection. Filtered rows
mapped `<reasoning>` to `<think>`, review rows kept only the final answer, and
literal `[GENERAL KNOWLEDGE]` annotations were removed. It is superseded. The
corresponding scalar response-style shape in `configs/packaging.yaml` is
incompatible with the current runner unless migrated.

## GLM v3 View

`data/packaged/glm47_v3/` replaced the earlier view with a filtered-only policy.
Its package run, `package-20260717T040952Z`, contains 4,152 rows split into
3,322 train, 415 validation, and 415 test records by `source_doc_id`. It derives
a deterministic 75% reasoning and 25% direct response mix without mutating the
canonical synthesis or quality records. This remains the current usable
dataset, so its live status also appears in [Current Project State](index.md).

# Training Revisions

No revision below was promoted. A completed training loop or export was never,
by itself, release evidence.

## V1

The preserved run is `train-20260714T025314Z`.

| Field | Value |
|---|---|
| Base model | `unsloth/GLM-4.7-Flash` |
| Method | Unsloth LoRA SFT; 4-bit-loaded base |
| Dataset | `package-20260708T071253Z` (`4,414` train / `552` validation / `551` test) |
| Epochs / steps | 1 / 552 |
| Final training loss | 0.95973044 |
| Runtime | 38,018.77 seconds |
| Adapter | `data/finetune/glm47_flash_subset1/lora_adapter` |
| GGUF | `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf` |

The exact host and code commit were not recorded. Web UI and direct-adapter
greeting tests repeated content, emitted role/template delimiters, and did not
emit EOS within 256 new tokens. V1 was rejected and must not be evaluated,
promoted, or integrated.

The original training manifest also had reproducibility defects: its
`training` mapping was empty because the runner read the wrong configuration
key, `loftq_config` was serialized as the string `"None"`, and the configured
GGUF directory differed from the actual `_gguf` output directory.

## V2

V2 completed, but its exploratory uncalibrated evaluation scored 0.6831 versus
the base model's 0.7588. It regressed most on IOC extraction and TTP
identification and was rejected as a release candidate.

## V3 And V4

V3 used the filtered-only package with rank 16 / alpha 32 attention-only LoRA,
dropout 0.05, learning rate `2e-5`, and a 4,096-token maximum. V4 repeated the
configuration in isolated output paths. Unsloth's `lora.ParamWrapper` on the
recorded stack rejected nonzero-dropout adapters during loading, preventing a
valid direct-adapter promotion record. This was a framework compatibility
constraint, not evidence that zero dropout was intrinsically better.

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260717T042223Z` (v3) | 416 | 1.23066088 | 1.15106297 | 17,271.22 s | No passing promotion record |
| `train-20260720T062603Z` (v4) | 416 | 1.23110431 | 1.15160668 | 18,002.76 s | No passing promotion record |

## V5

V5 retained the v3 package, rank, alpha, and learning rate, changed LoRA
dropout to zero, and added `gate_proj`, `up_proj`, and `down_proj` targets.

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260721T072838Z` | 416 | 1.11569183 | 1.04245424 | 21,905.23 s | Corrected termination retest pending |

Initial final-adapter and checkpoint-250 tests reached the 256-token cap and
continued after generating `<|user|>`. Those tests passed only scalar
`tokenizer.eos_token_id`, overriding the model's configured stop IDs `154820`,
`154827`, and `154829`. Because `<|user|>` is ID `154827`, those observations
are invalid as evidence of a termination failure.

## V6

V6 is a staged, unrun experiment. It raises rank/alpha to 32/64, maximum
sequence length to 8,192, and learning rate to `2e-4`, and adds `out_proj` to
the targets. It has no training manifest.

# Evaluation Revisions

All results in this section are historical diagnostics. They are uncalibrated
and do not match the current benchmark fingerprint and judge protocol.

## Exploratory Base Run

The `glm47-flash-base` run completed all 68 cases using a local
`gemma-4-31B-it-Q4_K_M.gguf` judge.

| Task | Cases | Exploratory mean |
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

The scorecard used `judge_calibration_id: uncalibrated`. It recorded judge
protocol `phase6-judge-v2-acceptable-variants` and configuration fingerprint
`52b3f0be829335ea19c43d8558f01c335c2a077ba8591a3b4db7d3a1238fa4d0`.

## Exploratory Tuned Runs

`data/evaluation/glm47-flash-finetuned_v2_1/` completed 68 of 68 cases with the
same uncalibrated judge and scored 0.6831 overall. The broad diagnostic
regression was sufficient to reject v2, but it is not calibrated comparison
evidence.

`data/evaluation/glm47-flash-finetuned_v3/` stopped after 9 of 68 cases and is
marked `in_progress`. It is preserved partial output and is not comparable
evidence.

The checked-in historical scorecards use benchmark fingerprint
`09b197857e44...` or another historical subset fingerprint and judge protocol
`phase6-judge-v2-acceptable-variants`. The later benchmark fingerprint is
`b1fc02a447e4...`, with judge protocol `phase6-judge-v3-target-output`. No
historical scorecard is a complete compatible result under that protocol.

# Maintenance Rule

When a live artifact, candidate, result, or state snapshot is superseded, move
its useful context here and remove the obsolete narrative from the live and
developer guides. Keep exact run facts in generated manifests, keep durable
decision rationale in `project_state/DECISIONS.md`, and do not use this page to
select a configuration.
