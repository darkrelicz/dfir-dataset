<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

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

## `configs/evaluation.yaml`

Defines the Phase 6 target-generation and local-judge clients:

* `benchmark.cases_path` selects a benchmark JSONL file or directory;
* `output.base_dir` owns generated evaluation runs;
* `prompt` defines the target system message and context wrapper;
* `generation.mode` selects `openai_compatible` generation or prediction-file
  replay;
* `generation.model`, sampling fields, token limit, timeout, and
  `structured_outputs` configure the evaluated model;
* `scoring.judge` configures the separately served judge model, JSON response
  format, validation retries, inference overrides, and calibration ID.

Both `base_url` values must be API roots such as
`http://127.0.0.1:8080/v1`. `OpenAICompatibleClient` appends
`/chat/completions`. The evaluator has no statistical mode and no evaluator
selector; a valid `scoring.judge` mapping is required.

The complete judge mapping contributes to the scorecard fingerprint. Once a
judge has been calibrated, freeze its model, quantization, chat template,
sampling fields, request overrides, and `calibration_id` for both base and tuned
runs.

## `configs/finetune_glm47flash.yaml`

Defines the local Unsloth LoRA SFT run:

* packaged train, validation, test, and manifest paths;
* GLM-4.7-Flash loading and sequence settings;
* LoRA target modules, rank, alpha, checkpointing, and seed;
* `finetune` trainer arguments, response-only masking, and checkpoint policy;
* adapter, merged-model, and GGUF export choices.

The current run loads the base model in 4-bit, trains one epoch with BF16
trainer precision, and exports an adapter plus Q4_K_M GGUF. The current training
runner incorrectly serializes `config.get("training", {})` into its manifest
even though trainer settings live under `finetune`; fix that mismatch before
using a future manifest as a complete reproducibility record.

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
