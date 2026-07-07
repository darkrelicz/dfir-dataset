# Synthesis

Phase 3 converts validated raw documents into candidate instruction-response
pairs.

<puml src="../diagrams/synthesis-sequence.puml" alt="Phase 3 synthesis sequence" width="1000" />

## CLI

`scripts.synthesize` exposes:

```bash
python -m scripts.synthesize validate-raw
python -m scripts.synthesize render-prompts
python -m scripts.synthesize run
```

The CLI stays thin. Execution lives in `synthesizers.runner`.

## Document Selection

`synthesizers.planner.select_documents` loads raw documents and selects by mode:

| Mode | Selection |
|---|---|
| `pilot` | `sample_pilot_documents` using `pilot_targets`. |
| `subset` | `sample_subset_documents` using `subset_targets`. |
| `full` | All docs sorted by source and doc ID. |

Pilot and subset sampling stratify by source, content type, and word-count
richness buckets.

## Category Assignment

`assign_categories` reads target weights from
`configs/task_categories.yaml`. It balances planned pair counts against target
distribution while respecting each source profile's allowed categories.

Assignment order prioritizes documents with fewer allowed categories, then uses
stable hash jitter from `utils.text.stable_index`.

## Difficulty Assignment

`assign_difficulties` uses configured difficulty targets and a stable hash of
`doc_id`. Current labels are `junior`, `mid`, and `senior`.

## PromptBuilder

`synthesizers.prompt_builder.PromptBuilder` builds one `PromptRecord` per raw
document.

Prompt rendering combines:

1. `synthesizers/prompts/base.md`;
2. category template from `configs/task_categories.yaml`;
3. source-type template from `configs/source_profiles.yaml`;
4. optional content-type template from `content_type_profiles`;
5. compacted source document content;
6. deterministic taxonomy refs.

`PromptBuilder.pairs_for_doc` starts with
`configs/synthesis.yaml:generation.pairs_per_document`, then caps pairs for:

* documents under 250 words;
* thin source profiles;
* thin content-type profiles;
* content-type `max_pairs`.

The current config requests one pair per document for every source.

## Deterministic Taxonomy Refs

`PromptBuilder` suggests one to three taxonomy IDs using:

* MITRE tactics found in source Markdown;
* content type;
* source;
* task category;
* platform hints;
* fallback `S1`.

These refs are stored on `PromptRecord` and rendered into the prompt as JSON.
Phase 3 validation later overwrites generated `taxonomy_refs` from the prompt
record.

## Prompt Compaction

Prompt-time compactors live under `synthesizers/prompts/compactors/`.

`compact_document_for_prompt`:

1. loads a source-specific compactor named `<source>_compactor.py` when present;
2. calls `compact_for_prompt(doc, content)`;
3. applies shared head/tail truncation if the compactor did not opt out.

Velociraptor opts out of shared truncation because VQL bodies are the main
training signal.

Current source-specific compactors:

| Source | Compactor Focus |
|---|---|
| `cisa_advisories` | Preserve advisory metadata, important sections, capped CVEs, high-CVSS blocks. |
| `cisa_kev` | Preserve vendor/product/CVE summary and selected KEV details. |
| `mitre_attack` | Preserve IDs, tactics, platforms, description, procedures, mitigations, detections. |
| `cybersec_skills` | Preserve workflow metadata, mappings, tools, steps, scenarios, and compacted code blocks. |
| `velociraptor_artifacts` | Preserve query bodies, parameters, reports, and structured defaults. |
| `loldrivers` | Preserve commands, hashes, detections, CVEs, and selected samples. |
| `hijacklibs` | Preserve DLL paths, hijack conditions, hashes, and privilege/elevation flags. |

## Gemini Client

`synthesizers.clients.gemini.GeminiClient`:

* requires `GEMINI_API_KEY` by default;
* supports `generate_content` / `models.generate_content`;
* uses `response_mime_type="application/json"`;
* supplies a sanitized schema for `list[InstructionPair]`;
* maps `temperature` and `thinking_budget`;
* converts parsed SDK responses back to JSON text for the same validation path.

The client strips unsupported `additionalProperties` keys from the response
schema but keeps strict local Pydantic validation.

## Run State

`synthesizers.run_state` owns:

* run ID generation;
* prompt hashing;
* prompt row serialization;
* run metadata fields;
* `--skip-present` terminal prompt detection.

Only accepted/rejected rows with matching `prompt_hash` and model are considered
complete for skip-present behavior.

## Generated-Output Validation

`synthesizers.validators.validate_generated_pairs` checks:

* valid JSON array output;
* expected pair count;
* strict `InstructionPair` schema;
* reasoning block structure;
* final answer presence;
* taxonomy refs;
* ATT&CK/ATLAS ID shape;
* grounding tag consistency;
* invented concrete indicators.

It normalizes category, difficulty, source, source doc ID, and taxonomy refs
from the prompt record before schema validation.

## Retry And Circuit Breaker

API retries use exponential backoff with jitter from `configs/synthesis.yaml`.

Validation failures can trigger a regeneration prompt that lists validator
errors and hard output requirements.

For `subset` and `full` modes, the rejection circuit breaker can stop a run
after the minimum attempted prompt count when rejection rate exceeds the
configured threshold. It is inactive in pilot mode.
