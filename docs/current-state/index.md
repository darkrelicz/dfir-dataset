<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Current Project State</h1>

This is the live handover snapshot for the repository as inspected on 2026-07-23. It records what exists, what is usable, and what must happen next.

Superseded snapshots and run histories are preserved in [Revisions](revisions.md).

<box type="warning" seamless header="">
Update this page whenever a phase status, active artifact, accepted risk, blocker, or immediate next action changes.
</box>

---

## Project At A Glance

| Item | Current State |
|---|---|
| Purpose | Re-runnable data pipeline for grounded DFIR training data |
| Scope | Public-sourced DFIR dataset generation from collection through local model training and evaluation |
| Runtime | Python 3.11+; setuptools project |
| Dataset scope | Core + Tier 1 + Tier 2; 16 collectors |
| Teacher model | `gemini-2.5-flash` through the direct Gemini API |
| Training target | `unsloth/GLM-4.7-Flash`, 4-bit base, LoRA SFT |
| Hosting | Local DGX storage |
| Current usable dataset | `data/packaged/glm47_v3/` |
| Current usable model | None promoted; candidate selection and an enforcing promotion gate are pending |
| Current evaluation evidence | None suitable for release; complete compatible calibrated base and tuned results are pending |
| Release status | Blocked on an enforcing direct-adapter smoke gate and calibrated comparison |

The repository is a data pipeline. The site under `docs/` (this website) documents how to use and maintain the pipeline.

---

## Phase Status

| No. | Phase | Status | Canonical Input | Current Artifact |
|---|---|---|---|---|
| 1. | Taxonomy and task design | Complete for current scope | Project plan and DFIR requirements | `docs/reference/taxonomy.md`, `configs/task_categories.yaml`, `configs/quality.yaml` |
| 2. | Collection | Complete for 16 sources | `configs/collection.yaml` and public sources | `data/raw/collection_manifest.json` |
| 3. | Synthesis | Complete for reduced subset | Phase 2 raw JSONL | `data/synthesized/gemini_subset_1/` |
| 4. | Quality | Complete for reduced subset | Phase 3 `accepted.jsonl` | `data/quality/gemini_subset_1/` |
| 5. | Packaging | Filtered-only GLM v3 view complete | Phase 4 `filtered.jsonl` | `data/packaged/glm47_v3/` |
| 6. | Training | No promoted model; v5 or staged v6 candidate decision pending | Phase 5 GLM package | `configs/finetune_glm47flash_v5.yaml`, `configs/finetune_glm47flash_v6.yaml` |
| 7. | Evaluation | No compatible calibrated release result | 68 benchmark cases | `configs/evaluation.yaml`, `evaluation/benchmark/` |

---

## Phase 1: Taxonomy And Task Design

The target taxonomy has 57 artifact categories across Windows, Linux, network, SIEM, cloud, file/storage, AI/LLM, mobile, anti-forensics, threat intelligence, IoT/OT, virtualization, supply chain, and compliance domains. The detailed taxonomy can be found in [Taxonomy](../reference/taxonomy.md).

Machine validation and coverage live in `configs/quality.yaml`.

Generation currently targets five categories:

1. Artifact Analysis
2. TTP Identification
3. Triage and Threat Hunting
4. Detection Engineering
5. Incident Report Generation

<box type="info" seamless header="">
<md>
Mobile, OT, deep file forensics, attribution, legal/compliance, and several cloud categories remain intentionally weak or deferred. The taxonomy is broader than the current source coverage so it can serve as an expansion roadmap.
</md>
</box>

---

## Phase 2: Raw Corpus

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

<box type="info" seamless header="">
<md>
Refer to [Source Internals](../developer/source-guide.md) and [Collectors](../developer/collectors.md) for collector specifics.
</md>
</box>

---

## Phase 3: Synthesis Snapshot

The current synthesis run is `run-20260701T021807Z`, stored in `data/synthesized/gemini_subset_1/`.

| Field | Value |
|---|---:|
| Mode | `subset` |
| Model | `gemini-2.5-flash` |
| Prompt records | 6,494 |
| Accepted candidate pairs | 6,287 |
| Rejected prompt rows | 206 |
| Raw output rows | 7,779 |

Artifacts are:
* `prompts.jsonl`
* `raw_outputs.jsonl`
* `accepted.jsonl`
* `rejected.jsonl`
* `generation_manifest.json` 

<box type="warning" seamless header="Deferred full synthesis">

The current synthesis run uses a representative sample of documents from all 16 configured sources, stratified by source, content type, and document-length richness. This reduced run was chosen for budget and time constraint purposes.

