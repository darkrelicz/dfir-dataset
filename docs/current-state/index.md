<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Current Project State

This page reflects the latest repository state inspected on 2026-07-07. The
generated manifests remain the authoritative record for run-specific counts.

## Phase Status

| Phase | Status | Current Artifact |
|---|---|---|
| Phase 1 taxonomy | Complete for current scope | `project_state/TAXONOMY.md`, `configs/quality.yaml` |
| Phase 2 collection | Complete for Core + Tier 1 + Tier 2 | `data/raw/collection_manifest.json` |
| Phase 3 synthesis | Complete for reduced subset | `data/synthesized/gemini_subset_1/` |
| Phase 4 quality | Complete by time-boxed acceptance | `data/quality/gemini_subset_1/` |
| Phase 5 packaging | Complete for local training path | `data/packaged/gemini_subset_1/` |
| Phase 6 evaluation/training | Active next phase | Not implemented in this repo yet |

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

The current quality run is `quality-20260707T024506Z`:

| Status | Pairs |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total checked | 6,287 |

For the shortened deadline, the package-eligible set is filtered plus review
rows. Rejected rows remain ineligible.

## Packaging Snapshot

The current package is `package-20260707T075641Z`:

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

## Current Risk Acceptance

Review rows are included in Phase 5 to preserve enough training volume for the
current deadline. This is a time-boxed risk acceptance, not a statement that
the review queue has been fully adjudicated.

Full-corpus synthesis, Hugging Face publishing, evaluation fixtures, and
training automation are deferred.
