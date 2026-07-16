<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Current Project State

This page reflects the latest repository state inspected on 2026-07-16. The
generated manifests remain the authoritative record for run-specific counts.

## Phase Status

| Phase | Status | Current Artifact |
|---|---|---|
| Phase 1 taxonomy | Complete for current scope | `project_state/TAXONOMY.md`, `configs/quality.yaml` |
| Phase 2 collection | Complete for Core + Tier 1 + Tier 2 | `data/raw/collection_manifest.json` |
| Phase 3 synthesis | Complete for reduced subset | `data/synthesized/gemini_subset_1/` |
| Phase 4 quality | Complete by time-boxed acceptance | `data/quality/gemini_subset_1/` |
| Phase 5 packaging | Complete for local training path | `data/packaged/gemini_subset_1/` |
| Phase 6 training | First LoRA SFT run complete | `data/finetune/glm47_flash_lora_dfir_subset1/training_manifest.json` |
| Phase 6 evaluation | Exploratory base run complete; calibrated comparison pending | `data/evaluation/glm47-flash-base/` |

## Raw Corpus

The current raw corpus contains 20,347 documents across 16 collectors.

| Source | Raw Documents |
|---|---:|
| `mitre_attack` | 697 |
| `sigma_rules` | 3,111 |
| `atomic_red_team` | 1,811 |
| `cisa_advisories` | 3,849 |
| `volatility3_docs` | 194 |
| `mitre_atlas` | 262 |
| `cisa_kev` | 270 |
| `kape_files` | 811 |
| `hayabusa_rules` | 4,839 |
| `lolbas_gtfobins` | 720 |
| `forensic_artifacts` | 731 |
| `velociraptor_artifacts` | 437 |
| `hijacklibs` | 590 |
| `loldrivers` | 656 |
| `ossem_data_dicts` | 699 |
| `cybersec_skills` | 670 |

## Synthesis Snapshot

The current synthesis run is `run-20260701T021807Z`:

| Field | Value |
|---|---:|
| Mode | `subset` |
| Model | `gemini-2.5-flash` |
| Prompt count | 6,494 |
| Accepted candidate pairs | 6,287 |
| Rejected prompt rows | 206 |
| Raw output rows | 7,779 |

Phase 3 `accepted.jsonl` is candidate synthesis output. It is not final training
data until Phase 4 quality has run.

## Quality Snapshot

The current quality run is `quality-20260708T064057Z`:

| Status | Pairs |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total checked | 6,287 |

For the shortened deadline, the package-eligible set is filtered plus review
rows. Rejected rows remain ineligible.

## Packaging Snapshot

The current package is `package-20260708T071253Z`:

| Split | Records |
|---|---:|
| Train | 4,414 |
| Validation | 552 |
| Test | 551 |
| Total | 5,517 |

The package has no `source_doc_id` overlap across train, validation, and test.

Response style mix:

| Style | Count | Fraction |
|---|---:|---:|
| Canonical reasoning | 4,152 | 0.7526 |
| Direct answer | 1,365 | 0.2474 |

Filtered rows keep the canonical `<reasoning>` response. Review rows are
converted to direct-answer examples by stripping the reasoning block.

## Training Snapshot

The first LoRA SFT run is `train-20260714T025314Z`:

| Field | Value |
|---|---|
| Base model | `unsloth/GLM-4.7-Flash` |
| Method | Unsloth LoRA SFT with a 4-bit-loaded base model |
| Training records | 4,414 |
| Epochs / steps | 1 / 552 |
| Final training loss | 0.95973044 |
| Runtime | 38,018.77 seconds |
| LoRA adapter | `data/finetune/glm47_flash_subset1/lora_adapter` |
| Q4_K_M GGUF | `data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf` |

The current training manifest has reproducibility defects that must be fixed
before another run: its `training` mapping is empty because the runner reads the
wrong config key, `loftq_config` was serialized as the string `"None"`, and the
configured GGUF directory differs from the actual `_gguf` output directory.

## Evaluation Snapshot

`glm47-flash-base` completed all 68 benchmark cases using the local
`gemma-4-31B-it-Q4_K_M.gguf` judge. The runner generated and judged each case
sequentially and checkpointed all run outputs after every verdict.

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

These values are diagnostic only. The scorecard records
`judge_calibration_id: uncalibrated`, and every case is flagged for manual
review by the current score builder. A `complete` run status means all cases
were written; it does not make the judge calibrated or the score deployment
evidence.

## Current Risk Acceptance

Review rows are included in Phase 5 to preserve enough training volume for the
current deadline. This is a time-boxed risk acceptance, not a statement that
the review queue has been fully adjudicated.

Full-corpus synthesis and Hugging Face publishing are deferred. The next gate
is to finish benchmark review, adjudicate a separate human-scored judge
calibration set, assign a non-placeholder calibration ID, and rerun complete
base and tuned evaluations with the frozen judge. Shepherd integration remains
blocked until that comparison passes both the overall and task-regression gates
and receives qualitative review.
