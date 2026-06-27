# Prompt Guide

## Purpose

This guide explains how Phase 3 prompts are structured, how to review pilot outputs, and how to safely iterate prompts without losing provenance.

## Prompt Architecture

Prompt construction uses three layers:

1. Base prompt: `synthesizers/prompts/base.md`
2. Task category prompt: `synthesizers/prompts/categories/*.md`
3. Source-type prompt plus optional content-type override:
   - `synthesizers/prompts/source_types/*.md`
   - `synthesizers/prompts/content_types/*.md`

Source and content-type policy lives in `configs/source_profiles.yaml`.

Task category and difficulty targets live in `configs/task_categories.yaml`.

## Canonical Response Format

All synthesized responses must use the canonical reasoning format:

```text
<reasoning>
E1: Source-grounded evidence.
A1 [uses E1]: Analysis of the evidence.
C1 [uses E1,A1] Confidence: medium. Conclusion.
CV1 [applies_to C1]: Caveat or corroboration need.
</reasoning>

Final practitioner-ready answer.
```

Do not switch canonical data to `<think>`. A model-specific Phase 5 exporter may create a training view using `<think>` only if the training recipe requires it.

## Prompt Review Checklist

Review dry-run prompts before API generation.

- [ ] Prompt asks for the expected number of pairs.
- [ ] Source document is recognizable and not over-truncated.
- [ ] Task category fits the source.
- [ ] Difficulty level is plausible.
- [ ] Source-type instructions are appropriate.
- [ ] Content-type override is present only when useful.
- [ ] Thin sources are capped.
- [ ] Prompt explicitly bans invented IOCs, paths, hashes, users, hosts, and event records.
- [ ] Output schema matches `synthesizers.schemas.InstructionPair`.

## Pilot Review Rubric

Score each pilot pair before full generation.

| Dimension | Pass Criteria | Notes |
|---|---|---|
| Grounding | Claims are supported by source evidence or marked `[GENERAL KNOWLEDGE]` |  |
| Reasoning links | Evidence, analysis, conclusions, and caveats reference valid IDs |  |
| Final answer consistency | Final answer does not introduce unsupported findings |  |
| Operational usefulness | Answer helps a real analyst act or decide |  |
| Specificity | Response uses source-specific details without inventing them |  |
| Uncertainty | Confidence and caveats are appropriate |  |
| Thin-source handling | No padded forensic detail from sparse records |  |

## Iteration Log

Use this table whenever prompt behavior changes.

| Date | File Changed | Reason | Expected Effect | Validation Result |
|---|---|---|---|---|
|  |  |  |  |  |

## Common Failure Modes

| Failure | Likely Cause | Fix |
|---|---|---|
| Invented file paths or IOCs | Source is thin or prompt asks for too much detail | Lower pair cap, strengthen source-only instruction |
| Broken reasoning links | Model ignored format or prompt examples are ambiguous | Tighten format example and validator feedback |
| Rephrased duplicate pairs | Pair count too high for the document | Lower source/content-type pair cap |
| Generic answers | Source truncation removed useful fields or source is too sparse | Adjust `max_source_chars` or cap pairs |
| Overconfident conclusions | Prompt underemphasizes caveats | Strengthen uncertainty and corroboration instructions |
| Unsupported ATT&CK/ATLAS mapping | Model inferred too aggressively | Require candidate `?` suffix or source-backed mapping only |

## Smoke Test Procedure

1. Pick one representative prompt.
2. Run a one-prompt Gemini job.
3. Inspect:
   - `accepted.jsonl`
   - `rejected.jsonl`
   - `raw_outputs.jsonl`
   - `generation_manifest.json`
4. Confirm validators behave as expected.
5. Fix prompt or validator issues before the full pilot.

## Full Pilot Procedure

1. Render pilot prompts.
2. Run pilot generation.
3. Review 100% of accepted and rejected outputs.
4. Record rejection reasons.
5. Record manual quality issues.
6. Update prompt templates, source profiles, or pair caps.
7. Re-run pilot if quality is below the selected gate.

## Full Generation Rules

- Do not run full synthesis from an invalid raw corpus.
- Do not run full synthesis before pilot quality is acceptable.
- Preserve all prompt, raw output, accepted, rejected, and manifest files.
- Keep alternate teacher-model comparisons in separate labeled output directories.
