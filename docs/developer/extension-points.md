<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Extension Points</h1>

Use this page when adding sources, prompt behavior, validators, or packaging
formats.

# Add A New Source

Use [Adding Sources](adding-sources.md). It is the canonical intake,
implementation, synthesis-profile, validation, and review checklist. Collector
internals and cache behavior are documented in [Collectors](collectors.md) and
[Source Internals](source-guide.md).

# Add A Prompt Template

Use a new prompt template only when existing source-type or content-type
instructions are not enough.

Possible locations:

* `synthesizers/prompts/source_types/<name>.md`
* `synthesizers/prompts/content_types/<name>.md`
* `synthesizers/prompts/categories/<name>.md`

Then update the relevant YAML config.

`synthesizers.prompt_policy.load_prompt_policy` will fail early if the config
references a missing template.

# Add A Prompt Compactor

Create:

```text
synthesizers/prompts/compactors/<source>_compactor.py
```

Expose:

```python
def compact_for_prompt(doc: RawDocument, content: str) -> str:
    ...
```

Use compactors to remove repeated or low-priority source blocks while preserving
evidence the model can cite. Do not mutate Phase 2 raw documents.

If shared `max_source_chars` truncation would harm the source, set:

```python
compact_for_prompt.skip_source_truncation = True
```

Use that sparingly. Velociraptor does it because full VQL bodies are the
training signal.

# Add A Validator

Prefer putting reusable parsing/checking logic in `validation/` when both Phase
3 and Phase 4 can use it.

Use stage wrappers for policy:

* Phase 3 generated-output policy belongs in `synthesizers/validators.py`.
* Phase 4 row/dataset policy belongs in `quality/validators.py` or
  `quality/dataset.py`.

Add stable issue codes when a quality result needs to be audited later.

# Tune Quality Scoring

Start in config:

* `configs/quality.yaml` for weights, generic penalties, operational verbs,
  reasoning bounds, dedupe, balance, and tool allowlist.
* `configs/task_categories.yaml` for category `quality_signals`.

Change Python only when config cannot express the behavior.

# Add Packaging Format

The current packager supports `messages_jsonl` behavior directly in
`dataset_packaging.runner`.

If adding another format:

1. keep split grouping by `source_doc_id`;
2. preserve quality/source/prompt metadata;
3. write split counts and overlap to `PackagingManifest`;
4. add or update the relevant model-specific packaging config;
5. update this guides site and durable state docs.

# Update Documentation

After structural changes, update:

* `project_state/PROJECT_BRIEF.md` for product intent or phase state;
* `docs/developer/architecture.md` for implementation structure;
* `project_state/DECISIONS.md` for durable choices;
* `project_state/TODO.md` for active next work;
* the relevant canonical page in this `docs/` source for stable
  user/developer details.
