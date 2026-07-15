# Handover Guide

## Purpose

Use this guide to hand the dataset factory to a successor. This file is an operating guide, not the canonical current-state record.

For run-specific status, read generated manifests and the state files named in `PROJECT_BRIEF.md`:

- `project_state/PROJECT_BRIEF.md`
- `project_state/ARCHITECTURE.md`
- `project_state/TODO.md`
- `project_state/DECISIONS.md`
- generated manifests under `data/raw/`, `data/synthesized/`, `data/quality/`, and `data/packaged/`

## Handover Packet Checklist

Before handing over the project, make sure the successor can find:

- The current phase and next actions in `project_state/TODO.md`.
- Durable architecture and implementation notes in `project_state/ARCHITECTURE.md`.
- Durable decisions in `project_state/DECISIONS.md`.
- Raw collection outputs and `data/raw/collection_manifest.json`.
- Synthesis outputs and the relevant `generation_manifest.json`.
- Quality outputs and the relevant `quality_manifest.json`.
- Packaging outputs and the relevant `packaging_manifest.json`, if packaging exists.
- Training/evaluation outputs, if training exists.

## Successor Orientation

Explain these points during handover:

- Phase 3 `accepted.jsonl` is candidate synthesis output, not final training data.
- Phase 4 `filtered.jsonl` is the first dataset eligible for packaging.
- `review_queue.jsonl` is included in the current Phase 5 package by explicit time-boxed risk acceptance and transformed into direct-answer examples. Rejected rows remain excluded.
- Splits must be by `source_doc_id` to avoid leakage.
- Canonical responses use `<reasoning>`, not `<think>`.
- Model-specific exporters may transform formatting only at packaging time.
- Full-corpus generation should be treated as a separate budget decision.

## Reproduction Commands

### Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Collect Raw Sources

```bash
python -m scripts.collect_all
```

### Validate Raw Corpus

```bash
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
```

### Render Prompts

```bash
.venv/bin/python -m scripts.synthesize render-prompts --mode <pilot|subset|full> --output-dir data/synthesized/<run>
```

### Run Synthesis

```bash
.venv/bin/python -m scripts.synthesize run --mode <pilot|subset|full> --output-dir data/synthesized/<run>
```

### Run Phase 4 Quality Filter

```bash
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/<run>/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/<run> \
  --log-level INFO
```

## Critical Gates

Before packaging:

- [ ] Phase 4 deterministic and heuristic validation has run.
- [ ] Review queue has been adjudicated or explicitly excluded.
- [ ] Near-duplicate audit has been reviewed.
- [ ] Distribution audit has been reviewed.
- [ ] Manual spot-check sample has been reviewed.

Before training:

- [ ] Train/validation/test split is by `source_doc_id`.
- [ ] Dataset package loads locally.
- [ ] Dataset card is filled from the packaged run.
- [ ] Baseline evaluation set is finalized.
- [ ] Baseline model scores are recorded.

Before Shepherd integration:

- [ ] Fine-tuned model passes the calibrated local-judge comparison gate.
- [ ] No critical DFIR task or safety behavior has an unacceptable regression.
- [ ] No severe regressions on critical DFIR behavior.
- [ ] Reasoning format remains usable for Shepherd.
- [ ] Rollback path is documented.

## Artifact Inventory Template

Fill this table for a specific handover or release:

| Artifact | Path | Status | Notes |
|---|---|---|---|
| Raw manifest |  |  |  |
| Synthesis output |  |  |  |
| Quality output |  |  |  |
| Packaged dataset |  |  |  |
| Evaluation results |  |  |  |
| Training artifacts |  |  |  |

## Risk Review Template

| Risk | Status | Mitigation | Owner |
|---|---|---|---|
| Source imbalance |  |  |  |
| Thin sources cause padded answers |  |  |  |
| Prompt compaction removes useful evidence |  |  |  |
| Untagged general knowledge passes as source-only |  |  |  |
| Review queue is too large |  |  |  |
| Fine-tuning does not improve baseline |  |  |  |

## Credentials And Secrets

Do not commit real secrets.

- `GEMINI_API_KEY`: stored in `.env` or the environment
- DGX access: document outside the repository or in an approved secret store
- Local dataset storage path: repository-local `data/` unless changed

## Maintenance Rule

Update this guide only when the handover process changes. Do not use it as the current project status page.
