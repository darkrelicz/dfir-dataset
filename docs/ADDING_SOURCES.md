# Adding Sources

## Purpose

Use this guide when adding a new collector to the dataset factory. A new source is ready only when it can be collected reproducibly, normalized into `RawDocument`, validated, mapped to synthesis profiles, and documented in the coverage map.

## Source Intake Checklist

- [ ] Source is legally usable for local dataset generation.
- [ ] Source license and attribution notes are recorded.
- [ ] Source has stable access or a pinned clone/cache strategy.
- [ ] Source content is relevant to one or more current task categories.
- [ ] Source content is rich enough for the planned pairs per document.
- [ ] Thin sources are capped to avoid hallucinated details.
- [ ] Expected output volume is estimated.

## Collector Naming

Use a short source key that stays stable across runs.

- Python module: `collectors/<source_key>.py`
- Raw output path: `data/raw/<source_key>/<source_key>.jsonl`
- Config key: `configs/collection.yaml` -> `<source_key>`
- Synthesis pair target: `configs/synthesis.yaml` -> `generation.pairs_per_document.<source_key>`
- Source profile: `configs/source_profiles.yaml` -> `source_profiles.<source_key>`

## RawDocument Contract

Each collector must emit records matching `collectors.schemas.RawDocument`:

```json
{
  "doc_id": "stable-source-specific-id",
  "source": "source_key",
  "source_url": "https://example.org/source",
  "title": "Human-readable title",
  "date_collected": "YYYY-MM-DDTHH:MM:SSZ",
  "date_published": null,
  "content_type": "specific_content_label",
  "content_markdown": "Normalized source content",
  "metadata": {},
  "word_count": 0
}
```

## Collector Implementation Steps

1. Add source settings to `configs/collection.yaml`.
2. Create `collectors/<source_key>.py`.
3. Reuse `collectors.base.BaseCollector`.
4. Normalize each logical source item into one `RawDocument`.
5. Use stable `doc_id` values that do not depend on run order.
6. Preserve useful upstream metadata in `metadata`.
7. Keep `content_markdown` readable and grounded in original source fields.
8. Add the collector to `scripts/collect_all.py`.
9. Run the collector alone.
10. Run all collectors and validate the raw corpus.

## Content Type Guidance

Choose precise `content_type` labels. Add content-type prompt overrides only when broad source-type guidance is not enough.

| Source Shape | Suggested `source_type` | Example `content_type` |
|---|---|---|
| Technique/procedure descriptions | `ttp_description` | `technique_definition`, `atomic_test` |
| Detection rules | `detection_rule` | `sigma_rule`, `hayabusa_rule` |
| Artifact definitions | `artifact_definition` | `artifact_definition`, `event_dictionary` |
| Tool docs/artifacts | `tool_documentation` | `tool_plugin`, `tool_module` |
| Vulnerability catalogs | `vulnerability_catalog` | `kev_entry`, `advisory` |
| Practitioner workflows | `practitioner_workflow` | `case_study`, `workflow` |
| Abuse databases | `abuse_database` | `lolbas_windows_lolbin`, `gtfobins_linux_abuse_function` |

## Synthesis Profile Steps

Update `configs/source_profiles.yaml`:

```yaml
source_profiles:
  new_source_key:
    source_type: ttp_description
    prompt_template: ttp_description.md
    categories:
      - ttp_identification
      - triage_and_hunting
      - detection_engineering
    thin_source: false
```

Update `configs/synthesis.yaml`:

```yaml
generation:
  pairs_per_document:
    new_source_key: 2
```

If the source has unique behavior, add a content-type profile:

```yaml
content_type_profiles:
  new_content_type:
    prompt_template: new_content_type.md
    max_pairs: 2
    thin_source: true
```

## Validation Commands

```bash
.venv/bin/python -m scripts.collect_all --source new_source_key
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
.venv/bin/python -m scripts.synthesize render-prompts --mode pilot --source new_source_key --output-dir data/synthesized/dry_run_new_source
```

## Documentation Updates

- [ ] `docs/ARCHITECTURE.md`: add source to pipeline layout or generated state.
- [ ] `docs/DECISIONS.md`: record any durable source-specific decision.
- [ ] `docs/COVERAGE_MAP.md`: add source coverage and gaps.
- [ ] `docs/PROMPT_GUIDE.md`: document prompt behavior if new templates were added.
- [ ] `docs/HANDOVER.md`: mention source status if it affects current handover.

## New Source Review

| Question | Answer |
|---|---|
| What task categories does this source improve? |  |
| What taxonomy IDs does this source support? |  |
| Is the source rich or thin? |  |
| What pair cap is justified? |  |
| What hallucination risk does this source introduce? |  |
| What should the pilot manually inspect? |  |
