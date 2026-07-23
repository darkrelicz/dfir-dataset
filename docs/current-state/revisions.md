<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Pipeline Revisions</h1>

> This page tracks synthesis runs, quality-filter snapshots, dataset/package variants, fine-tuning attempts, and evaluation evidence. It does not track documentation or general repository revisions.
>
> For the live project snapshot, head over to [Current Project State](index.md).

---

## Synthesis Revisions

### Gemini Reduced Subset

`data/synthesized/gemini_subset_1/`, run `run-20260701T021807Z`, selected 6,494 source documents using the configured subset stratification. Its completed artifacts contain 6,287 accepted candidate pairs and 206 rejected prompts. This run remains the synthesis input for the recorded quality snapshots.

### Gemini Pilot

`data/synthesized/gemini_pilot_7/`, run `run-20260630T041212Z`, was the representative pilot using `gemini-2.5-flash`. It selected 285 source documents, accepted 477 candidate pairs, and recorded 64 rejected prompts. It was superseded by the reduced subset run and is not an input to the active quality or packaging artifacts.

---

## Quality Revisions

| Run | Recorded outcome |
|---|---|
| `quality-20260708T064057Z` | Current quality input for the filtered-only package |
| `quality-20260707T024506Z` | First recorded quality snapshot; superseded |

Both snapshots reported 4,152 filtered, 1,365 review, and 770 rejected rows from 6,287 candidates.

---

## Dataset And Packaging Revisions

### GLM v3 View

`data/packaged/glm47_v3/` replaced the earlier view with a filtered-only policy. Its package run, `package-20260717T040952Z`, contains 4,152 rows split into 3,322 train, 415 validation, and 415 test records by `source_doc_id`. It derives a deterministic 75% reasoning and 25% direct response mix without mutating the canonical synthesis or quality records. This remains the current usable dataset, so its live status also appears in [Current Project State](index.md).

### GLM v2 View

`data/packaged/glm47_dfir_v2/`, run `package-20260716T053818Z`, applied the GLM format to the same 5,517-row filtered-plus-review selection. Filtered rows mapped `<reasoning>` to `<think>`, review rows kept only the final answer, and literal `[GENERAL KNOWLEDGE]` annotations were removed. It is superseded. The corresponding scalar response-style shape in `configs/packaging.yaml` is incompatible with the current runner unless migrated.

### Filtered-Plus-Review Views

`package-20260708T071253Z` and `package-20260707T075641Z` each contained 5,517 rows: 4,414 train, 552 validation, and 551 test. Under the current time constraint (of about 2 months), 4,152 filtered rows retained canonical reasoning and 1,365 unadjudicated review rows were converted to direct answers. This risk acceptance was superseded by the filtered-only policy.

---

## Training Revisions

No revision below was promoted yet. All training runs had a lower score than the base model.

### v6

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260722T091441Z` | 416 | 0.99951077 | 0.95553052 | 22,090.92 s | No passing promotion record |

Configs used:

| Config | Value |
| --- | --- |
| rank | 32 |
| alpha | 64 |
| dropout | 0 |
| learning rate | 2e-4 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, `out_proj` |

### V5

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260721T072838Z` | 416 | 1.11569183 | 1.04245424 | 21,905.23 s | Corrected termination retest pending |

Configs used:

| Config | Value |
| --- | --- |
| rank | 16 |
| alpha | 32 |
| dropout | 0 |
| learning rate | 2e-5 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |

Initial final-adapter and checkpoint-250 tests reached the 256-token cap and continued after generating `<|user|>`. Those tests passed only scalar `tokenizer.eos_token_id`, overriding the model's configured stop IDs `154820`, `154827`, and `154829`. Because `<|user|>` is ID `154827`, those observations are invalid as evidence of a termination failure.

### V4

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260720T062603Z` | 416 | 1.23110431 | 1.15160668 | 18,002.76 s | No passing promotion record |

Configs used:

| Config | Value |
| --- | --- |
| rank | 16 |
| alpha | 32 |
| dropout | 0.05 |
| learning rate | 2e-5 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj` |

V4 repeated the v3 configuration in isolated output paths. Unsloth's `lora.ParamWrapper` on the recorded stack rejected the nonzero-dropout adapter during loading, preventing a valid direct-adapter promotion record. This was a framework compatibility constraint, not evidence that zero dropout was intrinsically better.

### V3

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260717T042223Z` | 416 | 1.23066088 | 1.15106297 | 17,271.22 s | No passing promotion record |

Configs used:

| Config | Value |
| --- | --- |
| rank | 16 |
| alpha | 32 |
| dropout | 0.05 |
| learning rate | 2e-5 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj` |

