<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Quality Filtering</h1>

Quality filtering decides which synthesized candidates are eligible for
packaging. It is a two-pass, in-memory pipeline: first assign an independent
decision and heuristic score to every input row, then apply gates and audits
that require a view of the current batch. This page describes the architecture,
row and dataset implementation, references, scoring, output lifecycle, manual
review, and policy-change workflow.

## Architecture

<puml src="../diagrams/quality-macro.puml" alt="Macro view of quality filtering" width="900" />

Quality filtering consumes Phase 3 `accepted.jsonl` plus the complete raw corpus.
It does not call the Phase 3 validator again. Instead, both stages reuse pure
functions from `validation/` with different stage policies.

The pipeline has three decision states:

- `filtered`: no current issue; eligible for packaging;
- `review`: at least one review issue and no reject issue;
- `rejected`: at least one reject issue.

Dataset gates may change an earlier row decision. In particular, near-duplicate
processing can reject a previously filtered or review row, and source balancing
can move a filtered row to review.

### Row Decision Flow

<puml src="../diagrams/quality-row-detail.puml" alt="Detailed row-level quality decision flow" width="450" />

For each nonblank input line, the runner:

1. parses the JSON object;
2. validates it as `QualityCandidate`;
3. resolves the original `RawDocument` by `source_doc_id`;
4. validates provenance, category, taxonomy, mappings, tools, reasoning,
   grounding, and concrete indicators;
5. computes five heuristic score dimensions;
6. assigns `filtered`, `review`, or `rejected` from issue severity.

Schema and missing-source failures return immediately without a score. Other
issues are accumulated so one decision can expose multiple causes.

### Dataset Gate Flow

<puml src="../diagrams/quality-dataset-detail.puml" alt="Detailed dataset gates and reporting audits" width="350" />

After every row has a decision, `quality.dataset.apply_dataset_gates` mutates
those decisions in this fixed order:

1. near-duplicate rejection;
2. source-balance review movement;
3. category distribution audit;
4. difficulty distribution audit;
5. taxonomy coverage audit.

Only the first two are enforcing. The remaining audits are reported in the
manifest and do not change status or process exit code.

All candidate rows and decisions for the current input file are retained in
memory until dataset gates finish. This is not a streaming filter, and append
mode does not load historical output rows back into that in-memory batch.

### Component Ownership

| Component | Responsibility |
|---|---|
| `scripts/quality_filter.py` | Thin CLI, logging setup, and exit-code handoff |
| `quality/runner.py` | Configuration, input loading, two-pass orchestration, output, sampling, and manifest |
| `quality/schemas.py` | Candidate, issue, score, decision, and manifest contracts |
| `quality/references.py` | Taxonomy, ATT&CK, ATLAS, and tool reference sets |
| `quality/validators.py` | Row checks, severity, and heuristic scoring |
| `quality/dataset.py` | Near-duplicate/source gates and distribution/coverage audits |
| `validation/` | Pure reasoning, grounding, indicator, mapping, and taxonomy primitives shared with synthesis |
| `configs/quality.yaml` | Quality thresholds, weights, taxonomy, tools, balance, and sampling policy |
| `configs/task_categories.yaml` | Valid categories, category quality signals, and target distributions |

### Contracts

| Contract | Role |
|---|---|
| `QualityCandidate` | Phase 3 candidate fields required for Phase 4; unknown input fields are ignored during validation |
| `QualityIssue` | Stable code, `reject`/`review` severity, and human-readable message |
| `QualityScore` | Five 1–5 heuristic dimensions plus weighted total |
| `QualityDecision` | Mutable-in-practice status, issues, and optional score attached to an internal record |
| `QualityManifest` | Latest batch counts, filtered distributions, and dataset audits |

The runner preserves the original input mapping when writing output and adds
`quality_*` fields. Therefore synthesis run fields ignored by
`QualityCandidate` validation can still survive into filtered/review/rejected
rows.

---

## Runner And Output Lifecycle

### CLI

```bash
.venv/bin/python -m scripts.quality_filter \
  --input data/synthesized/<run>/accepted.jsonl \
  --raw-dir data/raw \
  --quality-config configs/quality.yaml \
  --task-config configs/task_categories.yaml \
  --output-dir data/quality/<run>
```

The CLI also supports `--append`. It logs at INFO and has no `--log-level`
option.

### Runner Sequence

`quality.runner.run_quality_filter`:

1. loads quality and task YAML as untyped mappings;
2. prepares or clears the three row-output files;
3. loads all raw documents and indexes them by `doc_id`;
4. builds local taxonomy, ATT&CK, ATLAS, and tool references;
5. reads and validates every nonblank candidate line into an internal
   `{row, decision, line_number}` record;
6. applies dataset gates and reporting audits to the current batch;
7. routes final rows to filtered, review, or rejected JSONL;
8. creates a deterministic manual spot-check sample from filtered rows;
9. writes `quality_manifest.json`;
10. prints counts and returns zero.

The raw-document dictionary is built without running the synthesis raw-corpus
validator. If duplicate raw `doc_id` values exist, the last loaded row silently
wins. Validate the raw corpus before Phase 4.

### Output Lifecycle

<puml src="../diagrams/quality-output-detail.puml" alt="Detailed quality output lifecycle" width="900" />

| Output | Meaning |
|---|---|
| `filtered.jsonl` | Final `filtered` rows; the only valid packaging input |
| `review_queue.jsonl` | Rows requiring adjudication before any later use |
| `rejected.jsonl` | Schema, row-policy, or dataset-gate rejects; includes input line number |
| `manual_spot_check_sample.jsonl` | Seeded sample of final filtered rows with pending review fields |
| `quality_manifest.json` | Current batch counts, filtered distributions, and dataset audits |

