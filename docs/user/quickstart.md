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

These files produced the completed `train-20260714T025314Z` Unsloth LoRA SFT
run. Use the package manifest and training manifest to verify provenance before
retraining. Phase 6 uses only the local judge configured under
`scoring.judge`; calibrate and freeze it before producing comparison
scorecards.

Current generated artifacts include:

```text
data/finetune/glm47_flash_lora_dfir_subset1/training_manifest.json
data/finetune/glm47_flash_subset1/lora_adapter/
data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf
data/evaluation/glm47-flash-base/
```

The existing base scorecard is complete but uncalibrated. Its `0.7588` score is
useful for pipeline smoke testing only, not as the final comparison baseline.

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

Finalize manual review of the 68 cases under `evaluation/benchmark/`, calibrate
the local judge on a separate human-scored dataset, and replace
`scoring.judge.calibration_id: uncalibrated` with the frozen calibration release
ID. Then run new complete base and tuned evaluations with identical benchmark
and judge fingerprints. Do not use the existing exploratory base run for the
final model-improvement claim.
