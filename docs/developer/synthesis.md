<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Synthesis</h1>

Synthesis converts validated `RawDocument` rows into grounded candidate
`InstructionPair` rows. It is a two-part pipeline: deterministic prompt planning
followed by model-backed generation and local acceptance. This page describes
the architecture, planning and prompt implementation, model client, generation
loop, validation, state, resume behavior, and extension workflow.

## Architecture

<puml src="../diagrams/synthesis-macro.puml" alt="Macro view of candidate synthesis" width="900" />

Synthesis preserves a strict boundary between deterministic inputs and
probabilistic output:

- the planner owns document selection, category, difficulty, pair count,
  taxonomy suggestions, prompt content, and prompt identity;
- the teacher model proposes instructions, responses, confidence, technique
  IDs, tools, and grounding declarations;
- local validation restores deterministic provenance and either accepts the
  complete requested list or rejects the prompt.

Accepted synthesis rows are still candidates. Only quality rows marked
`filtered` may become training data.

### Planning Flow

<puml src="../diagrams/synthesis-planning-detail.puml" alt="Detailed prompt planning sequence" width="1000" />

Planning is deterministic for the same raw corpus, configuration, profile file,
prompt assets, compactor code, and repository version:

1. validate and load `data/raw/*/*.jsonl`;
2. select pilot, subset, or full documents;
3. assign one allowed task category and a difficulty to each document;
4. determine the requested pair count;
5. derive a prompt-only compacted evidence view;
6. combine base, category, source-type, and optional content-type templates;
7. attach deterministic taxonomy references;
8. construct one `PromptRecord` and prompt hash per selected document.

### Generation Flow

<puml src="../diagrams/synthesis-generation-detail.puml" alt="Detailed candidate generation and validation sequence" width="700" />

Generation processes prompt records sequentially. For each non-skipped prompt,
the runner calls the model with API retries, appends the raw response, validates
the complete JSON array, optionally asks the model to regenerate with validator
feedback, then appends accepted pairs or one terminal rejection. A subset/full
rejection-rate circuit breaker can stop the loop early.

There is no concurrent request scheduler, provider plugin discovery, database,
or transactional job queue. `synthesizers.runner` owns orchestration and writes
JSONL incrementally.

### Component Ownership

| Component | Responsibility |
|---|---|
| `scripts/synthesize.py` | Thin CLI and exit-code handoff |
| `synthesizers/io.py` | Discover and load raw JSONL documents |
| `synthesizers/sampler.py` | Source/content/richness-aware pilot and subset selection |
| `synthesizers/planner.py` | Selection orchestration and category/difficulty assignment |
| `synthesizers/source_profiles.py` | Load fixed source/content-type profiles and sample targets |
| `synthesizers/prompt_policy.py` | Validate category, difficulty, and template policy |
| `synthesizers/prompt_builder.py` | Pair caps, compaction, taxonomy suggestions, and prompt assembly |
| `synthesizers/prompts/` | Layered prompt assets and source-specific compactors |
| `synthesizers/clients/` | Provider-neutral protocol and Gemini SDK adapter |
| `synthesizers/validators.py` | Raw-corpus and generated-pair acceptance |
| `synthesizers/run_state.py` | Prompt hashes, run fields, and skip-present discovery |
| `synthesizers/runner.py` | Dry-run rendering, generation, retries, persistence, manifests, and circuit breaker |
| `validation/` | Reusable reasoning, grounding, indicator, mapping, and taxonomy primitives |

### Contracts

| Contract | Defined in | Role |
|---|---|---|
| `RawDocument` | `collectors/schemas.py` | Complete source input |
| `PromptRecord` | `synthesizers/schemas.py` | Deterministic plan for one source document/model call |
| `InstructionPair` | `synthesizers/schemas.py` | Strict model-neutral candidate; extra fields forbidden |
| `ModelResponse` / `ModelClient` | `synthesizers/clients/base.py` | Provider boundary used by retry/orchestration code |
| `GeneratedPairValidation` | `synthesizers/schemas.py` | Accepted parsed pairs plus structured validation issues |
| `GenerationManifest` | `synthesizers/schemas.py` | Latest invocation identity and high-level plan metadata |