Without `--append`, row files are cleared before raw documents and candidates
are loaded. The sample and manifest are replaced only near the end, so an early
failure can leave old summary files beside new empty row files.

With `--append`, the three row files retain old rows, but gates, sample, and
manifest still cover only the current input batch. Do not treat an append-mode
directory as one aggregate quality run.

The command returns zero after a completed pass regardless of rejection rate,
empty/all-rejected input, distribution tolerance failures, or taxonomy gaps.
Acceptance requires inspecting logs, counts, and audits.

---

## Row Validation Implementation

### Shared Primitives

| Module | Responsibility |
|---|---|
| `validation.reasoning` | Parse and validate canonical `<reasoning>` blocks. |
| `validation.grounding` | Check `grounding` versus `[GENERAL KNOWLEDGE]` tags. |
| `validation.indicators` | Extract concrete CVEs, hashes, IPs, domains, paths, registry paths, and event IDs. |
| `validation.mappings` | ATT&CK/ATLAS regexes and candidate suffix normalization. |
| `validation.taxonomy` | Extract valid taxonomy refs from config. |

### Phase 3 And Phase 4 Boundary

Phase 3 rejects malformed model output before it becomes quality input. It
checks JSON/list shape, pair count, strict `InstructionPair`, core reasoning
links, final answer, taxonomy/mapping shapes, grounding tags, and basic invented
indicators.

Phase 4 reparses the accepted row as `QualityCandidate`, resolves its raw
source, applies stricter reasoning and broader grounding checks, scores it, and
then evaluates it against the current dataset. Shared primitives prevent parser
drift; stage wrappers own severity and policy. Phase 3 uses
`BASIC_INDICATOR_OPTIONS`, while Phase 4 enables the broader default path and
event-ID checks.

### Reasoning Contract

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

### Row Validator Order

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

### Quality References

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

### Tool Validation

A tool is accepted when:

* its normalized name is in the allowlist; or
* the exact or normalized name appears in the source text.

Unknown tools route to review, not hard rejection.

The allowlist is static; it is not expanded from other raw tool-documentation
sources. The source-text check uses substring matching rather than token or word
boundaries, so a short normalized tool name can match inside an unrelated word.

### Indicator Validation

Phase 4 extracts concrete indicators from the instruction, response, mapping
arrays, and tool list, then compares them with the source title, URL, Markdown,
and metadata.

For `source_only`, absent concrete indicators are reject-severity. For
`source_plus_general`, they are review-severity.

### Heuristic Scores

`score_candidate` emits five 1-5 scores:

* factual accuracy;
* reasoning quality;
* operational relevance;
* specificity;
* completeness.

The total is a weighted average using `configs/quality.yaml`.

Quality scores do not directly set row status. They help rank rows for duplicate
retention and source-balance movement.

| Dimension | Implemented signal |
|---|---|
| Factual accuracy | Starts at 5; reject-severity invented indicators force 1 and grounding mismatch forces 2 |
| Reasoning quality | Starts at 5; reject-severity `reasoning_links_invalid` forces 1 |
| Operational relevance | Counts category description/quality terms and configured operational verbs in the final answer, then subtracts configured generic-phrase penalties |
| Specificity | Measures distinctive token overlap with the raw source and adds credit for concrete indicators |
| Completeness | Penalizes short final answers, missing caveats, and responses above preferred/long/maximum word thresholds |

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

---

## Dataset Gate Implementation

### Gates And Audits

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

### Output Writing And Sampling

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

---

## Configuration And Review

### Configuration Validation

Quality and task YAML are loaded as untyped mappings. Phase 4 has no dedicated
configuration schema or startup range checks for weights, thresholds,
tolerances, reasoning limits, or sample sizes. Values are converted where they
are consumed. Review configuration changes carefully: for example, a Jaccard
threshold above 1 disables matches, a source share above 1 disables balancing,
and negative scoring weights distort ranking.

### Decision Rubric

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

### Coverage Review

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

---

## Changing Quality Policy

Start with the narrowest owner:

| Intended change | Primary owner | Coupled review |
|---|---|---|
| Reasoning parser or link grammar | `validation/reasoning.py` | Phase 3 and Phase 4 options, prompt examples |
| Grounding/tag interpretation | `validation/grounding.py` | Synthesis acceptance and row severity |
| Concrete-indicator extraction | `validation/indicators.py` | Phase-specific options and source normalization |
| ATT&CK/ATLAS syntax normalization | `validation/mappings.py` | Local reference loading and candidate suffix behavior |
| Taxonomy ID validity | `configs/quality.yaml`, `validation/taxonomy.py` | Prompt taxonomy suggestions and coverage audit |
| ATT&CK/ATLAS reference sources | `quality/references.py` | Collector cache layout, logged counts, reproducibility |
| Tool acceptance | `configs/quality.yaml`, `quality/references.py`, `quality/validators.py` | Normalization and source substring behavior |
| Row rule, severity, or issue code | `quality/validators.py` | Accepted/review/rejected fixtures and scorer effects |
| Heuristic dimension or weight | `quality/validators.py`, `configs/quality.yaml` | Duplicate/source ranking and manual rubric |
| Near-duplicate behavior | `quality/dataset.py`, `configs/quality.yaml` | Short-row behavior and retained-row ordering |
| Source balance | `quality/dataset.py`, `configs/quality.yaml` | Final denominator and review queue |
| Category/difficulty audit | `quality/dataset.py`, `configs/task_categories.yaml` | Non-enforcing manifest semantics |
| Sampling, files, or manifest | `quality/runner.py`, `quality/schemas.py` | Append/failure lifecycle and packaging input |

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
