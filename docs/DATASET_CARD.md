# Dataset Card

## Dataset Summary

- Name: Shepherd DFIR Dataset
- Version: pre-packaging reduced subset snapshot
- Date: 2026-07-01
- Owner: current project owner
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

Current source counts below use the Phase 2 raw corpus and the latest Phase 4 reduced-subset quality snapshot at `data/quality/gemini_subset_1/`.

| Source | Raw Docs | Filtered Pairs | License/Attribution Notes | Included |
|---|---:|---:|---|---|
| `mitre_attack` | 697 | 137 | Preserve MITRE ATT&CK attribution | Yes |
| `sigma_rules` | 3,111 | 143 | Preserve Sigma rule attribution | Yes |
| `atomic_red_team` | 1,811 | 112 | Preserve Atomic Red Team attribution | Yes |
| `cisa_advisories` | 3,849 | 138 | Public CISA advisory content | Yes |
| `volatility3_docs` | 194 | 46 | Preserve Volatility documentation attribution | Yes |
| `mitre_atlas` | 262 | 42 | Preserve MITRE ATLAS attribution | Yes |
| `cisa_kev` | 270 | 17 | Public CISA KEV catalog content | Yes |
| `kape_files` | 811 | 92 | Preserve KAPE Files attribution | Yes |
| `hayabusa_rules` | 4,839 | 112 | Preserve Hayabusa rule attribution | Yes |
| `lolbas_gtfobins` | 720 | 51 | Preserve LOLBAS/GTFOBins attribution | Yes |
| `forensic_artifacts` | 731 | 67 | Preserve ForensicArtifacts attribution | Yes |
| `velociraptor_artifacts` | 437 | 81 | Preserve Velociraptor documentation attribution | Yes |
| `hijacklibs` | 590 | 43 | Preserve HijackLibs attribution | Yes |
| `loldrivers` | 656 | 5 | Preserve LOLDrivers attribution | Yes |
| `ossem_data_dicts` | 699 | 43 | Preserve OSSEM data dictionary attribution | Yes |
| `cybersec_skills` | 670 | 5 | Preserve upstream skills attribution | Yes |

## Generation Methodology

- Raw source collection process: 16 collectors normalize public DFIR/cybersecurity sources into `RawDocument` JSONL under `data/raw/`.
- Teacher model: Gemini 2.5 Flash through the Google GenAI SDK with structured JSON output.
- Prompt structure: base prompt, task-category instructions, source/content-type instructions, deterministic taxonomy refs, and prompt-time source compaction.
- Pilot procedure: smoke and pilot gates are still required before treating full generation as final.
- Current synthesis procedure: budget-aware `subset` mode is the main shortened-timeline path; the latest quality snapshot checked 6,023 Phase 3 candidate pairs.
- Rejection gates: Phase 3 catches invalid JSON/schema/reasoning/provenance/grounding/indicator failures before Phase 4.
- Quality filtering: Phase 4 independently checks schema, provenance, taxonomy, ATT&CK/ATLAS IDs, tool names, reasoning links, grounding, invented indicators, rubric score, near-duplicates, balance, tactic coverage, taxonomy coverage, and manual spot-check sampling.

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
| `artifact_analysis` | 417 | 36.8% |
| `ttp_identification` | 229 | 20.2% |
| `triage_and_hunting` | 166 | 14.6% |
| `detection_engineering` | 240 | 21.2% |
| `report_generation` | 82 | 7.2% |

### Difficulty Distribution

| Difficulty | Records | Percent |
|---|---:|---:|
| `junior` | 430 | 37.9% |
| `mid` | 547 | 48.2% |
| `senior` | 157 | 13.8% |

### Taxonomy Coverage

See `docs/COVERAGE_MAP.md`. The latest Phase 4 snapshot covers 26 of 57 configured taxonomy IDs. Strongest filtered coverage is detection coverage (`S3`), threat-intel operations (`TI1`), Windows execution/disk/event-log categories (`W1`, `W4`, `W8`), living-off-the-land (`AF3`), and C2/beaconing (`N4`). Missing IDs remain concentrated in cloud, SaaS/file-storage, legal/chain-of-custody, container, OT/IoT, malware-analysis, and some network categories.

## Quality Controls

- Deterministic validators: schema, source provenance, category/difficulty, taxonomy refs, ATT&CK/ATLAS IDs against local reference caches, tool names, reasoning links, grounding/tag consistency, final-answer consistency, and invented concrete indicators.
- Heuristic scoring: weighted factual accuracy, reasoning quality, operational relevance, specificity, and completeness with accept/review thresholds from `configs/quality.yaml`.
- Near-duplicate checks: current Phase 4 snapshot found zero pairs above the 0.8 Jaccard threshold.
- Manual spot-check: `data/quality/gemini_subset_1/manual_spot_check_sample.jsonl` contains 100 pending rows.
- Known rejected/review patterns: invented indicators, broad unsupported claims, mapping inconsistencies, low operational value, invalid ATT&CK/ATLAS IDs, and reasoning-link failures.

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
.venv/bin/python -m scripts.synthesize run --mode subset --output-dir data/synthesized/gemini_subset_1
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/gemini_subset_1/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/gemini_subset_1 \
  --log-level INFO
```

Phase 5 packaging is not implemented yet; packaged train/validation/test splits are intentionally blank above.
