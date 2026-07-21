<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Validation And Quality</h1>

Validation is split into pure primitives and stage-specific policy wrappers.

<puml src="../diagrams/quality-activity.puml" alt="Phase 4 quality activity diagram" width="900" />

# Shared Primitives

| Module | Responsibility |
|---|---|
| `validation.reasoning` | Parse and validate canonical `<reasoning>` blocks. |
| `validation.grounding` | Check `grounding` versus `[GENERAL KNOWLEDGE]` tags. |
| `validation.indicators` | Extract concrete CVEs, hashes, IPs, domains, paths, registry paths, and event IDs. |
| `validation.mappings` | ATT&CK/ATLAS regexes and candidate suffix normalization. |
| `validation.taxonomy` | Extract valid taxonomy refs from config. |

# Reasoning Contract

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

# Phase 3 Validation

Phase 3 is focused on rejecting obvious generation failures before they become
quality inputs.

It rejects invalid JSON, wrong pair count, strict schema failures, broken
reasoning links, missing final answers, unknown taxonomy refs, malformed mapping
IDs, grounding/tag mismatches, and invented concrete indicators.

Phase 3 uses `BASIC_INDICATOR_OPTIONS`, so path and event-ID invention checks
are not as broad as Phase 4.

# Phase 4 Row Quality

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

# Quality References

`quality.references.build_quality_references` creates:

* taxonomy refs from `configs/quality.yaml`;
* ATT&CK IDs from `data/raw/.cache/enterprise-attack.json` when present;
* ATLAS IDs from `data/raw/.repos/atlas-data/dist/ATLAS.yaml` when present;
* normalized tool allowlist from `configs/quality.yaml`.

If local ATT&CK or ATLAS caches are absent, reference sets for those frameworks
are empty. There is no fallback extraction from collected `RawDocument` rows.
Any candidate with a non-empty mapping list for the missing framework is then
rejected as unknown. Cache loading errors are silently treated the same way, so
verify reference counts in the quality-run logs before trusting mapping results.

# Tool Validation

A tool is accepted when:

* its normalized name is in the allowlist; or
* the exact or normalized name appears in the source text.

Unknown tools route to review, not hard rejection.

The allowlist is static; it is not expanded from other raw tool-documentation
sources. The source-text check uses substring matching rather than token or word
boundaries, so a short normalized tool name can match inside an unrelated word.

# Indicator Validation

Phase 4 extracts concrete indicators from the instruction, response, mapping
arrays, and tool list, then compares them with the source title, URL, Markdown,
and metadata.

For `source_only`, absent concrete indicators are reject-severity. For
`source_plus_general`, they are review-severity.

# Heuristic Scores

`score_candidate` emits five 1-5 scores:

* factual accuracy;
* reasoning quality;
* operational relevance;
* specificity;
* completeness.

The total is a weighted average using `configs/quality.yaml`.

Quality scores do not directly set row status. They help rank rows for duplicate
retention and source-balance movement.

These dimensions are coarse lexical heuristics rather than a semantic rubric
grader. Factual accuracy is reduced only for reject-severity invented indicators
or grounding mismatches, and reasoning quality only for reject-severity broken
reasoning links. Review-severity versions of those problems do not reduce those
dimensions. Specificity rewards source-token overlap and concrete-artifact
counts even when a separate issue says an artifact is ungrounded. Consequently,
a score of 5 is not evidence that a row is factually correct or fully grounded.

There is no standalone validator for generic-but-nonempty evidence and no
general semantic comparison of final-answer claims with the source. Structural
reasoning failures and concrete indicators are covered; fuzzy unsupported claims
remain a manual or AI-assisted review responsibility.

# Dataset Gates

`quality.dataset.apply_dataset_gates` runs after row validation.

| Gate | Behavior |
|---|---|
| Near duplicate | Tokenizes instruction and final answer, keeps higher-scored rows, and rejects compared rows above the Jaccard threshold. Rows with fewer than eight distinctive tokens are indexed but not compared. |
| Source balance | Moves a one-pass initial surplus of low-scoring rows from overrepresented sources to review. |
| Category balance | Reports filtered rows against configured category targets; does not change status. |
| Difficulty balance | Reports filtered rows against configured difficulty targets; does not change status. |
| Taxonomy coverage | Reports covered and missing taxonomy IDs by domain; does not change status. |

The source-balance calculation derives its allowed count from the initial
filtered total and does not iterate after moving rows. Because movement reduces
the denominator, a source can still exceed `max_source_share` in the final
filtered set. Treat `final_source_distribution` as the authoritative result,
not `overrepresented` as proof that the configured share was enforced.

Near-duplicate and source-balance processing are enforcing gates. Category,
difficulty, and taxonomy results are audits only; out-of-tolerance or missing
coverage values do not fail the command.

Because the near-duplicate gate skips comparison when the current candidate has
fewer than eight distinctive tokens, even two identical short pairs can remain
eligible. If short pairs are allowed, audit them separately or change the gate
before treating the output as deduplicated.

# Output Writing

`quality.runner.write_quality_outputs` writes row outputs and distribution
counts. Only filtered rows contribute to source/category/difficulty/taxonomy
distribution counts in the manifest.

`write_spot_check_sample` samples filtered rows with the configured seed and
adds `spot_check_*` fields for manual review.

The manifest does not persist quality/task configuration fingerprints, cache
paths or hashes, or the loaded ATT&CK/ATLAS/tool reference counts. Reference
counts are present only in the INFO log. Preserve that log with released
artifacts if reference provenance matters; the manifest alone cannot reproduce
or diagnose a historical cache-backed decision.

# Configuration Validation

Quality and task YAML are loaded as untyped mappings. Phase 4 has no dedicated
configuration schema or startup range checks for weights, thresholds,
tolerances, reasoning limits, or sample sizes. Values are converted where they
are consumed. Review configuration changes carefully: for example, a Jaccard
threshold above 1 disables matches, a source share above 1 disables balancing,
and negative scoring weights distort ranking.

# Output Lifecycle

Without `--append`, `filtered.jsonl`, `review_queue.jsonl`, and `rejected.jsonl`
are removed and recreated before raw documents and the candidate input are
loaded. The sample and manifest are not cleared at that point. A subsequent
failure can therefore leave an older sample/manifest beside empty row files.

With `--append`, new rows are appended to the three existing row files, but
dataset gates consider only the current input batch. The sample and manifest are
replaced and also describe only the current batch. Existing appended rows are
not included in duplicate detection, balance calculations, distributions, or
sampling. Do not treat an append-mode directory as an aggregate quality run.

The runner returns zero after a completed pass regardless of rejection rate,
empty input, all-rejected input, category/difficulty tolerance failures, or
taxonomy gaps. Operational acceptance requires inspecting counts and audits in
the manifest.
