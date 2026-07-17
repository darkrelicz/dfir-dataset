<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Packaging</h1>

Phase 5 exports local chat JSONL for the current Unsloth/GLM training path.

<puml src="../diagrams/packaging-sequence.puml" alt="Phase 5 packaging sequence" width="900" />

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
`package-20260717T040952Z` contains 4,152 records: 3,322 train, 415 validation,
and 415 test, with no source-document overlap. Its response mix is 3,114
reasoning and 1,038 direct examples.

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

The current manifest reports empty overlap for all split comparisons.
