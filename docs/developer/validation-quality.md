# Validation And Quality

Validation is split into pure primitives and stage-specific policy wrappers.

<puml src="../diagrams/quality-activity.puml" alt="Phase 4 quality activity diagram" width="900" />

## Shared Primitives

| Module | Responsibility |
|---|---|
| `validation.reasoning` | Parse and validate canonical `<reasoning>` blocks. |
| `validation.grounding` | Check `grounding` versus `[GENERAL KNOWLEDGE]` tags. |
| `validation.indicators` | Extract concrete CVEs, hashes, IPs, domains, paths, registry paths, and event IDs. |
| `validation.mappings` | ATT&CK/ATLAS regexes and candidate suffix normalization. |
| `validation.taxonomy` | Extract valid taxonomy refs from config. |

## Reasoning Contract

The canonical response format is:

```text
<reasoning>
E1: Source-grounded evidence.
A1 [uses E1]: Analysis of the evidence.
C1 [uses E1,A1] Confidence: medium. Conclusion.
CV1 [applies_to C1]: Caveat or corroboration need.
</reasoning>

Final practitioner-ready answer.
```

Phase 4 runs stricter options than Phase 3:

* response begins with `<reasoning>`;
* opening and closing tags are on their own lines;
* only known reasoning line formats are allowed inside the block;
* conclusions must include confidence;
* final answer is required;
* min/max reasoning step counts come from `configs/quality.yaml`.

## Phase 3 Validation

Phase 3 is focused on rejecting obvious generation failures before they become
quality inputs.

It rejects invalid JSON, wrong pair count, strict schema failures, broken
reasoning links, missing final answers, unknown taxonomy refs, malformed mapping
IDs, grounding/tag mismatches, and invented concrete indicators.

Phase 3 uses `BASIC_INDICATOR_OPTIONS`, so path and event-ID invention checks
are not as broad as Phase 4.

## Phase 4 Row Quality

`quality.validators.validate_row_quality` performs:

1. `QualityCandidate` parsing.
2. raw source lookup by `source_doc_id`;
3. source match check;
4. category validation;
5. taxonomy validation;
6. mapping ID validation;
7. tool validation;
8. reasoning validation;
9. grounding validation;
10. source-grounding indicator validation;
11. heuristic scoring;
12. status decision.

Reject-severity issues produce `rejected`. Review-severity issues produce
`review`. No issues produces `filtered`.

## Quality References

`quality.references.build_quality_references` creates:

* taxonomy refs from `configs/quality.yaml`;
* ATT&CK IDs from `data/raw/.cache/enterprise-attack.json` when present;
* ATLAS IDs from `data/raw/.repos/atlas-data/dist/ATLAS.yaml` when present;
* normalized tool allowlist from `configs/quality.yaml`.

If local ATT&CK or ATLAS caches are absent, reference sets for those frameworks
will be smaller, which can affect mapping validation.

## Tool Validation

A tool is accepted when:

* its normalized name is in the allowlist; or
* the exact or normalized name appears in the source text.

Unknown tools route to review, not hard rejection.

## Indicator Validation

Phase 4 extracts concrete indicators from the instruction, response, mapping
arrays, and tool list, then compares them with the source title, URL, Markdown,
and metadata.

For `source_only`, absent concrete indicators are reject-severity. For
`source_plus_general`, they are review-severity.

## Heuristic Scores

`score_candidate` emits five 1-5 scores:

* factual accuracy;
* reasoning quality;
* operational relevance;
* specificity;
* completeness.

The total is a weighted average using `configs/quality.yaml`.

Quality scores do not directly set row status. They help rank rows for duplicate
retention and source-balance movement.

## Dataset Gates

`quality.dataset.apply_dataset_gates` runs after row validation.

| Gate | Behavior |
|---|---|
| Near duplicate | Tokenizes instruction and final answer, keeps higher-scored rows, rejects rows above Jaccard threshold. |
| Source balance | Moves low-scoring rows from overrepresented sources to review. |
| Category balance | Audits filtered rows against configured category targets. |
| Difficulty balance | Audits filtered rows against configured difficulty targets. |
| Taxonomy coverage | Reports covered and missing taxonomy IDs by domain. |

## Output Writing

`quality.runner.write_quality_outputs` writes row outputs and distribution
counts. Only filtered rows contribute to source/category/difficulty/taxonomy
distribution counts in the manifest.

`write_spot_check_sample` samples filtered rows with the configured seed and
adds `spot_check_*` fields for manual review.
