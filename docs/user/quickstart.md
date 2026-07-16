<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Quick Start</h1>

# Python Environment

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

# Current Training Inputs

The active GLM-specific package is already built locally:

```bash
data/packaged/glm47_dfir_v2/train.jsonl
data/packaged/glm47_dfir_v2/validation.jsonl
data/packaged/glm47_dfir_v2/test.jsonl
```

These files are prepared for v2 retraining. The earlier
`train-20260714T025314Z` artifact is retained for diagnosis but rejected because
it looped and did not emit EOS. Use the package manifest and training manifest
to verify provenance. Phase 6 uses only the local judge configured under
`scoring.judge`; calibrate and freeze it before producing comparison
scorecards.

Historical diagnostic artifacts include:

```text
data/finetune/glm47_flash_lora_dfir_subset1/training_manifest.json
data/finetune/glm47_flash_subset1/lora_adapter/
data/finetune/glm47_flash_subset1/gguf_q4_k_m_gguf/finetuned-GLM-4.7-Flash.Q4_K_M.gguf
data/evaluation/glm47-flash-base/
```

The existing base scorecard is complete but uncalibrated. Its `0.7588` score is
useful for pipeline smoke testing only, not as the final comparison baseline.

# Guides Site

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

# Important Secrets

`GEMINI_API_KEY` is required only when running Phase 3 generation against the
Gemini API. The runner reads it from `.env` or the process environment. Do not
commit real API keys.

# Immediate Next Step

Run v2 training with `configs/finetune_glm47flash_v2.yaml`, then require EOS from
a bounded direct-adapter smoke test. After that gate, finalize benchmark review,
calibrate the judge, and run new complete base and v2 tuned evaluations. Do not
use the rejected v1 artifact or exploratory base score for a final claim.
