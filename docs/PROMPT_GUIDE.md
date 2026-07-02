# Prompt Guide

## Purpose

This guide explains how Phase 3 prompts are structured, how to review generated outputs, and how to safely iterate prompts without losing provenance.

## Prompt Architecture

Prompt construction uses four layers:

1. Base prompt: `synthesizers/prompts/base.md`
2. Task category prompt: `synthesizers/prompts/categories/*.md`
3. Source-type prompt plus optional content-type override:
   - `synthesizers/prompts/source_types/*.md`
   - `synthesizers/prompts/content_types/*.md`
4. Prompt-time source compaction:
   - Shared dispatch and helpers: `synthesizers/prompts/compactors/prompt_compactors.py`
   - Source-specific compactors: `synthesizers/prompts/compactors/<source>_compactor.py`

Source and content-type policy lives in `configs/source_profiles.yaml`.

Task category and difficulty targets live in `configs/task_categories.yaml`.

Prompt compaction must not mutate Phase 2 raw documents. Raw documents stay complete for provenance and reprocessing; compactors only create shorter source views for Phase 3 prompts. Source-specific compactors follow the naming convention `synthesizers/prompts/compactors/<source>_compactor.py`.

Velociraptor is a special case: VQL is the valuable training signal, so `velociraptor_artifacts_compactor.py` preserves query bodies in full and opts out of shared source truncation. Review large Velociraptor prompts for cost, but do not solve that by capping `precondition`, `export`, `query`, `queries`, VQL-like parameter defaults, or long structured parameter defaults such as YARA, Grok, CSV, registry glob, JSON, and YAML blocks.

Lossy source compactors append a shared note: `[Compacted source view: repeated or lower-priority blocks were omitted. Use only visible details as evidence.]`

## Taxonomy Refs

`PromptBuilder` renders a deterministic JSON list of one to three suggested taxonomy IDs into each prompt:

```text
Taxonomy references: ["TI1", "N4", "S3"]
```

The full 57-ID taxonomy is not repeated in every prompt. The model should normally copy or use the rendered refs, and Phase 3 validators still reject missing or unknown taxonomy refs.

`PromptRecord` also stores the deterministic taxonomy refs. During Phase 3 validation, generated `category`, `difficulty`, `source_doc_id`, `source`, `taxonomy_refs`, and `reasoning_format` are normalized from the prompt record before validation so model typos in provenance metadata do not reject otherwise valid pairs.

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

## Grounding Contract

The `grounding` field must match the response text:

- Use `source_only` only when every substantive claim is directly supported by the visible source document. A `source_only` response must not contain `[GENERAL KNOWLEDGE]`.
- Use `source_plus_general` whenever any substantive claim uses well-established knowledge that is not directly present in the visible source document. Every non-source claim must be explicitly marked with `[GENERAL KNOWLEDGE]`.
- Do not mark source-derived evidence, source-derived conclusions, or source-visible details as `[GENERAL KNOWLEDGE]`.

Phase 3 validators reject obvious tag/field mismatches: `source_only` with `[GENERAL KNOWLEDGE]`, and `source_plus_general` with no `[GENERAL KNOWLEDGE]` tag.

## Prompt Review Checklist

Review dry-run prompts before API generation.

- [ ] Prompt asks for the expected number of pairs.
- [ ] Source document is recognizable and not over-truncated.
- [ ] If a prompt compaction note is present, the compacted content still includes enough source evidence for the requested task.
- [ ] Taxonomy refs render as a JSON list, not a quoted string, and match valid taxonomy IDs.
- [ ] Task category fits the source.
- [ ] Difficulty level is plausible.
- [ ] Source-type instructions are appropriate.
- [ ] Content-type override is present only when useful.
- [ ] Thin sources are capped.
- [ ] Prompt explicitly bans invented IOCs, paths, hashes, users, hosts, and event records.
- [ ] Output schema matches `synthesizers.schemas.InstructionPair`.

