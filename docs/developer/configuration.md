# Configuration

The project keeps policy in YAML where practical. Python should implement
mechanics and validation, not hide durable project policy in hard-coded branches.

## `configs/collection.yaml`

Defines all Phase 2 sources:

* upstream URLs;
* clone/cache paths;
* output directories;
* collector-specific filters such as minimum rule level or minimum body tokens.

`scripts.collect_all` maps source keys from this file to concrete collector
classes.

## `configs/source_profiles.yaml`

Defines Phase 3 source and content-type behavior.

Source profiles specify:

* `source_type`;
* source-type prompt template;
* allowed task categories;
* `thin_source` when applicable.

Content-type profiles can specify:

* a content-type prompt template;
* `max_pairs`;
* `thin_source`.

The same file also contains default `pilot_targets` and `subset_targets`.

## `configs/synthesis.yaml`

Defines teacher-model and generation behavior:

* API mode: `generate_content`;
* API key env var: `GEMINI_API_KEY`;
* primary model: `gemini-2.5-flash`;
* no automatic fallback model;
* `thinking_budget`;
* one pair per document for every configured source;
* retry/backoff settings;
* validation retry count;
* `max_source_chars`;
* output settings.

The Gemini client maps supported controls into `models.generate_content`.

## `configs/task_categories.yaml`

Defines the five task categories:

* `artifact_analysis`
* `ttp_identification`
* `triage_and_hunting`
* `detection_engineering`
* `report_generation`

Each category has:

* a description;
* category prompt template;
* quality signals;
* Shepherd alignment metadata;
* absorbed taxonomy/domain hints.

The file also defines category and difficulty distribution targets used by
planning and quality audits.

## `configs/quality.yaml`

Defines Phase 4 quality policy:

* all valid taxonomy IDs and coverage levels;
* heuristic scoring weights;
* generic-answer penalty terms;
* operational verbs;
* reasoning min/max steps;
* deduplication method and Jaccard threshold;
* source-balance and distribution tolerance;
* manual spot-check sample size and seed;
* tool allowlist.

Quality validators and dataset gates read from this file. They do not own the
canonical taxonomy list.

## `configs/packaging.yaml`

Defines Phase 5 packaging:

* quality input directory and filenames;
* split fractions, seed, and group key;
* output record format;
* system message;
* response-style policy;
* output paths;
* hosting policy.

The current packaging policy is local-only and does not publish to Hugging Face.

## Prompt Templates

Prompt assets live under `synthesizers/prompts/`:

| Path | Role |
|---|---|
| `base.md` | Global system and output contract. |
| `categories/*.md` | Task behavior instructions. |
| `source_types/*.md` | Broad source-shape instructions. |
| `content_types/*.md` | Exact content-type overrides. |
| `compactors/*.py` | Prompt-time source view generation. |

`synthesizers.prompt_policy.load_prompt_policy` preflights template references
before prompt rendering.