---

## CLI And Entrypoints

`scripts.synthesize` exposes:

```bash
python -m scripts.synthesize validate-raw
python -m scripts.synthesize render-prompts
python -m scripts.synthesize run
```

| Command | Implementation | External model calls | Primary output |
|---|---|---|---|
| `validate-raw` | `runner.print_validation` → `validators.validate_raw_corpus` | No | Console report and exit code |
| `render-prompts` | `runner.write_prompt_render` | No | `prompts.jsonl`, optional prompt Markdown, dry-run manifest |
| `run` | `runner.run_generation` | Yes | Prompt plan, raw responses, accepted/rejected rows, manifest |

The CLI accepts alternate raw, synthesis-config, task-config, quality-config,
and output paths where relevant. Source profiles remain fixed at
`configs/source_profiles.yaml`.

---

## Planning Implementation

### Raw Corpus Loading And Validation

`synthesizers.io.raw_jsonl_paths` discovers only
`<raw_dir>/*/*.jsonl`, sorted by path. `load_raw_documents` loads every row into
memory as `RawDocument`.

`validate_raw_corpus` checks that files and rows exist, every line parses as a
`RawDocument`, and `doc_id` values are unique across all sources. It reports
source counts. It does not check evidence completeness, `word_count`
correctness, source-profile coverage, or prompt suitability. `run` refuses to
start when this validation reports an issue; `render-prompts` currently builds
the plan without first calling this explicit corpus validation.

### Document Selection

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

### Category Assignment

`assign_categories` reads target weights from
`configs/task_categories.yaml`. It balances planned pair counts against target
distribution while respecting each source profile's allowed categories.

Assignment order prioritizes documents with fewer allowed categories, then uses
stable hash jitter from `utils.text.stable_index`.

### Difficulty Assignment

`assign_difficulties` uses configured difficulty targets and a stable hash of
`doc_id`. Current labels are `junior`, `mid`, and `senior`.

---

## Prompt Implementation

### `PromptBuilder`

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

The prompt ID is
`prompt-<source_doc_id>-<category>-<difficulty>`. `run_state.prompt_hash`
hashes only the final rendered prompt text. Model name, generation settings,
quality taxonomy config, and source bytes are not independently included in the
hash.

#### Canonical Response And Grounding

Every synthesized response uses a model-neutral reasoning contract:

```text
<reasoning>
E1: Source-grounded evidence.
A1 [uses E1]: Analysis of the evidence.
C1 [uses E1,A1] Confidence: medium. Conclusion.
CV1 [applies_to C1]: Caveat or corroboration need.
</reasoning>

Final practitioner-ready answer.
```

Use `grounding: source_only` only when every substantive claim is visible in
the prompt source. It must not contain `[GENERAL KNOWLEDGE]`. Use
`source_plus_general` when any claim relies on outside knowledge, and mark every
such claim with `[GENERAL KNOWLEDGE]`.

Do not change canonical data to model-native tags such as `<think>`. That
conversion belongs in [Packaging](packaging.md).

### Deterministic Taxonomy Refs

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

### Prompt Compaction

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

---

## Generation Implementation

### Client Boundary And `GeminiClient`

`synthesizers.clients.base.ModelClient` is a structural protocol with one
`generate(PromptRecord) -> ModelResponse` method. The runner's API retry logic
depends on this protocol, but `run_generation` currently imports and constructs
`GeminiClient` directly rather than selecting a provider from configuration.

`synthesizers.clients.gemini.GeminiClient`:

* requires `GEMINI_API_KEY` by default;
* accepts `generate_content` and `models.generate_content` as configuration
  labels; both use `client.models.generate_content`;
