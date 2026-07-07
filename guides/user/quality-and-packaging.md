# Quality And Packaging

Phase 4 and Phase 5 turn candidate generated pairs into local SFT-ready JSONL.

## Phase 4 Quality

The quality runner is `quality.runner.run_quality_filter`, dispatched by
`scripts/quality_filter.py`.

Inputs:

* `data/synthesized/<run>/accepted.jsonl`
* raw source documents under `data/raw/`
* `configs/quality.yaml`
* `configs/task_categories.yaml`

Outputs:

| File | Purpose |
|---|---|
| `filtered.jsonl` | No row-level issues after deterministic gates |
| `review_queue.jsonl` | Review-severity issues only |
| `rejected.jsonl` | At least one reject-severity issue |
| `manual_spot_check_sample.jsonl` | Deterministic filtered sample using seed 1337 |
| `quality_manifest.json` | Run counts, issue counts, distributions, and audits |

## Row Gates

Phase 4 validates:

* JSON and `QualityCandidate` shape.
* Source document existence and source match.
* Category labels from `configs/task_categories.yaml`.
* Taxonomy refs from `configs/quality.yaml`.
* ATT&CK and ATLAS ID format and local reference membership.
* Tool names against source text and configured allowlist.
* Canonical `<reasoning>` structure.
* Grounding field versus `[GENERAL KNOWLEDGE]` tags.
* Concrete indicators absent from source text.

Quality scoring is no-API and heuristic. It uses:

* reject issue codes for factual accuracy and reasoning penalties;
* task category `quality_signals`;
* configured generic-answer penalty terms;
* configured operational verbs;
* source-token overlap;
* concrete artifact counts;
* caveat presence and response length.

Scores help with ranking and audits. Row status is decided by issue severity.

## Dataset Gates

After row validation, `quality.dataset.apply_dataset_gates` runs:

* near-duplicate detection using a Jaccard inverted index;
* source-balance review movement;
* category balance audit;
* difficulty balance audit;
* taxonomy coverage audit.

The current reduced subset had zero near duplicates and no source-balance
movement.

## Current Quality Result

The latest quality run is `quality-20260707T024506Z`.

| Status | Count |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total | 6,287 |

The biggest rejection and review pressures are invented concrete indicators and
mapping inconsistencies.

## Phase 5 Packaging

The packager is `dataset_packaging.runner.run_packaging`, dispatched by
`scripts/package_dataset.py`.

Current config:

* quality input directory: `data/quality/gemini_subset_1`
* output directory: `data/packaged/gemini_subset_1`
* splits: 80 percent train, 10 percent validation, 10 percent test
* split grouping: `source_doc_id`
* seed: 1337

The current time-boxed package consumes both `filtered.jsonl` and
`review_queue.jsonl`.

Response style policy:

| Quality status | Packaged style |
|---|---|
| `filtered` | Keep canonical `<reasoning>` response |
| `review` | Strip the reasoning block and keep the final answer |
| `rejected` | Excluded |

The output record shape is `messages_jsonl`:

```json
{
  "id": "dfir-000001",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {
    "source_doc_id": "...",
    "quality_status": "filtered",
    "reasoning_style": "reasoning"
  }
}
```

The current package has 5,517 records and no source-document overlap across
splits.
