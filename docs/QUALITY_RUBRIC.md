# Quality Rubric

## Purpose

Define the Phase 4 quality gate for candidate instruction pairs. Phase 4 consumes Phase 3 `accepted.jsonl` and produces filtered training candidates, review queues, rejection manifests, and quality summaries.

## Current Implementation

The implementation lives in `quality/` and is run with `scripts/quality_filter.py`. It does not call Phase 3's generated-output validators. It uses independent Phase 4 row validators, local ATT&CK/ATLAS STIX/YAML reference caches when present, raw-corpus fallback references, a configurable tool allowlist, heuristic rubric scoring, near-duplicate checks, source/category/difficulty/tactic/taxonomy audits, and writes all required output files plus `quality_manifest.json`. The CLI defaults to `--log-level INFO` and logs each major sub-stage so long runs show visible progress. Semantic unsupported-claim adjudication remains review work because deterministic code cannot reliably prove every fuzzy forensic claim.

Current reduced-pair snapshot: `data/quality/gemini_subset_1/quality_manifest.json` from run `quality-20260701T064847Z` checked 6,023 candidate pairs, filtered 1,134, routed 4,144 to review, rejected 745, found zero near-duplicates above the 0.8 Jaccard threshold, covered 15/15 local ATT&CK tactic labels, covered 16/16 ATLAS tactics, and covered 26/57 taxonomy IDs.

## Required Outputs

| Output | Purpose |
|---|---|
| `filtered.jsonl` | Pairs accepted for packaging |
| `rejected.jsonl` | Pairs rejected with reasons |
| `review_queue.jsonl` | Pairs that need manual or AI-assisted review |
| `quality_manifest.json` | Run metadata, counts, distributions, thresholds |
| `manual_spot_check_sample.jsonl` | Deterministic 100-pair filtered sample for manual rubric scoring |

## Running Phase 4

```bash
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/gemini_subset_1/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/gemini_subset_1 \
  --log-level INFO
```

The logger reports config loading, output preparation, raw document loading, reference-set construction, row-level validation progress every 1,000 rows, each dataset-level audit, JSONL output writing, spot-check sampling, and manifest writing.

## Deterministic Validators

These checks should run before heuristic scoring.

| Validator | Reject | Review | Notes |
|---|---|---|---|
| Schema validity | Invalid row shape or missing required fields |  | Validate against canonical schemas |
| Source provenance | Missing or unknown `source_doc_id`/`source` |  | Pair must map to a raw source document |
| Category/difficulty | Invalid label |  | Must match configured labels |
| Taxonomy refs | Unknown taxonomy IDs |  | Use `configs/quality.yaml` |
| ATT&CK IDs | Malformed or absent from local ATT&CK STIX/reference cache | Candidate mapping may go to review | Allow `?` suffix for candidate mappings |
| ATLAS IDs | Malformed or absent from local ATLAS YAML/reference cache | Candidate mapping may go to review | Validate separately from ATT&CK |
| Tool names |  | Tool absent from source text and allowlist | Configured in `configs/quality.yaml` and expanded from raw tool-like sources |
| Reasoning links | Broken evidence/analysis/conclusion/caveat references | Reasoning step count above configured maximum | Use independent Phase 4 reasoning parser |
| Empty evidence | Evidence lines are empty or purely generic |  |  |
| Grounding/tag consistency | `source_only` contains `[GENERAL KNOWLEDGE]`, or `source_plus_general` lacks the tag | Untagged unsupported claims need semantic review | Use independent Phase 4 grounding checks |
| Final-answer consistency | Final answer introduces unsupported findings |  | May need heuristic/AI assist |
| Invented concrete indicators | Concrete path/hash/IP/user/host/event not present in source |  | Strict for source-only outputs |

## Heuristic Scoring

Suggested weights:

| Dimension | Weight | Score 1 | Score 3 | Score 5 |
|---|---:|---|---|---|
| Factual accuracy | 25% | Unsupported or contradicted | Mostly supported, minor ambiguity | Fully source-grounded |
| Reasoning quality | 25% | Broken or circular | Mostly coherent | Clear evidence-to-conclusion chain |
| Operational relevance | 20% | Academic or vague | Some useful next steps | Directly useful to an analyst |
| Specificity | 15% | Generic | Some source detail | Specific without invention |
| Completeness | 15% | Missing key fields or caveats | Adequate | Complete and well-calibrated |

