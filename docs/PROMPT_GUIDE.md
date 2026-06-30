# Prompt Guide

## Purpose

This guide explains how Phase 3 prompts are structured, how to review pilot outputs, and how to safely iterate prompts without losing provenance.

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

Prompt compaction must not mutate Phase 2 raw documents. Raw documents stay complete for provenance and reprocessing; compactors only create shorter source views for Phase 3 prompts. Current source-specific compactors are `cisa_advisories_compactor.py`, `cisa_kev_compactor.py`, `mitre_attack_compactor.py`, `cybersec_skills_compactor.py`, `velociraptor_artifacts_compactor.py`, `loldrivers_compactor.py`, and `hijacklibs_compactor.py`.

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
| 2026-06-29 | `synthesizers/prompts/base.md`, `synthesizers/prompt_builder.py`, `synthesizers/prompts/compactors/prompt_compactors.py`, `synthesizers/prompts/compactors/cisa_advisories_compactor.py` | Reduce prompt cost while keeping taxonomy refs deterministic and valid | Smaller CISA advisory prompts, no full taxonomy list in every prompt, non-empty valid `taxonomy_refs` in output schema | Python compile passed; dry-run prompt rendering passed; raw validation passed |
| 2026-06-29 | `synthesizers/prompts/compactors/mitre_attack_compactor.py`, `synthesizers/prompts/compactors/cybersec_skills_compactor.py` | Compact two remaining high-token source families before pilot cost estimation | Large ATT&CK procedure lists and Cybersecurity Skills scripts are capped while identifiers, mappings, detections, tools, examples, and workflow steps remain available | Python compile passed; pilot prompt rendering wrote 285 prompts |
| 2026-06-29 | `synthesizers/prompts/compactors/cisa_kev_compactor.py` | Compact vendor-grouped KEV catalogs that duplicate large summary tables and detailed CVE blocks | Large vendors keep vendor/product/CVE summary metadata and selected ransomware-linked/recent detail blocks without prompt-size truncation | Python compile passed; pilot prompt rendering wrote 285 prompts |
| 2026-06-29 | `synthesizers/prompts/compactors/velociraptor_artifacts_compactor.py`, `synthesizers/prompts/compactors/prompt_compactors.py` | Compact Velociraptor metadata/prose while preserving VQL query bodies in full | Duplicate rendered prose and non-query YAML boilerplate are shortened; VQL bodies bypass shared source truncation | Python compile passed; pilot prompt rendering wrote 285 prompts |
| 2026-06-29 | `synthesizers/prompts/compactors/loldrivers_compactor.py`, `synthesizers/prompts/compactors/hijacklibs_compactor.py` | Compact abuse databases with repeated sample, hash, executable, and signature blocks | LOLDrivers keeps abuse commands, mappings, detections, selected hashes, and sample metadata; HijackLibs keeps paths, hijack types, conditions, variables, hashes, and elevation flags | Python compile passed; pilot prompt rendering wrote 285 prompts |
| 2026-06-30 | `synthesizers/prompts/compactors/cybersec_skills_compactor.py`, `synthesizers/prompts/compactors/velociraptor_artifacts_compactor.py` | Fix malformed Markdown truncation and preserve long structured Velociraptor defaults | Cybersecurity Skills truncation closes code fences; Velociraptor keeps long VQL, YARA, Grok, CSV, registry glob, JSON, and YAML parameter defaults as full blocks | Python compile passed; corpus checks found 0 Cybersecurity Skills docs with odd code fences and 42/42 long Velociraptor defaults preserved as blocks |
| 2026-06-30 | `synthesizers/prompts/compactors/prompt_compactors.py`, `synthesizers/prompts/compactors/*_compactor.py` | Standardize lossy compaction note and avoid implying the model can access hidden raw corpus content | Lossy compacted source views append the same short note telling the model to use only visible details as evidence | Python compile passed; compactor note search confirmed no old `Prompt compaction note` strings remain |
| 2026-06-30 | `synthesizers/validators.py` | Treat full-output Markdown JSON fences as a recoverable wrapper instead of invalid JSON | Gemini outputs wrapped in Markdown JSON fences are normalized before JSON parsing, while genuinely malformed JSON still fails | Python compile passed; Gemini pilot 3 rejected rows replayed with T1011 passing and T1001 surfacing concrete-indicator issues |
| 2026-06-30 | `synthesizers/clients/gemini.py`, `configs/synthesis.yaml` | Move Gemini generation off Interactions text output and onto structured `models.generate_content` JSON output | Gemini receives `response_mime_type="application/json"` and a sanitized `InstructionPair` JSON schema; parsed responses are serialized before validation so new outputs should not arrive as Markdown-fenced JSON | Python compile passed; SDK config construction passed; pilot 5 `additional_properties` API error reproduced and sanitized schema conversion no longer emits `additional*` fields |
| 2026-06-30 | `synthesizers/clients/gemini.py`, `configs/synthesis.yaml` | Stop sending unsupported `thinking_level` to Gemini Flash through `models.generate_content` | Generation uses supported `thinking_budget` and does not request thought summaries for structured JSON output | Pilot 6 `Thinking level is not supported for this model` API error reproduced; Python compile and config conversion passed |
| 2026-06-30 | `synthesizers/runner.py`, `synthesizers/validators.py`, `synthesizers/schemas.py`, `synthesizers/prompt_builder.py`, `configs/synthesis.yaml`, `synthesizers/prompts/base.md` | Reduce pilot 7 validation rejects caused by recoverable model format slips, transient Gemini demand, and deterministic metadata typos | Runner uses exponential API retry/backoff with jitter, adds one validation-feedback regeneration, records validation retry metadata, and validators normalize deterministic provenance fields from `PromptRecord` | Python compile passed; `git diff --check` passed; raw corpus validation passed; one-prompt render and focused metadata-normalization validator replay passed |
| 2026-06-30 | `synthesizers/validators.py`, `synthesizers/prompts/base.md`, `synthesizers/runner.py` | Enforce consistency between `[GENERAL KNOWLEDGE]` tagging and the `grounding` field | `source_only` responses with general-knowledge tags and `source_plus_general` responses without tags are rejected; retry prompt restates the grounding contract | Python compile passed; `git diff --check` passed; focused validator cases passed |
| 2026-06-30 | `configs/synthesis.yaml`, `docs/TODO.md` | Reduce full-synthesis output cost for shortened timeline and limited generation budget | Source pair targets are budget-safe at one pair per document, preserving source breadth while reducing expected full output from about 42,048 pairs to 20,347 pairs | Pair estimate script confirmed 20,347 full pairs; pilot prompt render smoke check passed |

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
- Do not run full synthesis before pilot quality is acceptable.
- Preserve all prompt, raw output, accepted, rejected, and manifest files.
- Keep alternate teacher-model comparisons in separate labeled output directories.