V3 was the first run to use the filtered-only package. The same `lora.ParamWrapper` compatibility constraint prevented a valid direct-adapter promotion record.

### V2

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260716T055439Z` | 552 | 0.97943884 | 1.00713074 | 33,241.83 s | Rejected; evaluation regression |

Configs used:

| Config | Value |
| --- | --- |
| rank | 32 |
| alpha | 64 |
| dropout | 0 |
| learning rate | 2e-4 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, `out_proj` |

Its exploratory uncalibrated evaluation scored 0.6831 versus the historical base run's 0.7588. It regressed most on IOC extraction and TTP identification and was rejected as a release candidate.

### V1

| Run | Steps | Training loss | Step-250 eval loss | Runtime | Recorded outcome |
|---|---:|---:|---:|---:|---|
| `train-20260714T025314Z` | 552 | 0.95973044 | 0.99133718 | 38,018.77 s | Rejected; termination and template failures |

Configs used:

| Config | Value |
| --- | --- |
| rank | 32 |
| alpha | 64 |
| dropout | 0 |
| learning rate | 2e-4 |
| max tokens | 4096 |
| target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, `out_proj` |

The exact host and code commit were not recorded. Web UI and direct-adapter greeting tests repeated content, emitted role/template delimiters, and did not emit EOS within 256 new tokens. V1 was rejected and must not be evaluated, promoted, or integrated.

The original training manifest also had reproducibility defects: its `training` mapping was empty because the runner read the wrong configuration key, `loftq_config` was serialized as the string `"None"`, and the configured GGUF directory differed from the actual `_gguf` output directory.

---

## Evaluation Revisions

All results in this section are uncalibrated diagnostics, not release evidence. The judge still has the placeholder calibration ID `uncalibrated`.

### Current-Protocol Runs

These runs share benchmark fingerprint `b1fc02a447e4ab9c2262224f9eff233898f7dda3763b8cfeb62c1dd79216877b`, judge protocol `phase6-judge-v3-target-output`, and judge configuration fingerprint `44674da755ab3ad538e3c62e5feb2a20d11d98377d6e4696c330fedcc877cd3c`.

| Run | Target | Completed | Score | Status |
|---|---|---:|---:|---|
| `glm47-flash-base_2` | `unsloth/GLM-4.7-Flash` | 68 / 68 | 0.7309 | `complete` |
| `glm47-flash-finetuned_v6_1` | v6 GGUF | 68 / 68 | 0.6978 | `complete` |
| `glm47-flash-finetuned_v5_2` | v5 GGUF | 68 / 68 | 0.7346 | `complete` |

The compatible base rerun completed on all 68 cases. V5 scored 0.0037 above the base rerun, while v6 scored 0.0331 below it. These differences remain uncalibrated diagnostics and are not release evidence.

### Historical Tuned Runs

`data/evaluation/glm47-flash-finetuned_v3/` started on 2026-07-20 and stopped after 9 of 68 cases. It is marked `in_progress`, preserved as partial output, and is not comparable evidence.

`data/evaluation/glm47-flash-finetuned_v2_1/` started on 2026-07-17 and completed 68 of 68 cases with an overall score of 0.6831. The broad diagnostic regression was sufficient to reject v2, but it is not calibrated comparison evidence.

These runs use benchmark fingerprint `09b197857e44...` or another historical subset fingerprint and judge protocol `phase6-judge-v2-acceptable-variants`.

### Historical Base Run

The `glm47-flash-base` run started on 2026-07-15 and completed all 68 cases using a local `gemma-4-31B-it-Q4_K_M.gguf` judge:

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

The scorecard records judge protocol `phase6-judge-v2-acceptable-variants`, configuration fingerprint `52b3f0be829335ea19c43d8558f01c335c2a077ba8591a3b4db7d3a1238fa4d0`, and calibration ID `uncalibrated`. It is not directly comparable with the current-protocol runs.

The 0.0279 difference between this run's 0.7588 score and the second base evaluation's 0.7309 score was likely influenced by the target-generation sampling settings. The first run used `temperature: 1.0` and `top_p: 0.95`, allowing stochastic nucleus sampling, whereas the second used `temperature: 0.0` and `top_p: 1.0` for effectively deterministic generation. The change can produce different answers from the same underlying model. However, the benchmark fingerprint, judge protocol, token limit, and recorded served-model identifier also changed, so the score difference cannot be attributed to `temperature` and `top_p` alone.

---

## Maintenance Rule

When a synthesis run, quality snapshot, package variant, fine-tuning attempt, or evaluation result is superseded, preserve its useful context here and remove obsolete narrative from the live and developer guides. Keep exact run facts in generated manifests, keep durable decision rationale in `project_state/DECISIONS.md`, and do not use this page to select an active configuration.
