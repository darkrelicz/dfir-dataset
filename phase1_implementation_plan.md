# Phase 1: Taxonomy Restructuring

## Background

The old `taxonomy/` directory contained a monolithic `dfir_taxonomy.yaml` (357 lines) that tried to serve as both human documentation and machine-readable config, along with `validate_taxonomy.py`, `gap_analysis.py`, and `review_checklist.md`. This has already been deleted from `main`.

We're replacing it with a cleaner separation of concerns:

| File | Purpose | Audience |
|---|---|---|
| `docs/TAXONOMY.md` | Rich reference for the 57 artifact/domain categories | Human (you + successor) |
| `configs/quality.yaml` | Valid category IDs, domain groupings, coverage tiers | Machine (Phase 4 validator) |
| `configs/task_categories.yaml` | 5 task categories, distribution targets, domain fold-in rules | Machine (Phase 3 synthesizer) |

## Proposed Changes

### Documentation

#### [NEW] [TAXONOMY.md](file:///home/hunta/dfir-dataset/docs/TAXONOMY.md)

Comprehensive human reference document covering the 57-category artifact taxonomy. Structured as:

1. **Overview** — purpose, how to use, relationship to task categories
2. **Category Tables by Domain** — extracted from plan §1.1 (lines 62-213):
   - Windows (W1-W10), Linux (L1-L8), Network (N1-N6), SIEM (S1-S3), Cloud (C1-C6), File Storage (F1-F5), AI/LLM (A1-A4), Mobile (M1-M3), Anti-Forensics (AF1-AF4), Threat Intel (TI1-TI2), IoT/OT (OT1-OT2), Virtualization (V1), Supply Chain (SC1), Compliance (CL1-CL2)
   - Each entry: ID, forensic question, key artifact sources, example artifacts
3. **Coverage Mapping** — from plan §1.3 (lines 283-342):
   - Strong / Moderate / Weak coverage per category with primary sources
4. **Expanded Scope per Discipline** — from plan §1.4 (lines 346-632):
   - Tier A/B/C breakdown for each of the 9 forensic disciplines
   - Event Log Analysis, Memory Forensics, Filesystem & Disk, Registry, Network Artifacts, Anti-Forensics, Linux, Active Directory, Script & Command Forensics
5. **Summary Table** — 57 categories with domain, coverage tier, and current-iteration status

---

### Config Files

#### [MODIFY] [quality.yaml](file:///home/hunta/dfir-dataset/configs/quality.yaml)

Add a `taxonomy` section with:

```yaml
taxonomy:
  # Valid artifact/domain category IDs (Taxonomy B)
  # Used by Phase 4 validator to check taxonomy_refs on generated pairs
  domains:
    windows:
      ids: [W1, W2, W3, W4, W5, W6, W7, W8, W9, W10]
      coverage:
        strong: [W1, W2, W3, W5, W7, W8, W9, W10]
        moderate: [W4, W6]
        weak: []
    linux:
      ids: [L1, L2, L3, L4, L5, L6, L7, L8]
      coverage:
        strong: [L1, L2, L3]
        moderate: [L4, L5, L6]
        weak: [L7, L8]
    network:
      ids: [N1, N2, N3, N4, N5, N6]
      coverage:
        strong: []
        moderate: [N2, N4]
        weak: [N1, N3, N5, N6]
    siem:
      ids: [S1, S2, S3]
      coverage:
        strong: [S3]
        moderate: [S1]
        weak: [S2]
    cloud:
      ids: [C1, C2, C3, C4, C5, C6]
      coverage:
        strong: []
        moderate: [C1, C2]
        weak: [C3, C4, C5, C6]
    file_storage:
      ids: [F1, F2, F3, F4, F5]
      coverage:
        strong: []
        moderate: []
        weak: [F1, F2, F3, F4, F5]
    ai_llm:
      ids: [A1, A2, A3, A4]
      coverage:
        strong: [A1, A2, A3]
        moderate: [A4]
        weak: []
    mobile:
      ids: [M1, M2, M3]
      coverage:
        strong: []
        moderate: []
        weak: [M1, M2, M3]
    anti_forensics:
      ids: [AF1, AF2, AF3, AF4]
      coverage:
        strong: [AF1, AF3]
        moderate: []
        weak: [AF2, AF4]
    threat_intel:
      ids: [TI1, TI2]
      coverage:
        strong: []
        moderate: [TI1]
        weak: [TI2]
    iot_ot:
      ids: [OT1, OT2]
      coverage:
        strong: []
        moderate: []
        weak: [OT1, OT2]
    virtualization:
      ids: [V1]
      coverage:
        strong: []
        moderate: []
        weak: [V1]
    supply_chain:
      ids: [SC1]
      coverage:
        strong: []
        moderate: [SC1]
        weak: []
    compliance:
      ids: [CL1, CL2]
      coverage:
        strong: []
        moderate: []
        weak: [CL1, CL2]
```

