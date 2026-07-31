<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Packaging</h1>

Packaging turns filtered, model-neutral quality rows into a deterministic
training view and source-document-isolated train, validation, and test files. It
is the only stage allowed to introduce model-native response tags. This page
describes the architecture, record transformation, validation, grouped split
algorithm, manifest, output lifecycle, and model-family extension workflow.

## Architecture

<puml src="../diagrams/packaging-macro.puml" alt="Macro view of dataset packaging" width="900" />

Packaging is a pure local transformation: it reads Phase 4 artifacts, builds all
chat records in memory, validates the model-specific view, groups records by
source document, writes three JSONL splits, and records package metadata. It
does not call a model, modify canonical quality rows, train anything, or publish
artifacts.

The central boundary is:

```text
canonical filtered row
  → configured reasoning/direct view
  → model-specific text transforms
  → system/user/assistant record
  → source-grouped split
```

### Model View Flow

<puml src="../diagrams/packaging-transform-detail.puml" alt="Detailed model-specific response transformation flow" width="500" />

Response-style selection happens before model transforms. A reasoning row keeps
the complete canonical response; a direct row extracts only text after the
canonical reasoning block. The resulting assistant content is then transformed
for the target model and validated without writing back to Phase 4.

### Source-Isolated Split Flow

<puml src="../diagrams/packaging-split-detail.puml" alt="Detailed source-document-isolated split sequence" width="950" />

Every packaged record derived from the same `source_doc_id` is assigned to one
split as a group. This prevents source evidence from leaking across
train/validation/test even when a source document produced multiple pairs.

### Component Ownership

| Component | Responsibility |
|---|---|
| `scripts/package_dataset.py` | Thin CLI, logging setup, and exit-code handoff |
| `dataset_packaging/runner.py` | Input checks, style assignment, transforms, row validation, grouping, splitting, writing, and manifest |
| `dataset_packaging/schemas.py` | Manifest and per-split summary contracts |
| `validation.reasoning.final_answer_text` | Extract the direct-answer view from a canonical response |
| `configs/packaging*.yaml` | System message, response-style mix, split policy, and model transforms |

### Contracts And Trust Boundaries

`PackagingManifest` and `PackagedSplitSummary` are Pydantic models. Packaged
training rows themselves are plain dictionaries validated by
`validate_packaged_records`; there is no Pydantic row/message schema.

The packager trusts most canonical metadata and preserves selected fields
without validating their types. Its enforcing checks cover filtered status,
message role order, non-empty content, `source_doc_id`, response style, grounding
annotation removal, and reasoning-tag structure. Training preflight remains a
separate required boundary.

---

## CLI And Runner

`scripts.package_dataset` dispatches to `dataset_packaging.runner.run_packaging`.

Always pass the active config and paths explicitly. The current GLM-specific
view uses:

```bash
python -m scripts.package_dataset \
  --config configs/packaging_glm47_v3.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_v3
```

The CLI defaults to `configs/packaging.yaml`, whose legacy scalar
`response_style.filtered` is incompatible with the current runner. Always pass
a current versioned config explicitly.

### Runner Sequence

`run_packaging`:

1. loads the packaging YAML as an untyped mapping;
2. resolves fixed input names under the quality directory and output names under
   the package directory;
3. loads `quality_manifest.json` and every row in `filtered.jsonl`;
4. rejects empty input or any row whose `quality_status` is not exactly
   `filtered`;
5. assigns the configured reasoning/direct mix with the split seed;
6. builds and validates every packaged record in memory;
7. groups and assigns records to train/validation/test;
8. deletes existing split and manifest paths in the output directory;
9. writes the three split files;
10. builds and writes the packaging manifest;
11. prints counts and returns zero.

The loaded quality manifest contributes only `quality_run_id`; the runner does
not reconcile its filtered count, input identity, or config with
`filtered.jsonl`.

---

## Input Contract

Current config reads:

* `data/quality/gemini_subset_1/filtered.jsonl`
* `data/quality/gemini_subset_1/quality_manifest.json`

The packager does not read Phase 4 `review_queue.jsonl` or `rejected.jsonl`.
It rejects the filtered input if any row is not marked
`quality_status: filtered`.

---

## Record Transformation Implementation

### Record Building

`build_packaged_record` creates:

- sequential ID from current filtered-row order: `dfir-000001`, etc.;
- required non-empty system message from config;
- user message from `instruction`;
- assistant message from `response` or stripped final answer;
- metadata preserving source, taxonomy, mapping, quality, prompt, model, and
  provenance fields.

IDs are deterministic only while input row order remains unchanged. They are
not derived from prompt/source identity.

`format_content_by_reasoning_style` returns:

* full response for `reasoning`;
* `final_answer_text(response)` for `direct`;
* an explicit packaging failure if a direct answer cannot be extracted.

### Response Style Assignment

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

`assign_response_styles` validates non-negative fractions summing to 1.0,
computes `round(row_count * direct_fraction)`, assigns all remaining rows to
reasoning, and shuffles the style list with the split seed before zipping it to
input order. The mix is deterministic but is not stratified by source, category,
difficulty, or eventual split.

### Model-Specific Transforms And Validation

`configs/packaging_glm47_v3.yaml` adds export-time transforms:

