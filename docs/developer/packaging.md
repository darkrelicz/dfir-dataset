<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Packaging</h1>

Phase 5 turns filtered canonical rows into model-specific chat JSONL and
source-document-isolated splits. This page owns package inputs, transforms,
contracts, split policy, validation, and export extensions.

# Visual Overview

## Macro View

<puml src="../diagrams/packaging-macro.puml" alt="Macro view of dataset packaging" width="900" />

## Model Transformation Detail

<puml src="../diagrams/packaging-transform-detail.puml" alt="Detailed model-specific response transformation flow" width="500" />

## Source-Isolated Split Detail

<puml src="../diagrams/packaging-split-detail.puml" alt="Detailed source-document-isolated split sequence" width="950" />

# CLI

`scripts.package_dataset` dispatches to `dataset_packaging.runner.run_packaging`.

Always pass the active config and paths explicitly. The current GLM-specific
view uses:

```bash
python -m scripts.package_dataset \
  --config configs/packaging_glm47_v3.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_v3
```

# Inputs

Current config reads:

* `data/quality/gemini_subset_1/filtered.jsonl`
* `data/quality/gemini_subset_1/quality_manifest.json`

The packager does not read Phase 4 `review_queue.jsonl` or `rejected.jsonl`.
It rejects the filtered input if any row is not marked
`quality_status: filtered`.

# Record Building

`build_packaged_record` creates:

* stable sequential ID: `dfir-000001`, etc.;
* optional system message from config;
* user message from `instruction`;
* assistant message from `response` or stripped final answer;
* metadata preserving source, taxonomy, mapping, quality, prompt, model, and
  provenance fields.

`format_content_by_reasoning_style` returns:

* full response for `reasoning`;
* `final_answer_text(response)` for `direct`;
* an explicit packaging failure if a direct answer cannot be extracted.

# Response Style Policy

Current `configs/packaging_glm47_v3.yaml`:

```yaml
response_style:
  filtered:
    reasoning: 0.75
    direct: 0.25
```

The configured split seed deterministically assigns 75 percent of eligible
filtered rows to the full reasoning response and strips the reasoning block from
the remaining 25 percent to create direct-answer examples.

# GLM-Specific Training View

`configs/packaging_glm47_v3.yaml` adds export-time transforms:

* remove literal `[GENERAL KNOWLEDGE]` annotations from assistant text;
* convert canonical `<reasoning>` tags to GLM-native `<think>` tags;
* preserve the applied transforms in record metadata;
* reject empty responses, retained annotations/canonical tags, and unbalanced
  `<think>` blocks.

These transforms do not mutate synthesis or quality outputs. The generated
package and response mix are reported in [Current
State](../current-state/index.md#phase-5-packaging-snapshot).

# Splitting

`split_records_by_source_doc` groups records by
`metadata.source_doc_id`, shuffles groups with seed 1337, sorts groups by size
descending, then repeatedly assigns the next group to the split with the highest
remaining target ratio.

This prevents a source document from appearing in multiple splits.

# Manifest

`PackagingManifest` records:

* package run ID;
* created timestamp;
* config path;
* input quality directory;
* quality run ID;
* output directory;
* packaged pair count;
* response style counts/fractions;
* split config;
* split paths/counts/source-doc counts;
* source-doc overlap by split pair.

Treat non-empty overlap in any split comparison as a packaging failure.

# Packaged Row Contract

Each JSONL row contains a stable package ID, ordered `system`/`user`/`assistant`
messages, and metadata preserving:

- `source_doc_id`, source, task, difficulty, confidence, and grounding;
- taxonomy, ATT&CK/ATLAS, and tool references;
- quality status, issues, score, and quality run ID;
- synthesis run, prompt, pair, model, and generation provenance;
- selected reasoning style and applied model transforms.

The canonical quality record remains unchanged. A direct row contains only the
extracted final answer; a reasoning row retains the canonical response before
configured model transforms are applied.

# Configuration

Packaging config owns:

- output format and optional system message;
- train/validation/test fractions, seed, and grouping key;
- reasoning/direct fractions;
- model-specific tag and annotation transformations.

`configs/packaging_glm47_v3.yaml` is the current compatible GLM view.
`configs/packaging.yaml` uses an older scalar response-style shape and is not
compatible with the current runner. Always pass the intended config explicitly.
Reasoning/direct fractions must sum to 1.0.

# Validation Ladder

1. Parse the complete Phase 4 `filtered.jsonl` and reject any row whose status
   is not `filtered`.
2. Package a small fixture containing reasoning, direct, grounding annotation,
   and malformed-response cases.
3. Validate message order and non-empty assistant content.
4. Confirm expected response-style counts and deterministic assignment.
5. Confirm model-native tags are balanced and forbidden canonical tags or
   annotations are absent.
6. Reconcile split row counts with the manifest.
7. Confirm every source-document overlap list is empty.
8. Load all three split files with the intended training reader.

The runner validates model transformations, but training preflight must still
reconcile every row, role order, tag balance, and source-document split against
the manifest.

# Changing Packaging

To add a response style or model family:

1. keep canonical synthesis and quality inputs model-neutral;
2. implement the transformation in `dataset_packaging/`;
3. preserve source, quality, and prompt provenance;
4. group splits by `source_doc_id`;
5. validate empty output, forbidden tags, and balanced model-native tags;
6. record applied transforms and response-style counts in rows and the manifest;
7. add a versioned model-specific packaging config and fixtures;
8. update [Fine-tuning](finetuning.md) if the rendered training contract changes.

Never add hosting or publishing as an implicit packaging side effect. Current
artifacts remain local; a hosting decision requires an explicit durable project
decision.

# Output Lifecycle

Treat the output directory as one immutable package version. Preserve
`train.jsonl`, `validation.jsonl`, `test.jsonl`, `packaging_manifest.json`, the
exact config, input quality manifest, and code revision together. Rebuild into a
new directory after changing input rows, split policy, system message, response
style, or transforms.