## Pilot Review Rubric

Score each pilot pair before any future full-corpus generation or major prompt rerun.

| Dimension | Pass Criteria | Notes |
|---|---|---|
| Grounding | Claims are supported by source evidence or marked `[GENERAL KNOWLEDGE]` |  |
| Reasoning links | Evidence, analysis, conclusions, and caveats reference valid IDs |  |
| Final answer consistency | Final answer does not introduce unsupported findings |  |
| Operational usefulness | Answer helps a real analyst act or decide |  |
| Specificity | Response uses source-specific details without inventing them |  |
| Uncertainty | Confidence and caveats are appropriate |  |
| Thin-source handling | No padded forensic detail from sparse records |  |

## Prompt Change Review Template

Use this table in a run note or pull request when prompt behavior changes. Do not use this guide as the prompt history log.

| File Changed | Reason | Expected Effect | Validation To Run |
|---|---|---|---|
|  |  |  |  |

## Common Failure Modes

| Failure | Likely Cause | Fix |
|---|---|---|
| Invented file paths or IOCs | Source is thin or prompt asks for too much detail | Lower pair cap, strengthen source-only instruction |
| Broken reasoning links | Model ignored format or prompt examples are ambiguous | Tighten format example and validator feedback |
| Rephrased duplicate pairs | Pair count too high for the document | Lower source/content-type pair cap |
| Generic answers | Source truncation removed useful fields or source is too sparse | Adjust `max_source_chars` or cap pairs |
| Compacted prompt lacks key evidence | Source-specific compactor removed a section needed for the task | Adjust the source compactor or add task-aware preservation rules |
| JSON array wrapped in Markdown fences | Legacy Interactions text output path or model fallback treated JSON as code text | Use structured Gemini JSON output; validator still strips a full-output JSON fence before parsing as a compatibility fallback |
| Gemini API rejects `additional_properties` in `response_schema.items` | Pydantic `extra="forbid"` emitted `additionalProperties: false`, which the SDK serialized into an unsupported Gemini schema field | Send a sanitized API schema without `additionalProperties`; keep strict extra-field rejection in local Pydantic validation |
| Gemini API rejects `Thinking level is not supported for this model` | Legacy Interactions `thinking_level` was mapped into `generate_content` thinking config | Remove `thinking_level`; use supported `thinking_budget` for Gemini 2.5 thinking control and do not request thought summaries for structured JSON output |
| `taxonomy_refs` rendered as a string | Prompt template or builder passed JSON as quoted text | Render the list directly from `json.dumps(...)` without extra quotes |
| Overconfident conclusions | Prompt underemphasizes caveats | Strengthen uncertainty and corroboration instructions |
| Unsupported ATT&CK/ATLAS mapping | Model inferred too aggressively | Require candidate `?` suffix or source-backed mapping only |
| `source_only` response contains `[GENERAL KNOWLEDGE]` | Model tagged outside-source reasoning but left grounding as source-only | Validator rejects; regenerate with `source_plus_general` or remove non-source claim |
| `source_plus_general` response has no `[GENERAL KNOWLEDGE]` tag | Model set broad grounding but did not identify which claim is non-source | Validator rejects; tag each non-source claim or use `source_only` if all claims are source-backed |
| Recoverable validation failures persist after first generation | Model missed reasoning link, caveat, ID-shape, grounding, or indicator rule | Runner retries once with validator feedback; review remaining rejects for prompt or validator changes |
| Gemini high-demand `503 UNAVAILABLE` API errors | Temporary model capacity spike | API retry/backoff uses `max_retries`, initial delay, max delay, and jitter from `configs/synthesis.yaml`; rerun with `--skip-present` if needed |

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
- Do not run future full-corpus synthesis before smoke and pilot quality are acceptable.
- Preserve all prompt, raw output, accepted, rejected, and manifest files.
- Keep alternate teacher-model comparisons in separate labeled output directories.