* remove literal `[GENERAL KNOWLEDGE]` annotations from assistant text;
* convert canonical `<reasoning>` tags to GLM-native `<think>` tags;
* preserve the applied transforms in record metadata;
* reject empty responses, retained annotations/canonical tags, and unbalanced
  `<think>` blocks.

These transforms do not mutate synthesis or quality outputs. The generated
package and response mix are reported in [Current
State](../current-state/index.md#phase-5-packaging-snapshot).

`apply_model_specific_transforms` removes only the exact literal annotation,
replaces canonical reasoning tag strings with GLM tags when enabled, strips
trailing line whitespace, and records applied transforms. The current row stores
`model_transforms` as `str(set)` rather than a structured list, so its textual
ordering is not a stable contract.

`validate_packaged_records` requires exactly three ordered
`system`/`user`/`assistant` messages, non-empty message content, a usable
`source_doc_id`, and a `reasoning` or `direct` style. It checks expected and
forbidden reasoning tags as complete stripped lines and verifies annotation
removal. It does not re-run quality validation or validate every metadata field.

### Packaged Row Shape

Each JSONL row contains a sequential package ID, ordered
`system`/`user`/`assistant` messages, and metadata preserving:

- `source_doc_id`, source, task, difficulty, confidence, and grounding;
- taxonomy, ATT&CK/ATLAS, and tool references;
- quality status, issues, score, and quality run ID;
- synthesis run, prompt, pair, model, and generation provenance;
- selected reasoning style and applied model transforms.

The canonical quality record remains unchanged. A direct row contains only the
extracted final answer; a reasoning row retains the canonical response before
configured model transforms are applied. `source_pair_key` combines
`prompt_id:pair_index`; it is recorded as provenance but is not used for split
grouping.

---

## Split Implementation

### Grouped Assignment

`split_records_by_source_doc` groups records by
`metadata.source_doc_id`, shuffles groups with seed 1337, sorts groups by size
descending, then repeatedly assigns the next group to the split with the highest
remaining target ratio.

This prevents a source document from appearing in multiple splits.

The seeded shuffle establishes a deterministic tie order before the stable
size-descending sort. For each group, `choose_split` selects the split with the
largest remaining-target ratio; ties follow `train`, `validation`, `test` order.
Whole-group assignment means actual counts can differ from requested targets.

### Target Calculation

`split_targets` calculates train and validation targets with Python `round`, then
sets test to the remaining rows. The configured `split.test` value is not used
in this calculation. The runner does not validate that split fractions are
non-negative or sum to 1.0.

### Manifest

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

The runner computes pairwise source-document overlap after splitting and records
it in the manifest, but it does not raise when overlap is non-empty. Consumers
and training preflight must enforce empty overlap. The manifest's `split_config`
echoes the configured test fraction even though target calculation derives test
as the remainder.

---

## Configuration, Validation, And Lifecycle

### Configuration

Packaging config currently declares:

- required system message;
- train/validation/test fractions, seed, and grouping key;
- reasoning/direct fractions;
- model-specific tag and annotation transformations.

`configs/packaging_glm47_v3.yaml` is the current compatible GLM view.
`configs/packaging.yaml` and `configs/packaging_glm47_v2.yaml` use an older
scalar response-style shape and are not compatible with the current runner.
Always pass the intended config explicitly.

The current runner ignores `format.record_format`, `preflight`, and any
configured grouping key; it always emits message JSONL and groups by
`source_doc_id`. Only `remove_general_knowledge_annotations` and
`glm_reasoning_tags` are implemented model-transform keys.

### Validation Ladder

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

### Output Lifecycle

Record building, validation, and splitting finish before existing output files
are removed. `prepare_output_dir` then deletes the three split paths and old
manifest, writes splits sequentially, and writes the manifest last. Writes are
not transactional; a failure during output can leave a partial package without
a current manifest.

Treat the output directory as one immutable package version. Preserve
`train.jsonl`, `validation.jsonl`, `test.jsonl`, `packaging_manifest.json`, the
exact config, input quality artifacts, and code revision together. Rebuild into
a new directory after changing input rows, split policy, system message,
response style, or transforms.

---

## Changing Packaging

Start with the narrowest owner:

| Intended change | Primary owner | Coupled review |
|---|---|---|
| Accepted input names or quality-manifest checks | `resolve_input_paths` and `run_packaging` | Quality output contract and provenance |
| System/user/assistant row shape | `build_packaged_record` | Training reader, row validation, metadata handoff |
| Reasoning/direct style | `assign_response_styles`, `format_content_by_reasoning_style`, config | Style counts and all split examples |
| Target-model tags or annotations | `apply_model_specific_transforms`, `validate_packaged_records`, versioned config | Fine-tuning template and stop behavior |
| Packaged row schema | Add/update a row contract in `dataset_packaging/` | Existing package compatibility and training preflight |
| Grouping key | `split_records_by_source_doc` and manifest | Leakage policy and overlap enforcement |
| Split targets or assignment heuristic | `split_targets`, `choose_split`, config validation | Count tolerance and deterministic fixtures |
| Overlap enforcement | `split_source_doc_overlap` and `run_packaging` | Manifest and nonzero exit behavior |
| Manifest fields | `dataset_packaging/schemas.py`, `build_packaging_manifest` | Fine-tuning input identity |
| Output lifecycle | `prepare_output_dir`, `write_packaged_splits` | Partial-write recovery and immutable package policy |

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