* uses `response_mime_type="application/json"`;
* supplies a sanitized schema for `list[InstructionPair]`;
* maps `temperature` and `thinking_budget`;
* converts parsed SDK responses back to JSON text for the same validation path.

The client strips unsupported `additionalProperties` keys from the response
schema but keeps strict local Pydantic validation.

### Runner Loop

`synthesizers.runner.run_generation`:

1. loads `.env` values only when the key is not already present in the process
   environment;
2. validates circuit-breaker arguments and the complete raw corpus;
3. loads synthesis, task, and quality configs;
4. verifies the configured API-key environment variable;
5. builds the complete prompt plan and replaces `prompts.jsonl`;
6. resolves matching terminal prompts when `--skip-present` is enabled;
7. constructs `GeminiClient`, retry settings, and valid taxonomy IDs;
8. processes remaining prompt records one at a time;
9. appends every successful model response before local validation;
10. appends one row per accepted pair or one terminal rejection per prompt;
11. checks the subset/full circuit breaker after each attempted prompt;
12. writes the final manifest only after leaving the loop.

An API retry repeats the same prompt after exponential backoff. A validation
retry creates a new temporary prompt ID with validator feedback, but persisted
raw/accepted/rejected rows retain the original prompt's run fields so resume
logic still treats it as one planned prompt.

### Run State

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

### Output Directory And Resume Semantics

<puml src="../diagrams/synthesis-resume-detail.puml" alt="Detailed synthesis output replacement and append behavior" width="900" />

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

### Generated-Output Validation

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

### Retry And Circuit Breaker

API retries use exponential backoff with jitter from `configs/synthesis.yaml`.

Validation failures can trigger a regeneration prompt that lists validator
errors and hard output requirements.

For `subset` and `full` modes, the rejection circuit breaker can stop a run
after the minimum attempted prompt count when rejection rate reaches the
configured threshold. It is inactive in pilot mode.

A circuit-breaker stop returns exit code 2 and writes the final manifest with a
free-form `Stopped early` note. Ordinary API or validation rejections do not by
themselves make the command fail.

---

## Configuration And Reproducibility

### Configuration Boundaries

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

### Generation Manifest Scope

`GenerationManifest` records the run ID, mode, model, creation time, selected
document and prompt counts, output directory, synthesis-config path, and notes.
It does not fingerprint the raw corpus, task config, quality config, source
profiles, prompt templates, compactors, or effective model settings. It also has
no structured completion status or structured attempted/accepted/rejected/
skipped counters. Preserve the invoked configuration and code revision
separately when exact run reproduction is required.

---

## Changing Synthesis

Start with the narrowest owner:

| Intended change | Primary owner | Coupled review |
|---|---|---|
| Pilot/subset source counts | `configs/source_profiles.yaml` | `synthesizers/sampler.py`, representative plan |
| Category/difficulty targets | `configs/task_categories.yaml` | `synthesizers/planner.py`, quality distribution gates |
| Per-source pair count or prompt-size limit | `configs/synthesis.yaml` | Thin-source/content caps and prompt review |
| Global/category/source/content instructions | Narrowest template under `synthesizers/prompts/` | `PromptBuilder`, validators, rendered prompt |
| Source evidence compaction | `synthesizers/prompts/compactors/` | Grounding coverage and `max_source_chars` |
| Taxonomy suggestions | `synthesizers/prompt_builder.py` | Taxonomy reference and quality config |
| Provider or structured-output behavior | `synthesizers/clients/` and construction in `runner.py` | Retry behavior, response metadata, local validation |
| API/validation retry or circuit breaker | `configs/synthesis.yaml`, `synthesizers/runner.py`, CLI flags | Resume and rejection semantics |
| Phase 3 acceptance | `synthesizers/validators.py` and reusable `validation/` primitives | Regeneration feedback and Phase 4 policy |
| Prompt identity or resume behavior | `synthesizers/run_state.py` | Existing output compatibility and manifest scope |
| File lifecycle or manifest fields | `synthesizers/runner.py`, `synthesizers/schemas.py` | Interrupted runs, downstream quality input |