Under the current one-pair-per-document configuration, approximately *$70* was spent on API credits, in the generation of the current *~6.5k data rows*.

The planned full-corpus synthesis would have more generated pairs per document, and thus would require an estimated fund of *$500*. This would generate an estimated of *~47k data rows*.  
</box>

<box type="info" seamless header="">
<md>
Refer to [Synthesis](../developer/synthesis.md) for synthesis specifics.
</md>
</box>

---

## Phase 4: Quality Snapshot

The current quality run is `quality-20260708T064057Z`, stored in `data/quality/gemini_subset_1`.

| Status | Pairs |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total checked | 6,287 |

This phase is deterministic and heuristic; it makes no model API calls. 

It checks schema/provenance, taxonomy, ATT&CK/ATLAS identifiers, reasoning links, grounding tags, concrete indicators, tools, source specificity, operational value, duplicates, balance, and distribution. 

<box type="info" seamless header="">
<md>
Only filtered rows are eligible to be packaged. Review and rejected rows remain available for adjudication but are *excluded* from training.
</md>
</box>

<box type="info" seamless header="">
<md>
Refer to [Validation and Quality](../developer/validation-quality.md) and [Quality Rubrics](../developer/quality-rubric.md) for quality gate specifics.
</md>
</box>

---

## Phase 5: Packaging Snapshot

The active training view is `package-20260717T040952Z`, stored in `data/packaged/glm47_v3`.

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

This reasoning and direct split is recommended by [Unsloth](https://unsloth.ai/docs/models/tutorials/glm-4.7-flash#fine-tuning-glm-4.7-flash) in finetuning GLM 4.7 Flash.

<box type="info" seamless header="">
<md>
A GLM export view is created in this phase. The literal `[GENERAL KNOWLEDGE]` annotation is removed, `<reasoning>` tags are mapped to `<think>`, and reasoning chains are stripped for the 25% documents identified for direct answers.
</md>
</box>

<box type="info" seamless header="">
<md>
Refer to [Packaging](../developer/packaging.md) for packaging specifics.
</md>
</box>

---

## Phase 6: Training Snapshot

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

---

## Phase 7: Evaluation Snapshot

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

---

## Active Configuration

| Concern | Current File |
|---|---|
| Sources and paths | `configs/collection.yaml` |
| Source profiles and generation caps | `configs/source_profiles.yaml` |
| Teacher model and retry policy | `configs/synthesis.yaml` |
| Task mix and quality signals | `configs/task_categories.yaml` |
| Taxonomy, scoring, dedupe, balance | `configs/quality.yaml` |
| Active GLM packaging transform | `configs/packaging_glm47_v3.yaml` |
| Active LoRA configuration | `configs/finetune_glm47flash_v5.yaml` |
| Benchmark, target, and judge | `configs/evaluation.yaml` |

LLMs and API Keys involved:
* `GEMINI_API_KEY` is the only project API secret and is required only for Phase 3 generation.
* Phase 6 target and judge endpoints are local OpenAI-compatible servers. The current judge model is `gemma-4-31B-it-Q4_K_M`.

---

## Immediate Work And Release Gates

In order:

1. Fix the v5 smoke script's stop-ID reporting and turn it into a parameterized, enforcing gate covering bounded greeting and DFIR prompts, termination, repetition, and template leakage. Preserve the model's complete stop list.
1. Decide whether v5 or the staged aggressive v6 experiment is the next candidate; always pass its versioned config explicitly because the CLI default is not an active configuration.
1. Record candidate paths, versions, hashes, validation metrics, and selected checkpoint.
1. Finish manual review of all 68 benchmark cases and record owner/date.
1. Build and adjudicate a stratified human-scored judge calibration set; assign a real calibration ID and freeze the judge configuration.
1. Run complete calibrated base and tuned evaluations with the same benchmark and judge.
1. Compare them and review task-level and severe DFIR regressions before any Shepherd integration.

Code hardening still due: reject placeholder calibration IDs in comparison, 
fingerprint target-generation inputs, return nonzero for a failed regression
gate, make checkpoint-set consistency recoverable, add fingerprint-safe
evaluation resume, and add configurable retry/failure for empty target responses.

---

## Sources Of Truth

Use the following precedence when facts disagree:

1. generated run manifests for run-specific counts, paths, IDs, and status;
2. `project_state/PROJECT_BRIEF.md`, `TODO.md`, and `DECISIONS.md` for live
   direction, risks, and next work;
3. this page for the consolidated handover snapshot;
4. stable developer and user pages for operating and maintenance procedures;
5. [Revisions](revisions.md) for superseded snapshots and run history.
