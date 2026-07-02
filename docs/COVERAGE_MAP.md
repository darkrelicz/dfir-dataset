# Coverage Map Guide

## Purpose

Use this guide to assess dataset coverage after collection, synthesis, and quality filtering. 

For run-specific values, read generated manifests and the state files named in `PROJECT_BRIEF.md`:

- `docs/PROJECT_BRIEF.md`
- `docs/ARCHITECTURE.md`
- `docs/TODO.md`
- `docs/DECISIONS.md`
- `data/raw/collection_manifest.json`
- `data/synthesized/<run>/generation_manifest.json`
- `data/quality/<run>/quality_manifest.json`

## Coverage Inputs

Use these sources when preparing a run-specific coverage report:

| Input | What It Answers |
|---|---|
| `data/raw/collection_manifest.json` | Which raw collectors ran and how many documents each produced |
| `data/synthesized/<run>/accepted.jsonl` | Which sources, categories, difficulties, techniques, and taxonomy refs synthesis produced |
| `data/synthesized/<run>/rejected.jsonl` | Which prompts failed generation or Phase 3 validation |
| `data/quality/<run>/quality_manifest.json` | Filtered/review/rejected counts, distributions, tactic coverage, and taxonomy coverage |
| `data/quality/<run>/review_queue.jsonl` | Fuzzy quality issues requiring human or AI-assisted adjudication |
| `configs/quality.yaml` | Valid taxonomy refs, coverage groupings, and quality thresholds |
| `configs/task_categories.yaml` | Target category and difficulty distributions |

## Coverage Labels

Use consistent labels when summarizing coverage:

| Label | Meaning |
|---|---|
| `strong` | Enough filtered examples for training and evaluation |
| `moderate` | Usable but shallow, imbalanced, or synthetic-heavy |
| `thin` | Present but should not be treated as a model strength |
| `absent` | No meaningful filtered coverage |

## Review Dimensions

Check coverage along these dimensions:

- Source family distribution: no single source should dominate the filtered set unless intentionally chosen.
- Task category distribution: compare against `configs/task_categories.yaml`.
- Difficulty distribution: compare against the configured junior/mid/senior target.
- Taxonomy coverage: report covered, thin, and absent taxonomy IDs from `configs/quality.yaml`.
- ATT&CK coverage: summarize tactic and technique coverage from the quality manifest.
- ATLAS coverage: summarize AI/ML tactic and technique coverage from the quality manifest.
- Review pressure: identify sources or categories that mostly route to `review_queue.jsonl`.
- Rejection pressure: identify sources or categories with high hard-rejection rates.

## Common Gaps To Watch

These areas are likely to remain weak unless new sources are added:

| Gap | Why It Matters | Candidate Sources |
|---|---|---|
| Cloud provider incident response | Cloud control-plane and identity investigations are common in real environments | AWS, Azure, GCP security and audit documentation |
| SaaS and file-storage forensics | M365, Google Workspace, and file-storage abuse are common enterprise cases | Microsoft UAL docs, Google Workspace audit docs, Box/Dropbox/SharePoint references |
| Realistic event-log corpora | Rule sources can be too synthetic without realistic event context | EVTX samples, Chainsaw examples, Sysmon configs |
| Malware analysis workflows | The current plan is DFIR-heavy, not malware-specialist-heavy | MalAPI, malware analysis references, sandbox report schemas |
| AI/LLM incident sources | ATLAS is foundational but real incident depth is limited | OWASP LLM Top 10, AI incident databases, model-platform audit docs |

## Coverage Report Template

Use this template in a run-specific report when packaging a dataset:

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

## Maintenance Rule

Change this guide only when the coverage-review method changes. Do not use it as a live snapshot of a run.
