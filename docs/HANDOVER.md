# Handover

## Snapshot

- Project: Shepherd DFIR Dataset
- Current owner: current project owner
- Handover date: 2026-06-29
- Repository: `/home/hunta/dfir-dataset`
- Dataset version: pre-packaging
- Shepherd version or branch: not set in this repository
- Target training platform: DGX Sparks
- Training approach: LoRA SFT via Unsloth
- Base model: GLM-4.7-Flash

## Executive Summary

- Phase 1 taxonomy work is complete enough for synthesis: the human taxonomy is in `docs/TAXONOMY.md`, and machine-readable taxonomy validation lives in `configs/quality.yaml`.
- Phase 2 collection is complete for the selected Core + Tier 1 + Tier 2 scope: 16 collectors, 20,347 raw documents, and zero raw validation issues in the current corpus.
- Phase 3 scaffolding is implemented: prompt planning, prompt rendering, deterministic taxonomy-ref suggestions, Gemini client/runner, run-state handling, inline validators, and prompt-time source compaction.
- Prompt-cost reduction is handled at prompt time, not by mutating Phase 2 raw documents. Current source-specific compactors cover `cisa_advisories`, `cisa_kev`, `mitre_attack`, `cybersec_skills`, `velociraptor_artifacts`, `loldrivers`, and `hijacklibs`.
- The full Gemini pilot and full synthesis are still gated. Existing old pilot artifacts should be treated as historical until prompts are regenerated with the current taxonomy and compactor behavior.
- Phase 4 quality filtering, Phase 5 packaging, and Phase 6 training/evaluation are planned but not yet implemented.
- The next critical gate is a regenerated dry-run prompt review followed by a one-prompt Gemini smoke test and a source-aware pilot.
- The biggest known risk is prompt compaction or truncation removing evidence that the model needs for grounded answers.

## Current Phase Status

| Phase | Status | Evidence | Next Action |
|---|---|---|---|
| Phase 1: Taxonomy | Complete for current scope | `docs/TAXONOMY.md`, `configs/quality.yaml` | Revisit only if new source families require new artifact IDs |
| Phase 2: Collection | Complete for selected 16 sources | `data/raw/*.jsonl`; validation passes with 20,347 unique docs | Re-run collectors only when upstream refresh is needed |
| Phase 3: Synthesis | In progress | `synthesizers/`, `scripts/synthesize.py`, `configs/synthesis.yaml`, `data/synthesized/dry_run/` | Regenerate/review prompts, then run Gemini smoke test and pilot |
| Phase 4: Quality | Planned | `docs/QUALITY_RUBRIC.md`, `configs/quality.yaml` | Implement deterministic and heuristic quality pipeline |
| Phase 5: Packaging | Planned | `configs/packaging.yaml` | Package Phase 4 filtered output only |
| Phase 6: Training | Planned | `docs/TRAINING_RECIPE.md` | Run baseline before LoRA SFT |

## What Is Done

- Source collectors: all 16 selected collectors emit `RawDocument` JSONL under `data/raw/`.
- Raw corpus validation: `.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw` currently reports 16 files, 20,347 documents, 20,347 unique IDs, and 0 issues.
- Prompt templates: base, category, source-type, and selected content-type templates exist under `synthesizers/prompts/`.
- Prompt compactors: shared compactor dispatch/helpers live in `synthesizers/prompts/compactors/prompt_compactors.py`; source compactors currently live in `cisa_advisories_compactor.py`, `cisa_kev_compactor.py`, `mitre_attack_compactor.py`, `cybersec_skills_compactor.py`, `velociraptor_artifacts_compactor.py`, `loldrivers_compactor.py`, and `hijacklibs_compactor.py`.
- Synthesis runner: `synthesizers/runner.py` renders prompts, calls Gemini, writes prompt/raw/accepted/rejected/manifest files, and supports terminal-output skipping.
- Inline validators: Phase 3 rejects invalid JSON, schema mismatches, wrong source/category/difficulty, missing or invalid taxonomy refs, malformed ATT&CK/ATLAS IDs, broken reasoning links, missing caveats, empty reasoning lines, missing final answers, and invented concrete indicators.
- Quality filters, packaging outputs, evaluation, and training artifacts are not yet implemented.

## What Is Next

