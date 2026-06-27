# Quality Rubric

## Purpose

Define the Phase 4 quality gate for candidate instruction pairs. Phase 4 consumes Phase 3 `accepted.jsonl` and produces filtered training candidates, review queues, rejection manifests, and quality summaries.

## Required Outputs

| Output | Purpose |
|---|---|
| `filtered.jsonl` | Pairs accepted for packaging |
| `rejected.jsonl` | Pairs rejected with reasons |
| `review_queue.jsonl` | Pairs that need manual or AI-assisted review |
| `quality_manifest.json` | Run metadata, counts, distributions, thresholds |

## Deterministic Validators

These checks should run before heuristic scoring.

| Validator | Reject | Review | Notes |
|---|---|---|---|
| Schema validity | Invalid row shape or missing required fields |  | Validate against canonical schemas |
| Source provenance | Missing or unknown `source_doc_id`/`source` |  | Pair must map to a raw source document |
| Category/difficulty | Invalid label |  | Must match configured labels |
| Taxonomy refs | Unknown taxonomy IDs |  | Use `configs/quality.yaml` |
| ATT&CK IDs | Malformed ID | Candidate mapping may go to review | Allow `?` suffix if policy permits |
| ATLAS IDs | Malformed ID | Candidate mapping may go to review | Validate separately from ATT&CK |
| Reasoning links | Broken evidence/analysis/conclusion/caveat references |  | Reuse Phase 3 reasoning validator |
| Empty evidence | Evidence lines are empty or purely generic |  |  |
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
| `taxonomy_invalid` | Unknown taxonomy reference |
| `attack_id_invalid` | Invalid ATT&CK technique ID |
| `atlas_id_invalid` | Invalid ATLAS technique ID |
| `reasoning_links_invalid` | Broken reasoning ID references |
| `invented_indicator` | Concrete indicator absent from source |
| `unsupported_claim` | Claim not supported by reasoning/source |
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
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "total_pairs": 0,
  "accepted_pairs": 0,
  "review_pairs": 0,
  "rejected_pairs": 0,
  "thresholds": {
    "accept_score": 3.5,
    "review_score": 3.0
  },
  "rejection_counts": {},
  "category_distribution": {},
  "difficulty_distribution": {},
  "source_distribution": {},
  "taxonomy_distribution": {},
  "notes": []
}
```
