# TODO

This file tracks pending work only. Completed-stage status and artifact details
belong in `PROJECT_BRIEF.md` and generated manifests.

## Next

- Fix `scripts/finetune.py` to pass `lora_dropout` as `float`; its current
  integer conversion changes v3's configured `0.05` to zero.
- Train v3 with `configs/finetune_glm47flash_v3.yaml` and run a bounded
  direct-adapter `hello` smoke test. Require `EOS generated: True` before GGUF
  promotion or benchmark evaluation.
- Record the selected checkpoint, GGUF path, package and runtime versions,
  artifact hashes, and validation metrics.
- Finish reviewing the 68 benchmark cases under `evaluation/benchmark/` and
  record the review owner and date.
- Build and adjudicate a stratified human-scored judge calibration set. Assign
  a real calibration ID and freeze the judge configuration.
- Make `evaluation.comparison` reject placeholder calibration IDs such as
  `uncalibrated`, in addition to missing or mismatched IDs.
- Run complete calibrated base and v3 evaluations with the same benchmark and
  frozen judge, then compare them with `scripts/compare_evaluations.py`.
- Integrate into Shepherd only if the reviewed scorecard improves without
  unacceptable task-level or critical-behavior regressions.

## Reliability

- Add configurable retry or failure behavior for empty target-model content.

## Deferred

- Adjudicate the Phase 4 review queue and complete manual quality spot checks.
- Revisit scoring signals and dedupe or source-balance thresholds after review.
- Run full-corpus synthesis only in a future budget window, preceded by a
  one-prompt smoke test and reviewed pilot; use `--skip-present` when resuming.
- Run Claude or other teacher comparisons only as separate labeled jobs.
- Expand benchmark coverage after the initial reviewed benchmark is stable.
- Add tests for collectors and synthesis utilities.
- Keep `docs/` and project-state documents synchronized when architecture,
  commands, decisions, or artifact paths change.
