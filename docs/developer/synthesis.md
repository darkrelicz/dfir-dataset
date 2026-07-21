<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Synthesis</h1>

Phase 3 converts validated raw documents into candidate instruction-response
pairs.

<puml src="../diagrams/synthesis-sequence.puml" alt="Phase 3 synthesis sequence" width="1000" />

# CLI

`scripts.synthesize` exposes:

```bash
python -m scripts.synthesize validate-raw
python -m scripts.synthesize render-prompts
python -m scripts.synthesize run
```

The CLI stays thin. Execution lives in `synthesizers.runner`.

# Document Selection

`synthesizers.planner.select_documents` loads raw documents and selects by mode:

| Mode | Selection |
|---|---|
| `pilot` | `sample_pilot_documents` using `pilot_targets`. |
| `subset` | `sample_subset_documents` using `subset_targets`. |
| `full` | All docs sorted by source and doc ID. |

Pilot and subset sampling stratify by source, content type, and word-count
richness buckets.

`--limit` is applied after the per-source samples have been concatenated in
`pilot_targets` or `subset_targets` order. It is not a second stratified sample.
For example, the current `--mode pilot --limit 10` plan contains ten
`mitre_attack` documents because that source is first in `pilot_targets`. Do not
use a small global limit when the review requires cross-source representation;
instead, run the complete pilot plan or change the configured per-source targets.

# Category Assignment

`assign_categories` reads target weights from
`configs/task_categories.yaml`. It balances planned pair counts against target
distribution while respecting each source profile's allowed categories.

Assignment order prioritizes documents with fewer allowed categories, then uses
stable hash jitter from `utils.text.stable_index`.

# Difficulty Assignment

`assign_difficulties` uses configured difficulty targets and a stable hash of
`doc_id`. Current labels are `junior`, `mid`, and `senior`.

# PromptBuilder

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

# Deterministic Taxonomy Refs

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

# Prompt Compaction

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

# Gemini Client

`synthesizers.clients.gemini.GeminiClient`:

* requires `GEMINI_API_KEY` by default;
* supports `generate_content` / `models.generate_content`;
* uses `response_mime_type="application/json"`;
* supplies a sanitized schema for `list[InstructionPair]`;
* maps `temperature` and `thinking_budget`;
* converts parsed SDK responses back to JSON text for the same validation path.

The client strips unsupported `additionalProperties` keys from the response
schema but keeps strict local Pydantic validation.

# Run State

`synthesizers.run_state` owns:

* run ID generation;
* prompt hashing;
* prompt row serialization;
* run metadata fields;
* `--skip-present` terminal prompt detection.

Only accepted/rejected rows with matching `prompt_hash` and model are considered
complete for skip-present behavior.

Both kinds of rejection are terminal for `--skip-present`, including
`status="api_error"`. The command therefore does not retry a transient API error
on a later invocation when its prompt hash and model still match. Completion is
detected from the presence of a matching row; it does not verify that all
`pairs_requested` rows were appended before an interruption.

# Output Directory And Resume Semantics

Synthesis output files do not all have the same replacement behavior:

| Output | Behavior on invocation |
|---|---|
| `prompts.jsonl` | Replaced with the current complete prompt plan. |
| `accepted.jsonl` | Existing file retained; new accepted pairs appended. |
| `rejected.jsonl` | Existing file retained; new terminal rejections appended. |
| `raw_outputs.jsonl` | Existing file retained; every new model response appended. |
| `generation_manifest.json` | Replaced after the generation loop finishes. |

`--skip-present` supports continuing an unchanged plan in the same directory,
but the resulting JSONL files can contain multiple run IDs. The replacement
manifest describes only the latest invocation and uses notes for its attempted,
accepted, rejected, and skipped counts.

Do not reuse an output directory after changing prompts, profiles, task policy,
source documents, or models. A changed prompt hash causes regeneration, but old
accepted/rejected rows are not removed; downstream quality would otherwise read
both old and new accepted rows. Running again without `--skip-present` also
appends duplicate work.

Writes are not transactional. Accepted, rejected, and raw-output rows survive an
interruption because they are appended incrementally, but an interrupted final
line may be incomplete and no current manifest is written until the loop ends.
Inspect and repair JSONL integrity before continuing an interrupted directory.

# Generated-Output Validation

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

# Retry And Circuit Breaker

API retries use exponential backoff with jitter from `configs/synthesis.yaml`.

Validation failures can trigger a regeneration prompt that lists validator
errors and hard output requirements.

For `subset` and `full` modes, the rejection circuit breaker can stop a run
after the minimum attempted prompt count when rejection rate exceeds the
configured threshold. It is inactive in pilot mode.

A circuit-breaker stop returns exit code 2 and writes the final manifest with a
free-form `Stopped early` note. Ordinary API or validation rejections do not by
themselves make the command fail.

# Configuration Boundaries

The `output` mapping in `configs/synthesis.yaml` is currently descriptive and is
not read by the runner. `--output-dir` controls the destination, while JSONL and
manifest writing are unconditional.

Source profiles and pilot/subset targets are loaded from the repository's fixed
`configs/source_profiles.yaml` path at Python import time; there is no CLI option
for an alternate source-profile file. Taxonomy suggestion mappings for sources,
content types, categories, tactics, and platforms are Python constants in
`synthesizers.prompt_builder`, rather than YAML policy.

Prompt-policy preflight checks that referenced templates exist and that source
categories are known. Prompt rendering uses `Template.safe_substitute`, so an
unknown or misspelled placeholder remains literally in the prompt instead of
failing preflight. Dry-run prompt review must check for unresolved `$...`
placeholders.

# Generation Manifest Scope

`GenerationManifest` records the run ID, mode, model, creation time, selected
document and prompt counts, output directory, synthesis-config path, and notes.
It does not fingerprint the raw corpus, task config, quality config, source
profiles, prompt templates, compactors, or effective model settings. It also has
no structured completion status or structured attempted/accepted/rejected/
skipped counters. Preserve the invoked configuration and code revision
separately when exact run reproduction is required.
