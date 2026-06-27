# Coverage Map

## Purpose

Track what the current dataset covers, what it only partially covers, and what should be added by a successor. This document should be updated after Phase 2 collection, Phase 3 synthesis, and Phase 4 filtering because coverage can change at each stage.

## Coverage Summary

| Area | Coverage | Evidence | Gaps | Successor Priority |
|---|---|---|---|---|
| Windows endpoint forensics |  |  |  |  |
| Linux endpoint forensics |  |  |  |  |
| macOS endpoint forensics |  |  |  |  |
| Memory forensics |  |  |  |  |
| Network forensics |  |  |  |  |
| Cloud forensics |  |  |  |  |
| Identity/SaaS forensics |  |  |  |  |
| AI/LLM incident response |  |  |  |  |
| Detection engineering |  |  |  |  |
| Incident reporting |  |  |  |  |

Coverage labels:

- `strong`: enough examples for training and evaluation
- `moderate`: usable, but likely imbalanced or shallow
- `thin`: present, but should not be trusted as a strength
- `absent`: no meaningful coverage

## Source Coverage

| Source | Raw Docs | Synthesized Pairs | Filtered Pairs | Main Strength | Main Weakness |
|---|---:|---:|---:|---|---|
| `mitre_attack` |  |  |  | ATT&CK technique grounding |  |
| `sigma_rules` |  |  |  | Detection logic |  |
| `atomic_red_team` |  |  |  | Procedure-level TTP examples |  |
| `cisa_advisories` |  |  |  | Vulnerability/advisory triage |  |
| `volatility3_docs` |  |  |  | Memory tool usage |  |
| `mitre_atlas` |  |  |  | AI/ML threat taxonomy |  |
| `cisa_kev` |  |  |  | Exploited vulnerability context |  |
| `kape_files` |  |  |  | Artifact path definitions | Thin source |
| `hayabusa_rules` |  |  |  | Windows event detections | Sigma overlap |
| `lolbas_gtfobins` |  |  |  | Living-off-the-land abuse |  |
| `forensic_artifacts` |  |  |  | Artifact definitions | Thin source |
| `velociraptor_artifacts` |  |  |  | VQL/artifact collection |  |
| `hijacklibs` |  |  |  | DLL hijacking references | Very thin source |
| `loldrivers` |  |  |  | Driver abuse references | Very thin source |
| `ossem_data_dicts` |  |  |  | Event field definitions | Thin source |
| `cybersec_skills` |  |  |  | Practitioner workflows |  |

## Task Category Coverage

| Category | Target Share | Synthesized Share | Filtered Share | Notes |
|---|---:|---:|---:|---|
| `artifact_analysis` | 30% |  |  |  |
| `ttp_identification` | 25% |  |  |  |
| `triage_and_hunting` | 18% |  |  |  |
| `detection_engineering` | 14% |  |  |  |
| `report_generation` | 13% |  |  |  |

## Difficulty Coverage

| Difficulty | Target Share | Synthesized Share | Filtered Share | Notes |
|---|---:|---:|---:|---|
| `junior` | 30% |  |  |  |
| `mid` | 50% |  |  |  |
| `senior` | 20% |  |  |  |

## Taxonomy Heatmap

Use `docs/TAXONOMY.md` and `configs/quality.yaml` as the source of truth for taxonomy IDs.

| Taxonomy ID | Name | Raw Source Support | Synthesized Pairs | Filtered Pairs | Coverage Label | Notes |
|---|---|---|---:|---:|---|---|
|  |  |  |  |  |  |  |

## ATT&CK And ATLAS Coverage

| Framework | Coverage Metric | Result | Notes |
|---|---|---:|---|
| ATT&CK tactics covered |  |  |  |
| ATT&CK techniques covered |  |  |  |
| ATLAS tactics covered |  |  |  |
| ATLAS techniques covered |  |  |  |

## Known Gaps

| Gap | Why It Matters | Candidate Sources | Priority |
|---|---|---|---|
| EVTX sample/event-log corpora | More realistic Windows event investigations | EVTX samples, Chainsaw rules, Sysmon configs |  |
| Cloud provider incident response docs | Shepherd will need cloud triage later | AWS, Azure, GCP security docs |  |
| M365/Google Workspace audit logs | SaaS investigations are common | Microsoft UAL docs, Google Workspace audit docs |  |
| Malware analysis workflows | Current scope is DFIR-heavy, not malware-specialist-heavy | MalAPI, malware analysis references |  |
| AI/LLM incident sources | ATLAS is foundational but small | OWASP LLM Top 10, AI incident databases |  |

## Successor Recommendations

1.
2.
3.
