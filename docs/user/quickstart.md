<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Quick Start</h1>

# Install

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Python 3.11 or newer is required. Confirm that the scripts are available:

```bash
python -m scripts.collect_all --list
python -m scripts.synthesize --help
python -m scripts.quality_filter --help
python -m scripts.package_dataset --help
python -m scripts.finetune --help
python -m scripts.run_evaluation --help
python -m scripts.compare_evaluations --help
```

# Safe First Run

These checks do not call Gemini or start training:

```bash
python -m scripts.collect_all --dry-run
python -m scripts.synthesize validate-raw --raw-dir data/raw
python -m scripts.synthesize render-prompts \
  --mode pilot \
  --limit 10 \
  --raw-dir data/raw \
  --output-dir data/synthesized/quickstart_preview
```

Inspect `data/synthesized/quickstart_preview/prompts.jsonl`. If the source data
is not present locally, run `python -m scripts.collect_all` first; collection
downloads public data and updates local Git caches.

# Current Dataset

The active, already packaged v3 training view is:

```text
data/packaged/glm47_v3/train.jsonl
data/packaged/glm47_v3/validation.jsonl
data/packaged/glm47_v3/test.jsonl
data/packaged/glm47_v3/packaging_manifest.json
```

Do not use the earlier v1 adapter or GGUF: both failed the EOS termination gate.
See [Current Project State](../current-state/index.md) before training or
evaluation.

# Run A Stage

The shortest useful commands are:

```bash
# Phase 2: all sources
python -m scripts.collect_all

# Phase 3: validate only
python -m scripts.synthesize validate-raw --raw-dir data/raw

# Phase 4: current candidates
python -m scripts.quality_filter

# Phase 5: active GLM view
python -m scripts.package_dataset \
  --config configs/packaging_glm47_v3.yaml \
  --quality-dir data/quality/gemini_subset_1 \
  --output-dir data/packaged/glm47_v3

# Phase 6: after fixing the lora_dropout cast (DGX only)
python -m scripts.finetune --config configs/finetune_glm47flash_v3.yaml
```

Before training, change the `lora_dropout` conversion in `scripts/finetune.py`
from `int` to `float`; otherwise v3's configured 0.05 is applied as zero.

The [Running The Pipeline](running-the-pipeline.md) page explains inputs,
outputs, API requirements, resumption behavior, and release gates for every
command.

# Gemini Secret

Only Phase 3 generation needs an external API key. Put
`GEMINI_API_KEY=<value>` in the ignored `.env` file or process environment. Do
not commit it. Prompt rendering and every Phase 2/4/5 operation run without it.

# Documentation Site

The docs use MarkBind:

```bash
cd docs
npm install
npm run serve
```

Run `npm run build` for a static build in `docs/_site/`. PlantUML rendering
requires Java; non-sequence UML diagrams also require Graphviz.
