# Architecture

This repository is a Python dataset pipeline. It is not a product frontend, API
server, or model-serving runtime.

## Runtime

| Area | Current Implementation |
|---|---|
| Language | Python 3.11+ |
| Packaging | `pyproject.toml` with setuptools |
| CLI entrypoints | `dfir-collect`, `dfir-synthesize`, `dfir-quality`, `dfir-package` |
| Core libraries | `pydantic`, `pyyaml`, `jsonlines`, `google-genai`, `requests`, `gitpython`, `rich`, `tqdm`, `mitreattack-python` |
| Tests | `pytest` is configured, but no `tests/` tree exists yet |

## Component View

<puml src="../diagrams/pipeline-component.puml" alt="Component diagram for the dataset factory" width="1000" />

## End-To-End Sequence

<puml src="../diagrams/end-to-end-sequence.puml" alt="End-to-end sequence diagram" width="1000" />

## Main Packages

| Path | Responsibility |
|---|---|
| `collectors/` | Phase 2 source-specific collection into `RawDocument` JSONL. |
| `scripts/collect_all.py` | CLI orchestrator for configured collectors. |
| `synthesizers/` | Phase 3 planning, prompt rendering, Gemini generation, run state, and generated-output validation. |
| `synthesizers/prompts/` | Base, category, source-type, content-type, and compactor prompt assets. |
| `validation/` | Pure reusable validation primitives shared by Phase 3 and Phase 4. |
| `quality/` | Phase 4 row gates, scoring, references, dataset audits, and output writing. |
| `dataset_packaging/` | Phase 5 local JSONL packaging for Unsloth/GLM SFT. |
| `scripts/` | Thin CLI entrypoints that dispatch to package runners. |
| `utils/` | Low-level helpers for IO, text normalization, Markdown frontmatter, and git URLs. |
| `configs/` | Machine-readable policy and pipeline settings. |
| `docs/` | Durable project memory and operating guides. |
| `guides/` | This MarkBind successor guide site. |

## Pipeline Phases

### Phase 2 Collection

`scripts.collect_all` loads `configs/collection.yaml`, maps source keys to
collector classes, and runs selected collectors. Each collector writes one JSONL
file under `data/raw/<source>/` and returns a `CollectionManifest` entry. The
script combines these entries into `data/raw/collection_manifest.json`.

### Phase 3 Synthesis

`scripts.synthesize` exposes three subcommands:

* `validate-raw`
* `render-prompts`
* `run`

`synthesizers.planner` selects documents and assigns category/difficulty.
`PromptBuilder` renders prompt records from config and templates. Prompt-time
compactors produce shorter source views without mutating raw documents.

`GeminiClient` uses the Google GenAI SDK `models.generate_content` path with
structured JSON response settings. The runner writes prompts, raw outputs,
accepted candidate rows, rejected rows, and a generation manifest.

### Shared Validation

`validation/` holds pure primitives:

* reasoning block parsing and link validation;
* grounding field and `[GENERAL KNOWLEDGE]` tag consistency;
* concrete indicator extraction and invention checks;
* ATT&CK/ATLAS ID regexes;
* taxonomy ref extraction from config.

Phase 3 and Phase 4 call these primitives through separate policy wrappers.

### Phase 4 Quality

`quality.runner` loads configs, raw docs, and references; validates every Phase 3
candidate row; scores candidates; applies dataset gates; writes filtered,
review, rejected, spot-check, and manifest outputs.

Phase 4 deliberately does not call Phase 3's generated-output validators.

### Phase 5 Packaging

`dataset_packaging.runner` reads Phase 4 filtered and review rows, builds
chat-style message records, splits by `source_doc_id`, writes train/validation/test
JSONL, and creates a packaging manifest. The package name is
`dataset_packaging/` to avoid shadowing Python's third-party `packaging` module.

## Current Generated State

The current reduced-subset package is:

```text
data/packaged/gemini_subset_1/
```

It contains 5,517 records split into 4,414 train, 552 validation, and 551 test
rows. The split has no `source_doc_id` overlap.

## Important Architectural Decisions

* Raw documents remain complete. Prompt-cost reduction happens only during
  Phase 3 prompt rendering.
* Config files own policy; Python modules own mechanics.
* Canonical responses use `<reasoning>`, not `<think>`.
* Gemini 2.5 Flash is the primary teacher model for canonical generation.
* Alternate teacher models must run as separate labeled jobs.
* Phase 3 `accepted.jsonl` is candidate data, not final training data.
* Phase 5 currently packages filtered plus review rows by explicit time-boxed
  decision.
