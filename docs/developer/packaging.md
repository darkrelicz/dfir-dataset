# Packaging

Phase 5 exports local chat JSONL for the current Unsloth/GLM training path.

<puml src="../diagrams/packaging-sequence.puml" alt="Phase 5 packaging sequence" width="900" />

## CLI

`scripts.package_dataset` dispatches to `dataset_packaging.runner.run_packaging`.

```bash
python -m scripts.package_dataset --config configs/packaging.yaml
```

Optional overrides:

```bash
python -m scripts.package_dataset \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/gemini_subset_1
```

## Inputs

Current config reads:

* `data/quality/gemini_subset_1/filtered.jsonl`
* `data/quality/gemini_subset_1/review_queue.jsonl`
* `data/quality/gemini_subset_1/quality_manifest.json`

The packager does not read Phase 4 `rejected.jsonl`.

## Record Building

`build_packaged_record` creates:

* stable sequential ID: `dfir-000001`, etc.;
* optional system message from config;
* user message from `instruction`;
* assistant message from `response` or stripped final answer;
* metadata preserving source, taxonomy, mapping, quality, prompt, model, and
  provenance fields.

`assistant_content_for_style` returns:

* full response for `reasoning`;
* `final_answer_text(response)` for `direct`;
* full response as fallback if no final answer can be extracted.

## Response Style Policy

Current `configs/packaging.yaml`:

```yaml
response_style:
  filtered: "reasoning"
  review: "direct"
  direct_transform: "strip_reasoning_block"
```

This yields the current 75/25 reasoning/direct mix without another generation
run.

## Splitting

`split_records_by_source_doc` groups records by
`metadata.source_doc_id`, shuffles groups with seed 1337, sorts groups by size
descending, then repeatedly assigns the next group to the split with the highest
remaining target ratio.

This prevents a source document from appearing in multiple splits.

## Manifest

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
