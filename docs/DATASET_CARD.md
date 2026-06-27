# Dataset Card

## Dataset Summary

- Name: Shepherd DFIR Dataset
- Version:
- Date:
- Owner:
- Intended use: Fine-tuning Shepherd's DFIR reasoning layer
- Hosting: Local DGX Sparks filesystem unless changed
- Canonical reasoning format: `<reasoning>`

## Dataset Purpose

Describe what the dataset is designed to teach the model:

- DFIR artifact interpretation
- TTP identification
- Triage and hunting
- Detection engineering
- Evidence-cited report generation

## Dataset Sources

| Source | Raw Docs | Filtered Pairs | License/Attribution Notes | Included |
|---|---:|---:|---|---|
| `mitre_attack` |  |  |  |  |
| `sigma_rules` |  |  |  |  |
| `atomic_red_team` |  |  |  |  |
| `cisa_advisories` |  |  |  |  |
| `volatility3_docs` |  |  |  |  |
| `mitre_atlas` |  |  |  |  |
| `cisa_kev` |  |  |  |  |
| `kape_files` |  |  |  |  |
| `hayabusa_rules` |  |  |  |  |
| `lolbas_gtfobins` |  |  |  |  |
| `forensic_artifacts` |  |  |  |  |
| `velociraptor_artifacts` |  |  |  |  |
| `hijacklibs` |  |  |  |  |
| `loldrivers` |  |  |  |  |
| `ossem_data_dicts` |  |  |  |  |
| `cybersec_skills` |  |  |  |  |

## Generation Methodology

Summarize:

- Raw source collection process:
- Teacher model:
- Prompt structure:
- Pilot procedure:
- Full synthesis procedure:
- Rejection gates:
- Quality filtering:

## Dataset Structure

Canonical packaged record:

```json
{
  "id": "dfir-000001",
  "conversations": [
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
    "reasoning_format": "canonical_reasoning_v1",
    "quality_score": 0.0
  }
}
```

## Splits

Splits must be by `source_doc_id` to avoid leakage.

| Split | Records | Percent | Path |
|---|---:|---:|---|
| Train |  |  |  |
| Validation |  |  |  |
| Test |  |  |  |

## Distribution

### Task Category Distribution

| Category | Records | Percent |
|---|---:|---:|
| `artifact_analysis` |  |  |
| `ttp_identification` |  |  |
| `triage_and_hunting` |  |  |
| `detection_engineering` |  |  |
| `report_generation` |  |  |

### Difficulty Distribution

| Difficulty | Records | Percent |
|---|---:|---:|
| `junior` |  |  |
| `mid` |  |  |
| `senior` |  |  |

### Taxonomy Coverage

Link to `docs/COVERAGE_MAP.md` and summarize the most important strengths/gaps.

## Quality Controls

- Deterministic validators:
- Heuristic scoring:
- Near-duplicate checks:
- Manual spot-check:
- Known rejected patterns:

## Intended Use

This dataset is intended for:

- Local supervised fine-tuning experiments for Shepherd
- Evaluation of DFIR task behavior before and after fine-tuning
- Reproducible dataset regeneration and extension

This dataset is not intended for:

- Autonomous incident response without human review
- Attribution claims without external corroboration
- Training on private incident data unless a separate approval and sanitization process exists

## Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Public-source bias | May overrepresent documented techniques and common Windows artifacts | Expand sources later |
| Synthetic responses | Teacher-model errors may survive filtering | Pilot, validators, manual review |
| Thin source records | Sparse records can cause generic examples | Pair caps and review |
| Limited cloud/SaaS coverage | Shepherd may underperform on those investigations | Add cloud/SaaS sources |
| Limited AI/LLM incident coverage | ATLAS foundation may be shallow | Add OWASP LLM and incident sources |

## Ethical And Safety Notes

- The dataset is for defensive DFIR and incident response training.
- Do not include private customer data without approval and sanitization.
- Preserve source provenance for auditability.
- Do not train the model to provide offensive procedural guidance beyond defensive analysis needs.

## Reproduction

```bash
.venv/bin/python -m scripts.collect_all
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
.venv/bin/python -m scripts.synthesize run --mode full --output-dir data/synthesized/full
```

Add Phase 4 and Phase 5 commands once implemented.