Existing `scoring` and `deduplication` sections remain unchanged.

---

#### [NEW] [task_categories.yaml](file:///home/hunta/dfir-dataset/configs/task_categories.yaml)

New config for the 5 task categories (Taxonomy A):

```yaml
# configs/task_categories.yaml
# Defines the 5 task categories (what the model learns to DO)
# Consumed by Phase 3 synthesizer for prompt template selection

categories:
  artifact_analysis:
    description: "Interpret forensic tool output, identify anomalies, explain what artifacts mean"
    prompt_template: "artifact_analysis.md"
    absorbs: [AF1, AF3, A2, A4]  # Anti-forensics detection, AI app/infra forensics
    shepherd_alignment: ["Memory Agent", "Windows Event Log Agent"]

  ttp_identification:
    description: "Map observed behaviors to MITRE ATT&CK / ATLAS techniques, identify attack chain stages"
    prompt_template: "ttp_identification.md"
    absorbs: [A1, A3, TI1]  # AI attacks, AI supply chain, threat intel ops
    shepherd_alignment: ["All specialist agents"]

  triage_and_hunting:
    description: "Prioritize investigation steps, recommend evidence collection, proactive threat hunting"
    prompt_template: "triage_and_hunting.md"
    absorbs: [SC1]  # Supply chain triage
    shepherd_alignment: ["Orchestrator", "All specialist agents"]

  detection_engineering:
    description: "Write/interpret Sigma rules, explain detection logic, translate query languages"
    prompt_template: "detection_engineering.md"
    absorbs: [S1, S3]  # SIEM queries, detection coverage
    shepherd_alignment: ["Future detection capability"]

  report_generation:
    description: "Produce evidence-cited IR reports, calibrate confidence, flag overclaims"
    prompt_template: "report_generation.md"
    absorbs: []
    shepherd_alignment: ["Report Agent", "Reviewer Agent"]

distribution:
  # Target category distribution (must sum to 1.0)
  category_targets:
    artifact_analysis: 0.30
    ttp_identification: 0.25
    triage_and_hunting: 0.18
    detection_engineering: 0.14
    report_generation: 0.13

  # Target difficulty distribution (must sum to 1.0)
  difficulty_targets:
    junior: 0.30
    mid: 0.50
    senior: 0.20

deferred:
  # Categories deferred to successor (not generated in this iteration)
  - { domain: "AF2, AF4", reason: "Requires specialized sources" }
  - { domain: "TI2", reason: "Attribution requires sensitive context" }
  - { domain: "M1-M3", reason: "No mobile forensic sources" }
  - { domain: "OT1-OT2", reason: "Different domain" }
  - { domain: "V1", reason: "Niche" }
  - { domain: "CL1-CL2", reason: "Procedural/legal, not technical" }
  - { domain: "C3-C6", reason: "Limited cloud-specific sources" }
  - { domain: "F1-F5", reason: "Limited file forensic sources" }
```

---

### Stale Reference Cleanup

#### [MODIFY] [README.md](file:///home/hunta/dfir-dataset/README.md)

- Replace "Validating the Taxonomy" section (lines 24-36) — remove references to `taxonomy/validate_taxonomy.py` and `taxonomy/gap_analysis.py`
- Update directory structure (line 51) — replace `taxonomy/: Phase 1 task definitions` with `docs/: Documentation including TAXONOMY.md` and `configs/: Pipeline configuration including taxonomy IDs`

#### [MODIFY] [ARCHITECTURE.md](file:///home/hunta/dfir-dataset/docs/ARCHITECTURE.md)

- Replace "Why YAML for the Taxonomy?" section (lines 15-21) — update to reflect the new three-file design
- Replace "Why Pydantic for Validation?" section (lines 23-28) — remove or update since `validate_taxonomy.py` no longer exists
- Update "Directory Layout" section (lines 30-33) — remove `taxonomy/` reference

---

## Verification Plan

### Automated

```bash
# Confirm no stale taxonomy/ references remain
grep -rn "taxonomy/" --include="*.py" --include="*.yaml" --include="*.md" .

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('configs/quality.yaml')); yaml.safe_load(open('configs/task_categories.yaml')); print('YAML OK')"
```

### Manual
- Review `docs/TAXONOMY.md` for completeness against plan §1.1, §1.3, §1.4
- Confirm all 57 category IDs appear in both the doc and `quality.yaml`
