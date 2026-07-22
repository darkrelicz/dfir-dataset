<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Quality And Packaging</h1>

Phase 4 and Phase 5 turn candidate generated pairs into local SFT-ready JSONL.

# Phase 4 Quality

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
| `filtered.jsonl` | Accepted by row-level validation and the enforcing dataset gates |
| `review_queue.jsonl` | Review-severity issues only |
| `rejected.jsonl` | At least one reject-severity issue |
| `manual_spot_check_sample.jsonl` | Deterministic filtered sample using seed 1337 |
| `quality_manifest.json` | Run counts, issue counts, distributions, and audits |

# Row Gates

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

ATT&CK and ATLAS membership is fail-closed against the expected local cache
files. There is no fallback to IDs embedded in raw documents. If a cache is
missing or unreadable, every non-empty mapping list for that framework is
rejected as unknown; confirm the logged reference counts before accepting a run.
Those counts and the cache identities are not stored in `quality_manifest.json`,
so retain the run log when you need durable reference provenance.

Quality scoring is no-API and heuristic. It uses:

* reject issue codes for factual accuracy and reasoning penalties;
* task category `quality_signals`;
* configured generic-answer penalty terms;
* configured operational verbs;
* source-token overlap;
* concrete artifact counts;
* caveat presence and response length.

Scores help with ranking and audits. Row status is decided by issue severity.
They are coarse lexical heuristics, not semantic grading: review-severity
problems may leave factual or reasoning scores at 5, and a concrete artifact can
increase specificity even when it is separately flagged as ungrounded. Scores
also influence duplicate retention and source-balance movement, so inspect issue
codes alongside scores.

Phase 4 does not generally prove that non-indicator final-answer claims are
supported, and it has no standalone check for generic-but-nonempty evidence.
Use the manual sample and review process for those judgments.

# Dataset Gates

After row validation, `quality.dataset.apply_dataset_gates` runs:

* near-duplicate detection using a Jaccard inverted index;
* source-balance review movement;
* category balance audit;
* difficulty balance audit;
* taxonomy coverage audit.

The current reduced subset had zero near duplicates and no source-balance
movement.

Near-duplicate and source-balance processing can change a row's status.
Category, difficulty, and taxonomy results are audits only; out-of-tolerance or
missing values do not fail the run. Source balancing uses one pass based on the
initial filtered total, so verify the reported final source shares manually.

Pairs with fewer than eight distinctive tokens across the instruction and final
answer are not compared by the near-duplicate gate. Identical short pairs can
therefore survive; audit short outputs separately if they are allowed.

# Safe Output Handling

Use a new Phase 4 output directory after confirming that the input and raw
corpus paths are readable. In normal replacement mode, the runner deletes the
existing filtered, review, and rejected JSONL files before it loads raw documents
or opens the input. A later failure can leave those files empty while an older
manifest and spot-check sample remain.

Do not use `--append` for a packaging input. Append mode adds current rows to the
three existing output streams, but duplicate/balance gates inspect only the
current input and the manifest and spot-check sample are replaced with
current-batch-only data.

Process success does not mean the dataset passed a release threshold. Empty or
all-rejected inputs, ordinary rejection volume, distribution tolerance failures,
and taxonomy gaps still return success after outputs are written. Inspect counts,
reference-set logs, final source shares, and every audit before packaging.

The quality configuration has no schema or range validation. Before a run,
review scoring weights, thresholds, tolerances, reasoning limits, and sample
sizes; numeric but out-of-range values can silently weaken filtering.

# Current Quality Result

The latest quality run is `quality-20260708T064057Z`.

| Status | Count |
|---|---:|
| Filtered | 4,152 |
| Review | 1,365 |
| Rejected | 770 |
| Total | 6,287 |

The biggest rejection and review pressures are invented concrete indicators and
mapping inconsistencies.

# Phase 5 Packaging

The packager is `dataset_packaging.runner.run_packaging`, dispatched by
`scripts/package_dataset.py`.

Active GLM config:

* quality input directory: `data/quality/gemini_subset_1`
* output directory: `data/packaged/glm47_v3`
* splits: 80 percent train, 10 percent validation, 10 percent test
* split grouping: `source_doc_id`
* seed: 1337

The v3 package consumes only `filtered.jsonl`. Rows in `review_queue.jsonl` are
not loaded, and a non-filtered `quality_status` in the filtered input fails
packaging validation.

Response style policy:

| Quality status | Packaged style |
|---|---|
| `filtered` | Deterministic 75% reasoning / 25% direct split |
| `review` | Excluded |
| `rejected` | Excluded |

The GLM v3 exporter strips the canonical reasoning block from direct examples,
removes literal `[GENERAL KNOWLEDGE]` annotations, and maps retained reasoning
blocks from `<reasoning>` to `<think>`. These transforms are recorded in metadata
and apply only to the training view.

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

`package-20260717T040952Z` has 4,152 records: 3,322 train, 415 validation,
and 415 test. It contains 3,114 reasoning and 1,038 direct examples with no
source-document overlap. Validation found no retained grounding annotations,
canonical reasoning tags, unbalanced thinking blocks, or empty responses.
