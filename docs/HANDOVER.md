# Handover

## Snapshot

- Project: Shepherd DFIR Dataset
- Current owner:
- Handover date:
- Repository:
- Dataset version:
- Shepherd version or branch:
- Target training platform: DGX Sparks
- Training approach: LoRA SFT via Unsloth
- Base model: GLM-4.7-Flash

## Executive Summary

Summarize the state of the dataset factory in 5-10 sentences:

- What is complete:
- What is partially complete:
- What is not started:
- The next critical gate:
- The biggest known risk:

## Current Phase Status

| Phase | Status | Evidence | Next Action |
|---|---|---|---|
| Phase 1: Taxonomy |  |  |  |
| Phase 2: Collection |  |  |  |
| Phase 3: Synthesis |  |  |  |
| Phase 4: Quality |  |  |  |
| Phase 5: Packaging |  |  |  |
| Phase 6: Training |  |  |  |

## What Is Done

List completed work with paths and commands where possible.

- Source collectors:
- Raw corpus validation:
- Prompt templates:
- Synthesis runner:
- Quality filters:
- Packaging outputs:
- Evaluation/training artifacts:

## What Is Next

List the next 5-10 actions in strict order.

1.
2.
3.
4.
5.

## Important Decisions

Capture only decisions a successor must not accidentally reverse.

| Decision | Rationale | Source |
|---|---|---|
| Canonical reasoning tag is `<reasoning>` | Keeps validation and audit format stable | `docs/DECISIONS.md` |
| Phase 5 consumes Phase 4 filtered output, not raw Phase 3 accepted output | Prevents candidate data from being treated as training data | `docs/DECISIONS.md` |
| Dataset hosting is local-only unless changed | Matches current training plan | `docs/DECISIONS.md` |

## Critical Gates

Before full synthesis:

- [ ] Raw corpus validation passes.
- [ ] Phase 3 code review is complete.
- [ ] One-prompt Gemini smoke test is acceptable.
- [ ] Pilot pass rate meets the selected threshold.
- [ ] Pilot manual review does not show systemic hallucination or weak reasoning.

Before packaging:

- [ ] Phase 4 deterministic validation is complete.
- [ ] Near-duplicate review is complete.
- [ ] Distribution audit is complete.
- [ ] Manual spot-check is complete.

Before training:

- [ ] Train/validation/test split is by `source_doc_id`.
- [ ] Dataset package loads locally.
- [ ] Baseline evaluation set is finalized.
- [ ] Baseline model scores are recorded.

## How To Reproduce

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

### Render Pilot Prompts

```bash
.venv/bin/python -m scripts.synthesize render-prompts --mode pilot --output-dir data/synthesized/dry_run
```

### Run Pilot Synthesis

```bash
.venv/bin/python -m scripts.synthesize run --mode pilot --output-dir data/synthesized/pilot
```

### Run Full Synthesis

```bash
.venv/bin/python -m scripts.synthesize run --mode full --output-dir data/synthesized/full
```

## Generated Artifacts

| Artifact | Path | Status | Notes |
|---|---|---|---|
| Raw manifest | `data/raw/collection_manifest.json` |  |  |
| Dry-run prompts | `data/synthesized/dry_run/` |  |  |
| Pilot synthesis | `data/synthesized/pilot/` |  |  |
| Full synthesis | `data/synthesized/full/` |  |  |
| Quality output | `data/quality/` |  |  |
| Packaged dataset | `data/packaged/` |  |  |
| Evaluation results | `data/evaluation/` |  |  |

## Known Risks

| Risk | Status | Mitigation | Owner |
|---|---|---|---|
| Full pair volume exceeds original plan |  | Decide source caps before full generation |  |
| Source imbalance |  | Audit source distribution after synthesis and quality filtering |  |
| Thin sources cause padded answers |  | Keep pair caps low and review pilot thin-source outputs |  |
| Sigma/Hayabusa duplicates |  | Run near-duplicate detection in Phase 4 |  |
| Fine-tuning may not improve baseline |  | Run baseline before training and document before/after results |  |

## Credentials And Secrets

Do not commit real secrets.

- `GEMINI_API_KEY`: stored in `.env` or the environment
- DGX access:
- Local dataset storage path:

## Final Checklist

- [ ] `docs/ARCHITECTURE.md` reflects final code shape.
- [ ] `docs/DECISIONS.md` reflects final decisions.
- [ ] `docs/COVERAGE_MAP.md` reflects final source and taxonomy coverage.
- [ ] `docs/PROMPT_GUIDE.md` reflects prompt iteration history.
- [ ] `docs/QUALITY_RUBRIC.md` reflects final quality gates.
- [ ] `docs/DATASET_CARD.md` reflects packaged dataset contents.
- [ ] `docs/TRAINING_RECIPE.md` reflects training and evaluation results.
- [ ] Commands above have been tested from a clean checkout or clean environment.