Composite threshold:

- Accept: `>= 3.5` and no hard rejection issues
- Review: `>= 3.0` with fuzzy concerns, or strong content with one reviewable issue
- Reject: `< 3.0` or any hard rejection issue

## Manual Review Guidance

Manual reviewers should ask:

1. Is every concrete claim supported by source evidence?
2. Would this answer help an incident responder make a better decision?
3. Does the response avoid declaring compromise without corroboration?
4. Are caveats real and specific, not boilerplate?
5. Is the reasoning trace auditable?
6. Is this pair too similar to another pair?

## Rejection Reasons

Use stable reason codes so later analysis is easy.

| Code | Meaning |
|---|---|
| `schema_invalid` | Row does not match expected schema |
| `source_missing` | Source document cannot be found |
| `source_mismatch` | Row source does not match the raw source document |
| `category_invalid` | Category is not configured |
| `taxonomy_invalid` | Unknown taxonomy reference |
| `attack_id_invalid` | Invalid ATT&CK technique ID |
| `atlas_id_invalid` | Invalid ATLAS technique ID |
| `mapping_inconsistency` | Response mapping IDs and metadata mapping IDs disagree |
| `reasoning_links_invalid` | Broken reasoning ID references |
| `reasoning_too_long` | Reasoning chain exceeds configured step-count maximum |
| `tool_name_unknown` | Tool is absent from source text and allowlist |
| `grounding_mismatch` | `grounding` field does not match `[GENERAL KNOWLEDGE]` tag usage |
| `invented_indicator` | Concrete indicator absent from source |
| `unsupported_claim` | Claim not supported by reasoning/source |
| `low_quality_score` | Heuristic rubric score is below the configured threshold |
| `low_specificity` | Too generic for useful training |
| `low_operational_value` | Does not help a real workflow |
| `duplicate_or_near_duplicate` | Redundant with existing pair |
| `source_overrepresented` | Accepted only if needed for balance |

## Distribution Audits

Run these after filtering:

| Audit | Target |
|---|---|
| Task category distribution | Within agreed tolerance of `configs/task_categories.yaml` |
| Difficulty distribution | Near 30/50/20 unless intentionally changed |
| Source balance | No single source dominates the final dataset |
| ATT&CK tactic coverage | All applicable tactics represented |
| ATLAS coverage | AI/ML coverage documented honestly |
| Taxonomy heatmap | Covered, thin, and absent categories visible |
| Duplicate audit | Sigma/Hayabusa and repeated advisory patterns checked |

## Spot Check Template

| Pair ID | Source | Category | Score | Decision | Notes |
|---|---|---|---:|---|---|
|  |  |  |  |  |  |

## Quality Manifest Template

```json
{
  "run_id": "quality-YYYYMMDDTHHMMSSZ",
  "input_path": "data/synthesized/full/accepted.jsonl",
  "raw_dir": "data/raw",
  "output_dir": "data/quality/full",
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "total_pairs": 0,
  "filtered_pairs": 0,
  "review_pairs": 0,
  "rejected_pairs": 0,
  "rejection_counts": {},
  "review_counts": {},
  "source_distribution": {},
  "category_distribution": {},
  "difficulty_distribution": {},
  "taxonomy_distribution": {},
  "score_threshold": 3.5,
  "review_threshold": 3.0,
  "dataset_audits": {
    "near_duplicates": {},
    "source_balance": {},
    "category_balance": {},
    "difficulty_balance": {},
    "attack_tactic_coverage": {},
    "atlas_tactic_coverage": {},
    "taxonomy_coverage": {},
    "manual_spot_check": {}
  },
  "notes": []
}
```

Older notes may refer to accepted pairs at this stage; the implemented Phase 4 name is `filtered_pairs` because Phase 3 `accepted.jsonl` remains candidate data until quality filtering.

The historical plan's `~10,000-15,000` filtered-pair target applied to the full synthesis path. Under the reduced subset budget, the expected filtered count is materially lower and should be judged against coverage and training budget, not the old full-corpus target.
