<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Developer Guide</h1>

This guide explains where the DFIR Dataset pipeline is designed, implemented,
and maintained. It is the starting point; focused pages own the implementation
details. Commands for operating an unchanged pipeline belong in the
[User Guide](../user/index.md).

<box type="info" seamless header="How to use this guide">

Read **Setting up**, **Design**, and **Implementation** when joining the project.
For a specific change, use [Common development
workflows](#common-development-workflows) to find the canonical guide.

</box>

---

## **Setting up and getting started**

### Prerequisites

- Python 3.11 or later
- Git
- Java and Graphviz for documentation diagrams
- A Gemini API key only for model-backed synthesis
- A CUDA-capable environment only for local fine-tuning

### Local setup

```bash
git clone https://github.com/darkrelicz/dfir-dataset.git
cd dfir-dataset
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
python -m scripts.collect_all --list
```

Preview the documentation with `cd docs && npm install && npm run serve`.
Training-specific dependencies and checks are documented in [Training and
Release](training-and-release.md#environment-record).

---

## **Design**

The repository is a re-runnable dataset factory, not a serving application.
Versioned YAML and Markdown own durable policy; Python packages implement each
pipeline phase.

<puml src="../diagrams/pipeline-component.puml" alt="Components of the DFIR dataset pipeline" width="1000" />

| Component | Responsibility |
|---|---|
| `collectors/` | Normalize public DFIR sources into `RawDocument` rows. |
| `synthesizers/` | Plan prompts, call the teacher model, and validate candidates. |
| `validation/` | Provide reusable grounding, taxonomy, indicator, mapping, and reasoning checks. |
| `quality/` | Apply row gates, scoring, deduplication, balance checks, and audits. |
| `dataset_packaging/` | Build model-specific training views and leakage-safe splits. |
| `evaluation/` | Run held-out cases, judge predictions, and compare scorecards. |
| `scripts/` | Expose thin command-line entry points for these packages. |

Core rules:

1. Preserve full source evidence during collection; compact only prompt views.
2. Carry stable provenance through every downstream record.
3. Separate reusable validation logic from phase policy.
4. Split packages by `source_doc_id` to avoid source leakage.
5. Use fresh output directories after prompt, policy, schema, or model changes.
6. Preserve manifests, configuration, and logs together for reproducibility.

See [Architecture](architecture.md) for component boundaries and architectural
decisions, [Data Contracts](data-contracts.md) for record fields, and
[Diagrams](diagrams.md) for all UML views.

---

## **Implementation**

The phases are ordered by dependency. Earlier changes can invalidate assumptions
in every later phase.

| Phase | Primary implementation | Canonical guide |
|---|---|---|
| 1. Taxonomy and task design | `docs/reference/`, task and quality config | [Taxonomy](../reference/taxonomy.md) · [Coverage Map](coverage-map.md) |
| 2. Collection | `collectors/`, `configs/collection.yaml` | [Collectors](collectors.md) |
| 3. Synthesis | `synthesizers/`, synthesis and source-profile config | [Synthesis](synthesis.md) · [Prompt Guide](prompt-guide.md) |
| 4. Quality | `quality/`, `validation/`, quality config | [Validation and Quality](validation-quality.md) · [Quality Rubric](quality-rubric.md) |
| 5. Packaging | `dataset_packaging/`, packaging config | [Packaging](packaging.md) |
| 6. Evaluation and training | `evaluation/`, training scripts and config | [Benchmark Design](benchmark-design.md) · [Training and Release](training-and-release.md) |

Use the [Phase Maintenance Guide](phase-maintenance.md) when changing a phase.
It owns the file maps, update order, validation ladders, and phase-specific
failure modes. Use [Configuration](configuration.md) to identify which policy
file owns a setting before adding a hard-coded branch.

---

## **Common development workflows**

| Change | Start here | Supporting reference |
|---|---|---|
| Add or modify a source | [Adding Sources](adding-sources.md) | [Collectors](collectors.md) · [Source Internals](source-guide.md) |
| Change prompt behavior | [Prompt Guide](prompt-guide.md) | [Synthesis](synthesis.md) |
| Add a compactor, validator, scoring rule, or export format | [Extension Points](extension-points.md) | The affected phase guide |
| Change a schema | [Data Contracts](data-contracts.md) | [Phase Maintenance](phase-maintenance.md) |
| Change quality policy or review practice | [Quality Rubric](quality-rubric.md) | [Validation and Quality](validation-quality.md) |
| Add or revise benchmark cases | [Benchmark Design](benchmark-design.md) | [Training and Release](training-and-release.md) |
| Transfer unfinished work | [Developer Handover](handover.md) | [Project State Memory](project-state-memory.md) |

Each workflow has one canonical procedure. Other pages link to that procedure
instead of restating its steps.

---

## **Documentation, testing, configuration, and operations**

### Validation principle

Start with the cheapest deterministic check, then progress through artifact
validation, dry runs, smoke runs, and pilots. Inspect warnings, rejected rows,
distributions, and manifests as well as process exit status. Some runners return
success even when rows are rejected or a reporting gate fails.

The exact checks belong to the affected section of the [Phase Maintenance
Guide](phase-maintenance.md). Rebuild this site after changing a command,
contract, configuration field, phase boundary, or output:

```bash
cd docs
npm run build
```

### Documentation ownership

| Information | Canonical location |
|---|---|
| Stable implementation guidance | `docs/developer/` |
| User-facing commands and source summaries | `docs/user/` |
| Current run status and results | [Current State](../current-state/index.md) |
| Durable project intent and decisions | `project_state/PROJECT_BRIEF.md` and `project_state/DECISIONS.md` |
| Active work | `project_state/TODO.md` |
| Future enhancements | [Suggested Improvements](suggested-improvements.md) |

Do not copy current run counts into implementation pages. Link to Current State
so status has one owner.

---

## **Appendix: Reference map**

These pages are references, not a second reading sequence.

| Need | Reference |
|---|---|
| Exact record and manifest fields | [Data Contracts](data-contracts.md) |
| Source behavior and caching | [Source Internals](source-guide.md) |
| Configuration fields and limitations | [Configuration](configuration.md) |
| Quality issue codes and manual review | [Quality Rubric](quality-rubric.md) |
| Artifact category definitions | [DFIR Artifact Taxonomy](../reference/taxonomy.md) |
| Operational documentation rules | [Project State Memory](project-state-memory.md) |
| Every UML view | [Diagrams](diagrams.md) |
| Prioritized future work | [Suggested Improvements](suggested-improvements.md) |
