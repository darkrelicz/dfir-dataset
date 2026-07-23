<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Developer Guide</h1>

The developer guide follows the dataset lifecycle. Each stage page owns its
implementation, configuration, contracts, extension workflow, validation
ladder, and operational caveats. Commands for running an unchanged pipeline
belong in the [User Guide](../user/index.md).

<box type="info" seamless header="Recommended reading order">

Start with [Pipeline Foundations](pipeline-foundations.md), then read only the
stage you plan to change. Read [Fine-tuning](finetuning.md) and
[Evaluation](evaluation.md) together when making a promotion decision.

</box>

# Local Setup

Prerequisites are Python 3.11 or later, Git, Java and Graphviz for diagrams, a
Gemini API key for model-backed synthesis, and a CUDA environment for local
fine-tuning.

```bash
git clone https://github.com/darkrelicz/dfir-dataset.git
cd dfir-dataset
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
python -m scripts.collect_all --list
```

Preview the documentation with:

```bash
cd docs
npm install
npm run serve
```

# Lifecycle Map

| Stage | Responsibility | Guide |
|---|---|---|
| Foundations | Architecture, shared contracts, configuration ownership, change discipline, and project memory | [Pipeline Foundations](pipeline-foundations.md) |
| Collection | Normalize and preserve public DFIR source material | [Collectors](collectors.md) |
| Synthesis | Plan prompts and generate grounded candidate pairs | [Synthesis](synthesis.md) |
| Quality filtering | Validate, score, deduplicate, audit, and select package-eligible rows | [Quality Filtering](quality-filtering.md) |
| Packaging | Build model-specific views and leakage-safe splits | [Packaging](packaging.md) |
| Fine-tuning | Train, export, and test a candidate adapter | [Fine-tuning](finetuning.md) |
| Evaluation | Design held-out cases, calibrate the judge, compare models, and decide promotion | [Evaluation](evaluation.md) |

The [DFIR Artifact Taxonomy](../reference/taxonomy.md) remains a standalone
domain reference because every data stage depends on it.

# Core Rules

1. Preserve complete source evidence during collection; compact only prompt
   views.
2. Carry stable provenance through every downstream record.
3. Treat synthesis output as candidates; package only rows marked `filtered`.
4. Split packages by `source_doc_id` to prevent source leakage.
5. Use a fresh output directory after changing inputs, prompts, policy, schema,
   or model settings unless the owning stage explicitly documents safe resume
   behavior.
6. Preserve manifests, exact configuration, logs, code revision, and environment
   information together for reproducibility.
7. Do not promote a model without an enforcing direct-adapter behavior gate and
   complete, calibrated, compatible evaluation evidence.

# Choosing Where To Make A Change

| Change | Canonical location |
|---|---|
| Add or modify a source | [Collectors](collectors.md#adding-or-changing-a-source) |
| Change prompt behavior or add a compactor | [Synthesis](synthesis.md#changing-synthesis) |
| Add a validator or change quality policy | [Quality Filtering](quality-filtering.md#changing-quality-policy) |
| Add an export format or response style | [Packaging](packaging.md#changing-packaging) |
| Change LoRA, trainer, or export settings | [Fine-tuning](finetuning.md#changing-the-training-recipe) |
| Add benchmark cases or change comparison policy | [Evaluation](evaluation.md#changing-evaluation) |
| Change a shared schema or phase boundary | [Pipeline Foundations](pipeline-foundations.md#changing-a-contract-or-boundary) |

# Documentation Ownership

| Information | Owner |
|---|---|
| Stable implementation and maintenance guidance | `docs/developer/` |
| User-facing commands and source summaries | `docs/user/` |
| Stable domain definitions | `docs/reference/` |
| Current results and candidate status | [Current State](../current-state/index.md) |
| Superseded run history | [Revisions](../current-state/revisions.md) |
| Product intent and durable decisions | `project_state/PROJECT_BRIEF.md` and `project_state/DECISIONS.md` |
| Pending and deferred work | `project_state/TODO.md` |
| Run-specific facts | Generated manifests under `data/` |

Do not copy live row counts, candidate status, or future-work lists into a stage
guide. Link to their owner instead.
