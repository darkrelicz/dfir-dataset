<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# Quick Start

## Python Environment

The repository is a Python 3.11+ data pipeline packaged with setuptools.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The `pyproject.toml` entrypoints are:

```bash
dfir-collect
dfir-synthesize
dfir-quality
dfir-package
dfir-evaluate
dfir-compare-evals
dfir-train-lora
```

The module commands used throughout the existing docs are equivalent:

```bash
python -m scripts.collect_all
python -m scripts.synthesize --help
python -m scripts.quality_filter
python -m scripts.package_dataset
python -m scripts.run_evaluation --help
python -m scripts.compare_evaluations --help
python -m scripts.finetune --help
```

## Current Training Inputs

The current package is already built locally:

```bash
data/packaged/gemini_subset_1/train.jsonl
data/packaged/gemini_subset_1/validation.jsonl
data/packaged/gemini_subset_1/test.jsonl
```

Use those three files for the Phase 6 baseline evaluation and Unsloth LoRA SFT
run unless the project state docs are updated. Phase 6 uses the local judge
configured under `scoring.judge`; calibrate and freeze it before comparing the
base and tuned models.

## Guides Site

The guides site is self-contained under `docs/`.

```bash
cd docs
npm install
npm run serve
```

A static build writes HTML to `docs/_site/`:

```bash
cd docs
npm run build
```

PlantUML diagrams require Java. Non-sequence diagrams also require Graphviz.
The GitHub Actions workflow installs both for Pages deployment.

## Important Secrets

`GEMINI_API_KEY` is required only when running Phase 3 generation against the
Gemini API. The runner reads it from `.env` or the process environment. Do not
commit real API keys.

## Immediate Next Step

Finalize and review the benchmark files under `evaluation/benchmark/`, then run baseline
evaluation before fine-tuning. After the baseline manifest exists, train LoRA
SFT on GLM-4.7-Flash with the local package under
`data/packaged/gemini_subset_1/`.
