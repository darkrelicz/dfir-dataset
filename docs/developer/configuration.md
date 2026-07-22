<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Configuration</h1>

The project keeps policy in YAML where practical. Python should implement
mechanics and validation, not hide durable project policy in hard-coded branches.

# `configs/collection.yaml`

Defines all Phase 2 sources:

* upstream URLs;
* clone/cache paths;
* output directories;
* collector-specific filters such as minimum rule level or minimum body tokens.

`scripts.collect_all` maps source keys from this file to concrete collector
classes.

# `configs/source_profiles.yaml`

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

# `configs/synthesis.yaml`

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
* an `output` mapping retained as descriptive configuration.

The Gemini client maps supported controls into `models.generate_content`.

The runner does not currently read `output.format`, `output.dir`, or
`output.manifest`. The CLI's `--output-dir` owns the destination, and JSONL plus
manifest output is always enabled.

`configs/source_profiles.yaml` is loaded from a fixed repository path at import
time. `--synthesis-config` and `--task-config` do not select an alternate source
profile file. Taxonomy suggestions based on source, content type, category,
tactic, and platform are currently hard-coded in
`synthesizers.prompt_builder`; these are exceptions to the config-first policy
described above.

# `configs/task_categories.yaml`

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

# `configs/quality.yaml`

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

Phase 4 loads this YAML as an untyped mapping and does not apply a configuration
schema or startup range validation. Keep scoring weights non-negative, Jaccard
and balance values within their intended 0-1 ranges, reasoning limits coherent,
and sample sizes non-negative. Invalid-but-numeric values may silently weaken a
gate or distort score-based ranking rather than fail at startup.

# Packaging Configurations

Packaging configs define:

* split fractions, seed, and group key;
* system message;
* response-style policy.

The packager writes local JSONL splits and a packaging manifest. It has no
hosting or publishing behavior. `configs/packaging.yaml` retains the historical
scalar response-style shape and is not compatible with the current runner; do
not use it without migrating `response_style.filtered` to reasoning/direct
fractions.

`configs/packaging_glm47_v3.yaml` is the active model-specific view. Its
`response_style.filtered` mapping requires reasoning/direct fractions that sum
to 1.0; the current policy is 0.75/0.25. It enables GLM reasoning-tag conversion
and grounding-annotation removal while preserving canonical inputs.
Packaged-record validation always runs and derives its tag checks from the
configured model transformations.

# `configs/evaluation.yaml`

Defines the Phase 6 target-generation and local-judge clients:

* `benchmark.cases_path` selects a benchmark JSONL file or directory;
* `output.base_dir` owns generated evaluation runs;
* `prompt` defines the target system message and context wrapper;
* `generation.mode` is exactly `openai_compatible` for target generation or
  `prediction_file` for saved-answer replay;
* `generation.model`, sampling fields, token limit, and timeout configure the
  evaluated model;
* `generation.structured_outputs.enabled` globally enables or suppresses the
  JSON instructions declared by each case's `target_output.format`;
* `scoring.judge` configures the separately served judge model, JSON response
  format, validation retries, inference overrides, and calibration ID.

Both `base_url` values must be API roots such as
`http://127.0.0.1:8080/v1`. `OpenAICompatibleClient` appends
`/chat/completions`. The evaluator has no statistical mode and no evaluator
selector; a valid `scoring.judge` mapping is required.

Server-specific request fields belong only under `request_overrides`; the
former `extra_body` alias is not supported. The implementation reserves only
`messages` and `model`; an override can replace standard payload fields such as
temperature, token limit, or response format. Avoid duplicating those fields,
because the override wins while the dedicated setting remains misleading.

The complete judge mapping contributes to the scorecard fingerprint. Once a
judge has been calibrated, freeze its model, quantization, chat template,
sampling fields, request overrides, and `calibration_id` for both base and tuned
runs.

Only the complete judge mapping is fingerprinted. Target prompt and generation
settings, endpoint, overrides, prediction-file identity, and the model actually
reported by the server are not included in comparison compatibility metadata.
Freeze and archive the full target configuration and logs separately.

Evaluation YAML has no typed top-level configuration model or range validation.
Values are converted when clients are built; review timeouts, token limits,
sampling values, and retry counts before running.

# Fine-Tuning Configurations

`configs/finetune_glm47flash.yaml` and
`configs/finetune_glm47flash_v2.yaml` preserve historical runs. V3, v4, and v5
have completed manifests and exports; v4 differs from v3 only in its isolated
output paths. V5 uses zero dropout plus attention and MLP targets. V6 is the
newest staged experiment definition and has no completed training manifest. The
repository does not provide an active-config pointer, and the CLI default still selects the
historical unversioned v1 config. Always pass the intended version explicitly.

Every fine-tuning config defines:

* packaged train, validation, test, and manifest paths;
* the GLM-4.7-Flash base model and sequence length;
* LoRA target modules, rank, alpha, checkpointing, and seed;
* `finetune` trainer arguments and checkpoint policy;
* the adapter and GGUF destinations plus GGUF quantization settings.

V3/v4 use `data/packaged/glm47_v3/`, rank 16, alpha 32, dropout 0.05,
attention-only targets, learning rate `2e-5`, and one epoch. V5 retains that
package, rank, alpha, and learning rate but uses dropout 0 and adds `gate_proj`,
`up_proj`, and `down_proj`. V6 raises rank/alpha to 32/64, maximum sequence
length to 8,192, and learning rate to `2e-4`, and also targets `out_proj`; it is
staged only. The runner is intentionally specific to 4-bit LoRA SFT: it always
uses response-only loss masking and saves both the adapter and GGUF artifact.
GGUF generation cannot be disabled; every configuration must provide
`gguf_dir` and `gguf_quantization`. The raw config mappings are copied into the
training manifest, but forced runtime choices such as `load_in_4bit=True` and
`trust_remote_code=True` are not added when absent from the config, and numeric
casts are not reflected as a normalized effective configuration.

There is no typed fine-tuning configuration schema or range validation. Values
are cast at their use sites; notably, `bf16` uses Python truth conversion, so a
quoted string such as `"false"` evaluates as enabled. Keep booleans as YAML
booleans and validate numeric ranges before committing an expensive run.

# Prompt Templates

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
