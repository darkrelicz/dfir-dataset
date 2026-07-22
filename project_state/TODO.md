# TODO

Pending work only. Completed state belongs in `PROJECT_BRIEF.md`; run facts
belong in generated manifests.

## Candidate Gate

- Fix `scripts/test_lora.py`: intersect generated IDs with the configured stop
  IDs, parameterize the adapter and prompts, and fail on termination,
  repetition, or template-leakage violations.
- Retest the v5 final adapter and checkpoint 250 with greeting and DFIR prompts.
- Choose v5 or staged v6 as the next candidate and record its checkpoint,
  artifacts, hashes, package/runtime versions, and validation metrics.

## Evaluation And Release

- Finish manual review of the 68 benchmark cases and record owner/date.
- Build a stratified human-scored judge calibration set, assign a real
  calibration ID, and freeze the judge configuration.
- Harden evaluation: reject placeholder calibration IDs, fingerprint target
  inputs and served-model identity, make failed regression gates enforceable,
  retry or fail empty target content, and prevent mixed checkpoint state.
- Run complete calibrated base and tuned evaluations with identical inputs and
  compare them with `scripts/compare_evaluations.py`.
- Integrate into Shepherd only after reviewed improvement with no unacceptable
  task-level or critical-behavior regressions.

## Deferred

- Adjudicate the Phase 4 review queue and complete manual quality spot checks.
- Revisit scoring, deduplication, and source-balance thresholds after review.
- Run full-corpus synthesis only in a future budget window after a smoke test
  and reviewed pilot; use `--skip-present` when resuming.
- Run alternate-teacher comparisons only as separate labelled jobs.
- Expand benchmark coverage and add collector/synthesis tests.
