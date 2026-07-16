<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Dataset Card Template</h1>

# Purpose

Use this template when documenting a packaged training dataset. Phase 6
evaluation cases are held out separately under `evaluation/benchmark/` and must
not be drawn from these packaged splits.

Run-specific dataset cards should be generated or filled from:

- `data/raw/collection_manifest.json`
- `data/synthesized/<run>/generation_manifest.json`
- `data/quality/<run>/quality_manifest.json`
- `data/packaged/<run>/packaging_manifest.json`
- `docs/developer/coverage-map.md`

# Dataset Summary

| Field | Value |
|---|---|
| Name | Shepherd DFIR Dataset |
| Version |  |
| Date |  |
| Owner |  |
| Intended use | Fine-tuning Shepherd's DFIR reasoning layer |
| Hosting | Local DGX Sparks filesystem unless changed |
| Canonical source reasoning format | `<reasoning>` |
| Packaged response styles | Reasoning for filtered rows; direct answer for accepted review rows |
| Source synthesis run |  |
| Quality run |  |
| Packaging run |  |

# Dataset Purpose

Describe what the packaged dataset is designed to teach the model:

- DFIR artifact interpretation
- TTP identification
- Triage and hunting
- Detection engineering
- Evidence-cited report generation

# Dataset Sources

Fill this table from the raw collection manifest and quality manifest.

| Source | Raw Docs | Package-Eligible Pairs | License/Attribution Notes | Included |
|---|---:|---:|---|---|
|  |  |  |  |  |

# Generation Methodology

Record the exact generation setup for the packaged run:

- Raw source collection process:
- Teacher model:
- Prompt structure:
- Synthesis mode:
- Synthesis output path:
- Rejection gates:
- Quality filtering path:
- Manual review performed:

# Dataset Structure

Canonical packaged record:

```json
{
  "id": "dfir-000001",
  "messages": [
    {
      "role": "system",
      "content": "You are Shepherd, a DFIR AI assistant..."
    },
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "<reasoning>...</reasoning>\n\n..."
    }
  ],
  "metadata": {
    "category": "artifact_analysis",
    "difficulty": "mid",
    "mitre_techniques": [],
    "atlas_techniques": [],
    "tools_referenced": [],
    "taxonomy_refs": [],
    "source_doc_id": "",
    "source": "",
    "quality_status": "filtered",
    "quality_issues": [],
    "quality_score": {},
    "reasoning_style": "reasoning",
    "response_transform": "none"
  }
}
```

# Splits

Splits must be by `source_doc_id` to avoid leakage.

| Split | Records | Percent | Path |
|---|---:|---:|---|
| Train |  |  |  |
| Validation |  |  |  |
| Test |  |  |  |

# Distribution

## Task Category Distribution

| Category | Records | Percent |
|---|---:|---:|
| `artifact_analysis` |  |  |
| `ttp_identification` |  |  |
| `triage_and_hunting` |  |  |
| `detection_engineering` |  |  |
| `report_generation` |  |  |

## Difficulty Distribution

| Difficulty | Records | Percent |
|---|---:|---:|
| `junior` |  |  |
| `mid` |  |  |
| `senior` |  |  |

## Taxonomy Coverage

Summarize covered, thin, and absent taxonomy IDs using `configs/quality.yaml` and the quality manifest.

# Quality Controls

Record which controls were applied:

- Deterministic validators:
- Heuristic scoring:
- Near-duplicate checks:
- Manual spot-check:
- Review queue adjudication:
- Known rejected/review patterns:

# Intended Use

This dataset is intended for:

- Local supervised fine-tuning experiments for Shepherd
- Designing separate held-out evaluations without copying packaged examples
- Reproducible dataset regeneration and extension

This dataset is not intended for:

- Autonomous incident response without human review
- Attribution claims without external corroboration
- Training on private incident data unless a separate approval and sanitization process exists

# Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Public-source bias | May overrepresent documented techniques and common Windows artifacts | Expand sources later |
| Synthetic responses | Teacher-model errors may survive filtering | Validators, review queue, manual review |
| Thin source records | Sparse records can cause generic examples | Pair caps and review |
| Limited cloud/SaaS coverage | Shepherd may underperform on those investigations | Add cloud/SaaS sources |
| Limited AI/LLM incident coverage | ATLAS foundation may be shallow | Add OWASP LLM and incident sources |

# Ethical And Safety Notes

- The dataset is for defensive DFIR and incident response training.
- Do not include private customer data without approval and sanitization.
- Preserve source provenance for auditability.
- Do not train the model to provide offensive procedural guidance beyond defensive analysis needs.

# Reproduction

Record exact commands used for the packaged run:

```bash
.venv/bin/python -m scripts.collect_all
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
.venv/bin/python -m scripts.synthesize run --mode <mode> --output-dir data/synthesized/<run>
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/<run>/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/<run> \
  --log-level INFO
.venv/bin/python -m scripts.package_dataset \
  --config configs/packaging.yaml \
  --quality-dir data/quality/<run> \
  --output-dir data/packaged/<run>
```