Prompt policy is layered:

1. `synthesizers/prompts/base.md` defines global behavior and output shape.
2. `synthesizers/prompts/categories/*.md` defines task behavior.
3. `synthesizers/prompts/source_types/*.md` defines broad source behavior.
4. `synthesizers/prompts/content_types/*.md` handles exceptional content types.
5. `synthesizers/prompts/compactors/` derives a smaller evidence view.

Add a more specific template only when the broader layer cannot express the
behavior. `configs/source_profiles.yaml` owns template selection, allowed
categories, thin-source flags, content-type caps, and pilot/subset targets.
`configs/task_categories.yaml` owns task definitions and distribution targets.
`configs/synthesis.yaml` owns the Gemini model, generation controls, retries,
validation retry count, pair counts, prompt-size limit, and circuit breaker.

To add a compactor, create
`synthesizers/prompts/compactors/<source>_compactor.py` and expose:

```python
def compact_for_prompt(doc: RawDocument, content: str) -> str:
    ...
```

Compactors remove repeated or low-priority blocks without mutating raw data.
Set `compact_for_prompt.skip_source_truncation = True` only when shared
head/tail truncation would destroy the main signal. Velociraptor uses this
because VQL bodies and structured parameter defaults are essential evidence.

Reusable parsing and grounding checks belong in `validation/`; Phase 3
acceptance policy belongs in `synthesizers/validators.py`.

### Prompt Review

Before an API run, confirm that:

- the requested pair count fits the visible evidence;
- the category and difficulty fit the document;
- compacted content retains evidence needed for the task;
- taxonomy references are a JSON list of valid IDs;
- thin sources are capped;
- the prompt bans invented indicators, paths, users, hosts, and event records;
- the rendered prompt contains no unresolved `$placeholder`;
- the expected schema still matches `InstructionPair`.

### Validation Ladder

1. Validate the complete raw corpus.
2. Render prompts without using API budget.
3. Inspect representative rich, thin, and heavily compacted sources.
4. Run one representative model-backed prompt into a fresh smoke directory.
5. Inspect `accepted.jsonl`, `rejected.jsonl`, `raw_outputs.jsonl`, and the
   manifest.
6. Run the complete pilot and review every accepted and rejected output.
7. Record rejection and manual-quality patterns.
8. Run a subset or full corpus only after the pilot meets the chosen gate.

Use a new output directory after changing a prompt, compactor, profile, task
policy, raw input, or model. Keep alternate teacher comparisons in separately
labelled directories. `--skip-present` treats API and validation errors as
terminal; use a separate retry directory when transient failures should be
attempted again.

### Frequent Failure Patterns

| Symptom | Likely owner |
|---|---|
| Invented paths, hashes, or IOCs | Pair cap, thin-source policy, or grounding prompt |
| Generic answers | Compactor, `max_source_chars`, or sparse evidence |
| Rephrased duplicates | Source/content-type pair cap |
| Broken reasoning links | Format example or validator feedback |
| Unsupported ATT&CK/ATLAS IDs | Mapping instructions and candidate-ID policy |
| Grounding field/tag mismatch | Base prompt and regeneration feedback |
| JSON wrapped in fences or wrong schema | Structured-output setup and local validation |
| Repeated Gemini `503` responses | Retry policy and a safe `--skip-present` continuation |

---

## Output Handover

| File | Meaning |
|---|---|
| `prompts.jsonl` | Current complete prompt plan; replaced each invocation |
| `raw_outputs.jsonl` | Append-only teacher responses |
| `accepted.jsonl` | Candidates that passed Phase 3 checks; not training data |
| `rejected.jsonl` | Terminal API or validation failures |
| `generation_manifest.json` | Latest completed invocation summary |

Preserve all five outputs with the exact configs, prompt assets, compactor code,
raw input identity, teacher model settings, and logs when reproducibility
matters.
