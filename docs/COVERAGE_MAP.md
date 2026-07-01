# Coverage Map

## Purpose

Track what the current dataset covers, what it only partially covers, and what should be added by a successor. This document should be updated after Phase 2 collection, Phase 3 synthesis, and Phase 4 filtering because coverage can change at each stage.

## Coverage Summary

Snapshot basis: Phase 2 raw corpus has 20,347 documents. The latest Phase 4 reduced-subset quality manifest is `quality-20260701T064847Z` under `data/quality/gemini_subset_1/` and contains 1,134 filtered pairs from 6,023 checked candidate pairs. Phase 3 `accepted.jsonl` may continue to grow after this snapshot; rerun Phase 4 before final packaging.

| Area | Coverage | Evidence | Gaps | Successor Priority |
|---|---|---|---|---|
| Windows endpoint forensics | strong | `W1`, `W4`, `W7`, `W8`, Sigma/Hayabusa/KAPE/ATT&CK/Atomic sources | Senior-depth case realism still synthetic | Medium |
| Linux endpoint forensics | moderate | `L1`, `L2`, `L3`, `L4`, `L5`, Atomic/ATT&CK/ForensicArtifacts | `L6`, `L7`, `L8` absent after filtering | High |
| macOS endpoint forensics | thin | Some cross-platform ATT&CK and ForensicArtifacts coverage | No strong macOS-specific filtered taxonomy category | High |
| Memory forensics | moderate | Volatility 3 docs and `W7` coverage | Malware reverse-engineering workflows are limited | Medium |
| Network forensics | moderate | `N3`, `N4`, `N5`, CISA/ATT&CK/Sigma coverage | `N1`, `N2`, `N6` absent after filtering | High |
| Cloud forensics | absent | No filtered `C*` taxonomy IDs | Cloud control plane, identity, storage, containers, and K8s sources are deferred | Very high |
| Identity/SaaS forensics | thin | Windows/AD identity via `W3`, `W9` | SaaS/M365/Google Workspace and file-storage IDs are absent | Very high |
| AI/LLM incident response | moderate | ATLAS tactics 16/16, `A1`, `A2` filtered coverage | `A3`, `A4` absent; real AI incident sources still thin | High |
| Detection engineering | strong | `S3` has 405 filtered refs; Sigma/Hayabusa dominate | Detection output is over target share and should be balanced if packaging time allows | Medium |
| Incident reporting | thin | 82 filtered `report_generation` pairs | Under target share in filtered output | High |

Coverage labels:

- `strong`: enough examples for training and evaluation
- `moderate`: usable, but likely imbalanced or shallow
- `thin`: present, but should not be trusted as a strength
- `absent`: no meaningful coverage

## Source Coverage

| Source | Raw Docs | Synthesized Pairs | Filtered Pairs | Main Strength | Main Weakness |
|---|---:|---:|---:|---|---|
| `atomic_red_team` | 1,811 | 485 | 112 | Procedure-level TTP examples | Can be terse and tool/procedure-heavy |
| `cisa_advisories` | 3,849 | 875 | 138 | Vulnerability/advisory triage | Large advisories require compaction and careful grounding |
| `cisa_kev` | 270 | 235 | 17 | Exploited vulnerability context | Vendor-grouped records can be broad |
| `cybersec_skills` | 670 | 55 | 5 | Practitioner workflows | Many rows route to review; review before relying on this source |
| `forensic_artifacts` | 731 | 281 | 67 | Artifact definitions | Thin source; easy to overgeneralize |
| `hayabusa_rules` | 4,839 | 772 | 112 | Windows event detections | Sigma overlap |
| `hijacklibs` | 590 | 243 | 43 | DLL hijacking references | Very thin source |
| `kape_files` | 811 | 289 | 92 | Artifact path definitions | Thin source |
| `lolbas_gtfobins` | 720 | 286 | 51 | Living-off-the-land abuse | Abuse entries are narrow |
| `loldrivers` | 656 | 291 | 5 | Driver abuse references | High rejection/review pressure; do not over-sample blindly |
| `mitre_atlas` | 262 | 249 | 42 | AI/ML threat taxonomy | Real-world AI incident evidence remains limited |
| `mitre_attack` | 697 | 497 | 137 | ATT&CK technique grounding | Procedure lists can be repetitive |
| `ossem_data_dicts` | 699 | 247 | 43 | Event field definitions | Field dictionaries need operational context |
| `sigma_rules` | 3,111 | 754 | 143 | Detection logic | Rule-centric; may overproduce detection engineering |
| `velociraptor_artifacts` | 437 | 296 | 81 | VQL/artifact collection | Prompts can be expensive because VQL is preserved |
| `volatility3_docs` | 194 | 194 | 46 | Memory tool usage | Tool docs need incident context |