1. Regenerate dry-run prompts with the current prompt compactor and taxonomy-ref rendering.
2. Manually inspect dry-run prompts for CISA advisories and other high-token source families.
3. Run a one-prompt Gemini smoke test and inspect `accepted.jsonl`, `rejected.jsonl`, `raw_outputs.jsonl`, and `generation_manifest.json`.
4. Run the planned source-aware Gemini pilot if the smoke test passes.
5. Review 100% of pilot accepted and rejected rows before full synthesis.
6. Add the next high-value source compactors based on observed prompt sizes and review results.
7. Implement Phase 4 deterministic and heuristic quality filtering before packaging.

## Important Decisions

| Decision | Rationale | Source |
|---|---|---|
| Canonical reasoning tag is `<reasoning>` | Keeps validation and audit format stable | `docs/DECISIONS.md` |
| Pydantic schema does not replace reasoning-format prompt instructions | Gemini still needs explicit linked-reasoning structure and example text | `docs/DECISIONS.md`, `synthesizers/prompts/base.md` |
| Taxonomy refs are deterministic-first prompt metadata | Reduces prompt size while preserving valid taxonomy grounding | `docs/DECISIONS.md`, `synthesizers/prompt_builder.py` |
| Raw Phase 2 documents stay complete; prompts may use compacted source views | Preserves provenance while reducing prompt cost | `docs/DECISIONS.md` |
| Source compactors live under `synthesizers/prompts/compactors/<source>_compactor.py` and expose `compact_for_prompt` | Keeps source-specific prompt reduction modular | `docs/DECISIONS.md` |
| Phase 5 consumes Phase 4 filtered output, not raw Phase 3 accepted output | Prevents candidate data from being treated as training data | `docs/DECISIONS.md` |
| Dataset hosting is local-only unless changed | Matches current training plan | `docs/DECISIONS.md` |

## Critical Gates

Before full synthesis:

- [x] Raw corpus validation passes.
- [ ] Phase 3 code review is complete.
- [ ] Dry-run prompt review confirms compaction does not remove required evidence.
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
| Raw manifest | `data/raw/collection_manifest.json` | Current | Produced by Phase 2 collection |
| Dry-run prompts | `data/synthesized/dry_run/` | Current but should be regenerated after prompt changes | Used for manual prompt review and cost estimation |
| Historical Gemini pilot | `data/synthesized/gemini_pilot_1/` | Historical | Pre-current prompt/taxonomy state; do not treat as final gate |
| Pilot synthesis | `data/synthesized/pilot/` | Not current | Next canonical pilot output location |
| Full synthesis | `data/synthesized/full/` | Not started | Must wait for accepted pilot |
| Quality output | `data/quality/` | Not started | Phase 4 |
| Packaged dataset | `data/packaged/` | Not started | Phase 5 |
| Evaluation results | `data/evaluation/` | Not started | Phase 6 |

## Known Risks

| Risk | Status | Mitigation | Owner |
|---|---|---|---|
| Full pair volume exceeds original plan | Open | Decide source caps before full generation | Project owner |
| Source imbalance | Open | Audit source distribution after synthesis and quality filtering | Project owner |
| Thin sources cause padded answers | Open | Keep pair caps low and review pilot thin-source outputs | Project owner |
| Prompt compaction removes useful evidence | Open | Review compacted prompts by source and add source-specific tests or checks where needed | Project owner |
| Sigma/Hayabusa duplicates | Open | Run near-duplicate detection in Phase 4 | Project owner |
| Fine-tuning may not improve baseline | Open | Run baseline before training and document before/after results | Project owner |

## Credentials And Secrets

Do not commit real secrets.

- `GEMINI_API_KEY`: stored in `.env` or the environment
- DGX access: not documented here
- Local dataset storage path: repository-local `data/` unless changed

## Final Checklist

- [x] `docs/ARCHITECTURE.md` reflects current Phase 3 code shape.
- [x] `docs/DECISIONS.md` reflects current prompt compaction and taxonomy decisions.
- [ ] `docs/COVERAGE_MAP.md` reflects final source and taxonomy coverage.
- [x] `docs/PROMPT_GUIDE.md` reflects prompt iteration history.
- [ ] `docs/QUALITY_RUBRIC.md` reflects final quality gates.
- [ ] `docs/DATASET_CARD.md` reflects packaged dataset contents.
- [ ] `docs/TRAINING_RECIPE.md` reflects training and evaluation results.
- [ ] Commands above have been tested from a clean checkout or clean environment.
