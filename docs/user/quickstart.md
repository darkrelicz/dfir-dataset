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
```

The module commands used throughout the existing docs are equivalent:

```bash
python -m scripts.collect_all
python -m scripts.synthesize --help
python -m scripts.quality_filter
python -m scripts.package_dataset
```

## Current Training Inputs

The current package is already built locally:

```bash
data/packaged/gemini_subset_1/train.jsonl
data/packaged/gemini_subset_1/validation.jsonl
data/packaged/gemini_subset_1/test.jsonl
```

Use those three files for the Phase 6 baseline evaluation and Unsloth LoRA SFT
run unless the project state docs are updated.

## Guides Site

The guides site is self-contained under `guides/`.

```bash
cd guides
npm install
npm run serve
```

A static build writes HTML to `guides/_site/`:

```bash
cd guides
npm run build
```

PlantUML diagrams require Java. Non-sequence diagrams also require Graphviz.
The GitHub Actions workflow installs both for Pages deployment.

## Important Secrets

`GEMINI_API_KEY` is required only when running Phase 3 generation against the
Gemini API. The runner reads it from `.env` or the process environment. Do not
commit real API keys.

## Immediate Next Step

Run baseline evaluation before fine-tuning. Then train LoRA SFT on
GLM-4.7-Flash with the local package under `data/packaged/gemini_subset_1/`.