## Task Category Coverage

| Category | Target Share | Synthesized Share | Filtered Share | Notes |
|---|---:|---:|---:|---|
| `artifact_analysis` | 30% | 30.0% | 36.8% | Filtered output is above target |
| `ttp_identification` | 25% | 25.9% | 20.2% | Filtered output is just within tolerance |
| `triage_and_hunting` | 18% | 17.1% | 14.6% | Filtered output is within tolerance |
| `detection_engineering` | 14% | 13.4% | 21.2% | Filtered output is above target |
| `report_generation` | 13% | 13.7% | 7.2% | Filtered output is below target |

## Difficulty Coverage

| Difficulty | Target Share | Synthesized Share | Filtered Share | Notes |
|---|---:|---:|---:|---|
| `junior` | 30% | 30.4% | 37.9% | Filtered output is above target |
| `mid` | 50% | 49.6% | 48.2% | Filtered output is within tolerance |
| `senior` | 20% | 20.0% | 13.8% | Filtered output is below target |

## Taxonomy Heatmap

Use `docs/TAXONOMY.md` and `configs/quality.yaml` as the source of truth for taxonomy IDs.

| Taxonomy ID | Name | Raw Source Support | Synthesized Pairs | Filtered Pairs | Coverage Label | Notes |
|---|---|---|---:|---:|---|---|
| S3 | Detection coverage | Sigma/Hayabusa/ATT&CK | n/a | 405 | strong | Highest filtered taxonomy signal |
| W8 | Event logs | Sigma/Hayabusa/OSSEM | n/a | 298 | strong | Windows event-log training strength |
| TI1 | Threat intel ops | ATT&CK/CISA/KEV | n/a | 189 | strong | Useful for IOC/advisory workflows |
| W1 | What executed? | ATT&CK/Atomic/Sigma | n/a | 174 | strong | Execution triage is well represented |
| W4 | Disk access/modification | KAPE/ForensicArtifacts/ATT&CK | n/a | 165 | strong | Artifact-path grounding is strong |
| N4 | C2/beaconing | ATT&CK/CISA/Sigma | n/a | 157 | strong | Network/C2 reasoning present |
| AF3 | Living off the land | LOLBAS/GTFOBins/Sigma/ATT&CK | n/a | 136 | strong | LOLBin abuse is well represented |
| A1/A2 | AI model access/attack staging | ATLAS | n/a | 84 | moderate | ATLAS present but real-world AI incident sources remain thin |
| Missing IDs | Cloud, SaaS/file storage, legal, containers, OT, malware, and several network IDs | Limited or absent in current sources | n/a | 0 | absent | Missing refs include `C1-C6`, `F1-F5`, `CL1-CL2`, `L6-L8`, `M1-M3`, `N1`, `N2`, `N6`, `OT1-OT2`, `A3-A4`, `W10` |

## ATT&CK And ATLAS Coverage

| Framework | Coverage Metric | Result | Notes |
|---|---|---:|---|
| ATT&CK tactics covered | Local tactic labels | 15/15 | Includes local labels `stealth` and `defense-impairment` from the cached ATT&CK bundle |
| ATT&CK techniques covered | Unique filtered technique IDs | 350 | 1,374 total MITRE technique references in filtered rows |
| ATLAS tactics covered | ATLAS tactic names | 16/16 | All local ATLAS tactics represented |
| ATLAS techniques covered | Unique filtered technique IDs | 86 | 153 total ATLAS technique references in filtered rows |

## Known Gaps

| Gap | Why It Matters | Candidate Sources | Priority |
|---|---|---|---|
| EVTX sample/event-log corpora | More realistic Windows event investigations | EVTX samples, Chainsaw rules, Sysmon configs | Medium |
| Cloud provider incident response docs | Shepherd will need cloud triage later | AWS, Azure, GCP security docs | Very high |
| M365/Google Workspace audit logs | SaaS investigations are common | Microsoft UAL docs, Google Workspace audit docs | Very high |
| Malware analysis workflows | Current scope is DFIR-heavy, not malware-specialist-heavy | MalAPI, malware analysis references | Medium |
| AI/LLM incident sources | ATLAS is foundational but small | OWASP LLM Top 10, AI incident databases | High |

## Successor Recommendations

1. Prioritize cloud and SaaS sources before expanding already-strong Windows event and detection-rule coverage.
2. Add realistic event-log or case-style corpora to reduce purely synthetic incident context.
3. Before packaging, adjudicate `review_queue.jsonl` and the 100-row manual spot-check sample, then rerun this coverage map from the final filtered set.
