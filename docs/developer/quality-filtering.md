<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Quality Filtering</h1>

Phase 4 decides which synthesized candidates are eligible for packaging. This
page owns shared validation boundaries, row decisions, scoring, dataset gates,
manual review, coverage audits, outputs, and quality-policy changes.

# Visual Overview

## Macro View

<puml src="../diagrams/quality-macro.puml" alt="Macro view of quality filtering" width="900" />

## Row Decision Detail

<puml src="../diagrams/quality-row-detail.puml" alt="Detailed row-level quality decision flow" width="450" />

## Dataset Gates Detail

<puml src="../diagrams/quality-dataset-detail.puml" alt="Detailed dataset gates and reporting audits" width="350" />

## Output Lifecycle Detail

<puml src="../diagrams/quality-output-detail.puml" alt="Detailed quality output lifecycle" width="900" />

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

# Running Phase 4

```bash
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/<run>/accepted.jsonl \
  --raw-dir data/raw \
  --output-dir data/quality/<run>
```

Use a fresh output directory. The CLI logs at INFO and has no `--log-level`
option. Preserve the log because loaded ATT&CK/ATLAS reference counts are not
stored in the manifest.

# Decision Rubric

| State | Meaning |
|---|---|
| `filtered` | No row-level issue; eligible for dataset gates and packaging |
| `review` | At least one review-severity issue and no reject issue |
| `rejected` | At least one reject-severity issue |

The five heuristic dimensions are factual accuracy, reasoning quality,
operational relevance, specificity, and completeness. The configured weights
are 25%, 25%, 20%, 15%, and 15%. Manual reviewers use this interpretation:

| Dimension | Low | Mid | High |
|---|---|---|---|
| Factual accuracy | Unsupported or contradicted | Mostly supported, minor ambiguity | Fully grounded |
| Reasoning quality | Broken or circular | Mostly coherent | Clear evidence-to-conclusion chain |
| Operational relevance | Academic or vague | Some useful next steps | Directly useful to an analyst |
| Specificity | Generic | Some source detail | Specific without invention |
| Completeness | Missing key fields/caveats | Adequate | Complete and calibrated |

The implemented scorer is lexical and does not automate this human rubric.
Scores rank rows for duplicate retention and source balancing; they do not prove
correctness.

Manual reviewers should ask:

1. Is every concrete claim supported by source evidence?
2. Would the answer help an incident responder decide or act?
3. Does it avoid declaring compromise or attribution without corroboration?
4. Are caveats specific rather than boilerplate?
5. Is the evidence-to-conclusion chain auditable?
6. Is the pair redundant with another example?

Common stable issue codes include `schema_invalid`, `source_missing`,
`source_mismatch`, `category_invalid`, `taxonomy_invalid`,
`attack_id_invalid`, `atlas_id_invalid`, `mapping_inconsistency`,
`reasoning_links_invalid`, `reasoning_too_long`, `tool_name_unknown`,
`grounding_mismatch`, `invented_indicator`, `duplicate_or_near_duplicate`, and
`source_overrepresented`. Add a stable code whenever a new decision must be
audited over time.

# Coverage Review

Training coverage is evaluated from collection through packaging; it is not the
same as benchmark coverage.

| Input | Coverage signal |
|---|---|
| Collection manifest | Which collectors ran and raw volume |
| Synthesis accepted/rejected rows | Generation and rejection pressure by source/task |
| Quality manifest and review queue | Filtered distributions, taxonomy gaps, and review pressure |
| Packaging manifest | Rows that reached isolated splits and response-style mix |
| `configs/task_categories.yaml` | Intended task and difficulty distributions |
| `configs/quality.yaml` | Valid taxonomy and balance policy |

Use `strong`, `moderate`, `thin`, and `absent` consistently. Review source
families, task categories, difficulty, taxonomy IDs, ATT&CK/ATLAS mapping health,
review pressure, and rejection pressure. Do not infer model behavior from
training coverage, or training coverage from a judge score.

Common weak areas include cloud control-plane and identity investigations,
SaaS/file-storage forensics, realistic event-log corpora, malware-analysis
workflows, and real AI/LLM incident reports. Record run-specific findings in a
run report or [Current State](../current-state/index.md), not in this guide.

# Changing Quality Policy

`configs/quality.yaml` owns taxonomy coverage groups, scoring weights, generic
penalties, operational verbs, reasoning bounds, deduplication, source balance,
distribution tolerances, spot-check sampling, and the tool allowlist.
`configs/task_categories.yaml` owns category quality signals and target
distributions.

The YAML is loaded as an untyped mapping. Validate that weights are
non-negative, thresholds and shares are within their intended 0–1 range,
reasoning bounds are coherent, and sample sizes are non-negative. Numeric but
invalid values can silently weaken a gate.

Extension rules:

- reusable parsing/checking belongs in `validation/`;
- Phase 3 generation acceptance belongs in `synthesizers/validators.py`;
- Phase 4 row policy belongs in `quality/validators.py`;
- dataset-wide gates belong in `quality/dataset.py`;
- decision codes and severity must remain stable and documented;
- every changed rule needs accepted, review, and rejected fixtures where
  applicable.

Validation ladder:

1. run focused shared-primitive and row-validator tests;
2. validate a fixture containing every affected severity path;
3. run Phase 4 into a fresh directory on a representative candidate set;
4. inspect every decision and score;
5. inspect reference counts, duplicates, final source shares, distributions,
   taxonomy coverage, and the spot-check sample;
6. run the full input only after sample behavior is accepted.

Only `filtered.jsonl` is a valid input to [Packaging](packaging.md).
