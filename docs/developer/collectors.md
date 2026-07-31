<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Collectors</h1>

Collectors are the ingestion boundary of the dataset factory. They acquire
public DFIR/security sources and normalize each logical source item into a
complete, traceable `RawDocument`. This page describes the collection
architecture, framework implementation, concrete source adapters, cache policy,
extension workflow, and validation.

## Architecture

<puml src="../diagrams/collectors-macro.puml" alt="Macro view of source collection" width="650" />

Collection is adapter-based. `scripts.collect_all` selects and constructs a
concrete collector from `configs/collection.yaml`. The collector acquires or
reuses upstream data, parses source-specific structures, creates validated
`RawDocument` objects, replaces its source JSONL, and returns a
`CollectionManifest`. The CLI combines those entries into the invocation
manifest.

The boundary is intentionally one-way: collectors preserve evidence and
provenance, but do not assign synthesis tasks, compact prompt content, score
quality, or create model-specific formats.

### Run And Data Flow

<puml src="../diagrams/collectors-run-detail.puml" alt="Detailed collection run and cache sequence" width="1000" />

One collection invocation follows this path:

1. `scripts.collect_all` loads the untyped `sources` mapping from
   `configs/collection.yaml`.
2. Its explicit `collector_map` binds a source key to a concrete class and that
   source's configuration mapping.
3. The CLI runs the selected source or all registered sources sequentially.
4. The collector downloads a feed or calls `_clone_repo()` to populate/reuse a
   local cache.
5. Source-specific code parses upstream objects and chooses the logical
   document boundary.
6. Each logical item is rendered as Markdown, assigned stable identity and
   provenance, and constructed as a Pydantic `RawDocument`.
7. `_write_documents()` replaces
   `data/raw/<source_key>/<source_key>.jsonl`.
8. The collector reports one manifest entry; the CLI replaces
   `data/raw/collection_manifest.json` with entries from this invocation.

There is no shared streaming pipeline or plugin discovery. Each collector holds
its parsed documents in memory, and registration is a code change in
`scripts/collect_all.py`.

### Collector Families

<puml src="../diagrams/collectors-families-detail.puml" alt="Detailed collector families and BaseCollector inheritance" width="1000" />

The diagram groups sources by domain use, while their implementation strategies
fall into these acquisition and parsing families:

| Family | Acquisition | Parsing approach | Examples |
|---|---|---|---|
| Direct HTTP data | JSON/STIX request | Feed-specific object traversal and optional grouping | ATT&CK, CISA KEV |
| Git-backed structured data | Reused local clone | YAML/JSON traversal with source-specific filtering | Sigma, Atomic Red Team, CSAF, KAPE, Hayabusa, ForensicArtifacts, HijackLibs, LOLDrivers, OSSEM |
| Git-backed code or documentation | Reused local clone | Python AST, RST, Markdown/frontmatter, or embedded YAML parsing | Volatility 3, Velociraptor, Cybersecurity Skills |
| Multi-source or in-repository model | One or more clones | Cross-file normalization or upstream parser/model loading | LOLBAS/GTFOBins, MITRE ATLAS |

All concrete collectors inherit `BaseCollector`, but the base class is
deliberately small. Acquisition details, parsing, document boundaries, identity,
metadata, filtering, and error recovery remain source-specific.

---

## Contracts And Configuration

### `RawDocument`

`collectors.schemas.RawDocument` contains:

| Field | Purpose |
|---|---|
| `doc_id` | Stable source-specific ID independent of run order |
| `source` | Stable source key used by downstream profiles |
| `source_url` | Public upstream or documentation URL |
| `title` | Human-readable title |
| `date_collected` / `date_published` | Collection and optional publication dates |
| `content_type` | Precise downstream policy label |
| `content_markdown` | Complete normalized source evidence |
| `metadata` | Useful source-specific structured fields |
| `word_count` | Count produced by `utils.text.count_words` |

Pydantic validates field types when a collector constructs a row. The schema
does not itself enforce non-empty content, recompute `word_count`, validate
cross-source ID uniqueness, or constrain `content_type`; collectors and
downstream validation own those checks.

Do not truncate source evidence at collection time. Avoid duplicating the entire
Markdown body in `metadata`, but preserve structure that prompts, validation, or
audits may need.

### `CollectionManifest`

`collectors.schemas.CollectionManifest` records the collector class/version,
upstream URL, collection time, document count, errors, warnings, and duration.
It describes one collector execution. It does not fingerprint input bytes,
configuration, cache revision, or output content.

### Output Layout

| Path | Contents and lifecycle |
|---|---|
| `data/raw/<source_key>/<source_key>.jsonl` | Canonical source rows; replaced by that collector |
| `data/raw/collection_manifest.json` | JSON list of manifest entries from the latest CLI invocation |
| `data/raw/.repos/<source>/` | Reused Git clones; generated and ignored by Git |
| `data/raw/.cache/` | Reused non-Git downloads such as ATT&CK STIX; generated and ignored by Git |

The source key must agree across CLI registration, configuration, output
directory, every row's `source`, and `configs/source_profiles.yaml`. The
framework does not enforce that agreement centrally.

### Configuration Boundary

`configs/collection.yaml` owns upstream URLs, clone/cache paths, output
locations, and collector-specific filters. Configuration is passed to
constructors as an untyped mapping; each concrete `__init__` reads its required
keys directly and supplies local defaults for optional keys.

`configs/source_profiles.yaml` is not read during collection. It owns the later
mapping from the stable `source` and `content_type` values to synthesis
categories, templates, pair caps, thin-source policy, and sampling targets. A
collector change that introduces either value must update that downstream
policy.

---

## Framework Implementation

### `BaseCollector`

`collectors.base.BaseCollector` defines the minimal interface:

- `collect() -> int` acquires, parses, normalizes, and writes the source;
- `manifest() -> CollectionManifest` reports the completed collector state;
- `_clone_repo()` creates or reuses a shallow/full Git clone;
- `_write_documents()` serializes validated rows with `jsonlines`;
- `_parse_datetime()` parses ISO timestamps, including trailing `Z`.

The base class does not implement a constructor or own common run state.
Concrete collectors currently repeat `config`, source/output paths, `errors`,
`warnings`, `duration`, and `doc_count` initialization. They also decide whether
an item-level exception becomes an error, warning, skipped row, or fatal early
return.

`_clone_repo()` is cache reuse, not synchronization. If the clone path is
non-empty, collection uses it as-is: the helper does not verify that it is a Git
repository and does not fetch, pull, or record its revision. Most source URLs in
raw documents point at a default branch rather than the exact collected commit.

`_write_documents()` opens the canonical source JSONL in write mode. It does not
write to a temporary file and atomically replace the destination, so an
interrupted write can leave partial output.

### Concrete Collector Lifecycle

Although parsing varies, a concrete collector normally implements this shape:

1. `__init__` resolves required config keys and initializes run state.
2. `collect()` starts a timer and acquires the upstream input.
3. It validates the expected upstream root, directory, or feed shape.
4. It iterates deterministically where practical, catching item-level parse
   failures without discarding unrelated valid items.
5. A source-specific renderer builds readable Markdown; metadata preserves
   useful machine-readable structure.
6. It constructs `RawDocument` with a stable `doc_id`, stable `source`, precise
   `content_type`, source URL, dates, and `count_words(markdown)`.
7. `_write_documents()` replaces the canonical source JSONL and updates
   `doc_count` and duration.
8. `manifest()` projects that local state into `CollectionManifest`.

The logical document boundary is part of the downstream contract. Most
collectors emit one row per upstream object. Intentional exceptions include one
row per Atomic test, per Volatility plugin or selected document, per KAPE
target/module, and per CISA KEV vendor group.

### Shared Utilities

| Utility | Collector use |
|---|---|
| `utils.text.to_markdown` | Normalize rendered Markdown |
| `utils.text.count_words` | Populate `RawDocument.word_count` |
| `utils.text.slugify` and list helpers | Build stable IDs and normalize repeated fields |
| `utils.git.github_blob_url` | Build source-file URLs, usually against a configured branch |
| `utils.git.current_commit` | Resolve a collected commit where supported |
| `utils.markdown.parse_yaml_frontmatter` | Parse Markdown-backed source metadata |
| `utils.io.load_yaml` | Load structured source/config files with repository conventions |

Prefer these utilities over source-local copies when their behavior matches.
Keep source-specific parsing in its collector rather than making shared helpers
understand upstream-specific schemas.

### CLI Orchestration

`scripts.collect_all`:

1. loads `configs/collection.yaml`;
2. maps each source key to a collector class;
3. supports `--list` and `--source`;
4. runs collectors sequentially;
5. writes `data/raw/collection_manifest.json`;
6. prints a Rich summary table.

`--source` changes only which registered entry runs. There is no CLI option for
an alternate collection config or output root, so isolated experiments require
a deliberate config change or equivalent controlled environment.

The combined manifest describes the current CLI invocation, not everything that
may exist under `data/raw/`. A single-source run therefore replaces the manifest
with one entry. The CLI also currently exits successfully after unknown-source
selection, collector-reported errors, or caught fatal exceptions. Treat the
manifest error fields and raw-corpus validation as required success checks.

`--list` reports available source keys, but it does not instantiate collectors, inspect
caches, contact upstreams, or validate collector-specific values. Use a
single-source collection in an isolated output/cache setup when a real preflight
is required.

### Failure And Output Semantics

| Condition | Current behavior |
|---|---|
| Unknown `--source` | Prints available keys and returns success without a manifest |
| Missing config required by one constructor | Caught by the per-source CLI wrapper and written as a fatal result |
| Acquisition/root-shape failure handled by collector | Usually appended to `errors`, then returns zero documents |
| Item-level parse failure | Source-specific; commonly records an error/warning and continues |
| Source output write | Replaces the source JSONL directly |
| Combined manifest write | Replaces the manifest with this invocation's entries |
| Collector errors present | CLI still normally exits zero |

Acceptance therefore requires inspecting the manifest and output, not only the
process exit status.

---

## Source Implementations

The source adapters share the lifecycle above but use different upstream
libraries and selection rules:

| Collector | Module | Key implementation strategy |
|---|---|---|
| `MitreAttackCollector` | `collectors/mitre_attack.py` | Cache STIX JSON, then use `mitreattack-python` to traverse techniques and related procedures, mitigations, and detections |
| `SigmaRulesCollector` | `collectors/sigma_rules.py` | Parse rule YAML, apply ordered level filtering, and extract ATT&CK/tactic tags |
| `AtomicRedTeamCollector` | `collectors/atomic_red_team.py` | Walk technique YAML and emit each atomic test separately |
| `CISAAdvisoriesCollector` | `collectors/cisa_advisories.py` | Walk CSAF JSON and flatten notes, vulnerabilities, remediation, and references per advisory |
| `Volatility3DocsCollector` | `collectors/volatility3_docs.py` | Use Python AST for plugin classes/requirements/output columns and parse selected RST without importing plugins |
| `MitreAtlasCollector` | `collectors/mitre_atlas.py` | Load the upstream v6 export model in-process and build relationship indexes for techniques, mitigations, and cases |
| `CISAKEVCollector` | `collectors/cisa_kev.py` | Download the live JSON feed and group vulnerabilities by configured vendor field |
| `KapeFilesCollector` | `collectors/kape_files.py` | Parse `.tkape` targets and `.mkape` modules as distinct content types |
| `HayabusaRulesCollector` | `collectors/hayabusa_rules.py` | Parse multi-document rule YAML, filter levels, and suppress duplicate IDs |
| `LOLBASGTFOBinsCollector` | `collectors/lolbas_gtfobins.py` | Normalize two repositories into Windows LOLBin and Linux function/alias content types |
| `ForensicArtifactsCollector` | `collectors/forensic_artifacts.py` | Use the `artifacts` library reader and typed artifact/source models |
| `VelociraptorArtifactsCollector` | `collectors/velociraptor_artifacts.py` | Parse generated Markdown/frontmatter and extract embedded HTML-escaped YAML/VQL |
| `HijackLibsCollector` | `collectors/hijacklibs.py` | Normalize DLL hijack YAML, vulnerable executables, conditions, hashes, and paths |
| `LOLDriversCollector` | `collectors/loldrivers.py` | Normalize driver YAML and nested samples, hashes, detections, CVEs, and resources |
| `OSSEMDataDictsCollector` | `collectors/ossem_data_dicts.py` | Apply path filters, group competing event dictionaries, and retain the highest-scored candidate |
| `CybersecSkillsCollector` | `collectors/cybersec_skills.py` | Parse YAML frontmatter plus Markdown and exclude bodies below the configured token threshold |

### `MitreAttackCollector`

Input: Enterprise ATT&CK STIX JSON from the configured URL/cache path.

Output:

* one `technique_definition` document per ATT&CK technique;
* `doc_id`: `mitre-attack-<TID>`;
* markdown includes tactics, platforms, description, procedures, mitigations,
  and detection strategies when present;
* metadata includes external references, parent technique, and contributors.

### `SigmaRulesCollector`

Input: `SigmaHQ/sigma` git repository under `rules/`.

Output:

* one `sigma_rule` document per rule at or above `min_rule_level`;
* `doc_id`: `sigma-<rule id>`;
* markdown includes logsource, detection YAML, tags, false positives, and
  references;
* metadata includes level, status, logsource fields, ATT&CK IDs, tactic tags,
  false positives, and author.

### `AtomicRedTeamCollector`

Input: `redcanaryco/atomic-red-team` `atomics/` YAML files.

Output:

* one `atomic_test` document per atomic test;
* `doc_id`: `atomic-rt-<auto_generated_guid>`;
* markdown includes input arguments, dependencies, executor, command, and cleanup
  command;
* metadata includes technique ID, test GUID/index, platforms, executor,
  elevation, cleanup, and dependency flags.

### `CISAAdvisoriesCollector`

Input: `cisagov/CSAF` `csaf_files/**/*.json`.

Output:

* one `threat_advisory` document per CSAF advisory;
* `doc_id`: `cisa-<tracking id lowercased>`;
* markdown includes document notes, vulnerabilities, CVSS/CWE details,
  remediation, and references;
* metadata includes advisory ID, category, IT/OT type, CVEs, publisher, and
  version.

### `Volatility3DocsCollector`

Input: `volatilityfoundation/volatility3`.

Output:

* `tool_plugin` documents parsed from plugin classes;
* `tool_documentation` documents from selected RST docs;
* plugin markdown includes class, platform, docstring, output columns, and user
  options;
* metadata includes plugin name, module path, OS platform, requirements, output
  columns, and source commit.

The collector uses Python AST parsing. It does not import arbitrary plugin
modules to inspect them.

### `MitreAtlasCollector`

Input: `mitre-atlas/atlas-data` latest v6 YAML from `dist/manifest.yaml`.

Output:

* `technique_definition` documents for ATLAS techniques;
* `mitigation` documents for ATLAS mitigations;
* `case_study` documents for ATLAS cases;
* metadata includes ATLAS ID, UUID, collection/format versions, source file,
  source commit, modified date, and object-specific relationships.

The collector loads the repo's parser package in-process without importing the
full API/database stack.

### `CISAKEVCollector`

Input: CISA KEV JSON feed.

Output:

* one `vulnerability_catalog` document per vendor group;
* `doc_id`: `kev-<vendor slug>`;
* markdown includes vendor/product summary, vulnerability table, and details;
* metadata includes products, CVE IDs/count, ransomware-linked count, and
  catalog version.

### `KapeFilesCollector`

Input: `EricZimmerman/KapeFiles`.

Output:

* `artifact_definition` documents from `.tkape` targets;
* `tool_module` documents from `.mkape` modules;
* disabled KAPE files under `!Disabled` paths are skipped;
* metadata records target paths/categories or module tools/processors.

### `HayabusaRulesCollector`

Input: `Yamato-Security/hayabusa-rules`.

Output:

* one `hayabusa_rule` document per YAML rule document;
* skips non-rule YAML documents and duplicate IDs;
* markdown includes logsource, detection YAML, alert details, tags, false
  positives, samples, and references;
* metadata includes rule level, status, logsource fields, tags, references,
  author, modified date, rule type, and details format.

### `LOLBASGTFOBinsCollector`

Input:

* `LOLBAS-Project/LOLBAS`;
* `GTFOBins/GTFOBins.github.io`.

Output:

* `lolbas_windows_lolbin` for LOLBAS entries;
* `gtfobins_linux_abuse_function` for GTFOBins entries with functions;
* `gtfobins_linux_alias` for thin alias entries;
* metadata captures binary names, platforms, functions/categories, MITRE IDs,
  command counts, full paths, detection details, contexts, and related fields.

### `ForensicArtifactsCollector`

Input: `ForensicArtifacts/artifacts` YAML data.

Output:

* one `artifact_definition` document per artifact definition;
* markdown includes supported OS, description, source types, paths, registry
  keys/values, WMI queries, commands, artifact groups, and references;
* metadata includes artifact name, supported OS, source types/count, file paths,
  and registry keys.

### `VelociraptorArtifactsCollector`

Input: generated Velociraptor artifact reference Markdown pages.

Output:

* Velociraptor-specific content types such as `velociraptor_client_artifact`,
  `velociraptor_event_artifact`, `velociraptor_vql_artifact`, and related
  labels;
* extracts embedded YAML from HTML code blocks;
* normalizes that embedded block into fenced Markdown;
* metadata records artifact family, platform, type, tags, parameters, sources,
  VQL presence, permissions, references, tools, and relative path.

### `HijackLibsCollector`

Input: `wietze/HijackLibs` YAML entries.

Output:

* one `abuse_database` document per DLL hijacking entry;
* markdown includes expected locations, vulnerable executables, hijack type,
  conditions, variables, hashes, elevation flags, CVEs, and resources;
* metadata includes DLL name, vendor, hijack types, executable paths, expected
  locations, CVEs, and vulnerable executable metadata.

### `LOLDriversCollector`

Input: `magicsword-io/LOLDrivers` YAML entries.

Output:

* one `abuse_database` document per driver entry;
* markdown includes abuse details, known vulnerable samples, detections, and
  resources;
* metadata includes driver ID/name, category, tags, CVEs, vendors, products,
  MITRE ID, sample hashes, detections, and sample metadata.

### `OSSEMDataDictsCollector`

Input: `OTRF/OSSEM-DD` YAML event dictionaries.

Output:

* one `event_dictionary` document per selected event dictionary candidate;
* applies include/exclude path rules;
* requires `event_fields`;
* groups candidates by platform, log source, and event ID;
* keeps the best candidate by event version, described fields, field count, and
  path;
* metadata includes event ID/name/version, platform, log source, fields,
  references, source path, and tags.

### `CybersecSkillsCollector`

Input: `mukul975/Anthropic-Cybersecurity-Skills` `SKILL.md` files.

Output:

* one `practitioner_workflow` document per skill above the body-token threshold;
* filters body text under `min_body_tokens` from config;
* parses YAML frontmatter and Markdown body;
* metadata includes domain, subdomain, tags, framework mappings, version,
  license, body size, workflow steps, scenarios, tools referenced, and source
  path.

## Cache And Revision Policy

Git-backed collectors use `data/raw/.repos/`; ATT&CK STIX uses
`data/raw/.cache/enterprise-attack.json`. These caches are generated and ignored
by Git.

An existing non-empty clone is reused as-is. The shared helper does not fetch,
pull, verify the repository, or generally record the collected commit. A normal
rerun therefore reproduces the local cache, not necessarily current upstream
content. Refresh the exact source cache deliberately when freshness is required,
and preserve its commit/feed version with the run. `collected_at` is not an
upstream revision.

`volatility3_docs` and `mitre_atlas` pin source URLs to the collected commit when
possible. Most other Git-backed collectors retain configured default-branch
URLs.

## Adding Or Changing A Source

Before implementation, confirm legal use and attribution, stable access,
relevant task coverage, expected volume, and whether the source is rich enough
for the intended prompt count. Sparse sources must be marked or capped rather
than padded with inferred detail.

Use this naming pattern:

| Item | Pattern |
|---|---|
| Module | `collectors/<source_key>.py` |
| Raw output | `data/raw/<source_key>/<source_key>.jsonl` |
| Collection config | `configs/collection.yaml` → `<source_key>` |
| Source profile | `configs/source_profiles.yaml` → `source_profiles.<source_key>` |

Implementation sequence:

1. Add source settings to `configs/collection.yaml`.
2. Implement `collectors/<source_key>.py` using `BaseCollector`.
3. Normalize each logical item into one complete `RawDocument`.
4. Keep `doc_id` stable and unique across the complete corpus.
5. Preserve useful upstream structure and source revision metadata.
6. Register the class in `scripts/collect_all.py`.
7. Add its source/content-type policy to `configs/source_profiles.yaml`.
8. Add a prompt override or compactor only when existing source-type behavior is
   insufficient.
9. Add representative, malformed, and upstream-shape regression fixtures.
10. Run the source alone, validate the corpus, and render representative prompts.

Recommended content types include `technique_definition`, `atomic_test`,
`sigma_rule`, `hayabusa_rule`, `artifact_definition`, `event_dictionary`,
`tool_plugin`, `tool_module`, `vulnerability_catalog`, `case_study`,
`practitioner_workflow`, and `abuse_database`. Prefer the most precise stable
label that changes downstream policy.

## Validation Ladder

```bash
.venv/bin/python -m scripts.collect_all --source <source_key>
.venv/bin/python -m scripts.synthesize validate-raw --raw-dir data/raw
.venv/bin/python -m scripts.synthesize render-prompts \
  --mode pilot \
  --output-dir data/synthesized/<source_key>_dry_run
```

Then:

1. inspect the source JSONL for complete Markdown, stable IDs, readable titles,
   correct types, and useful metadata;
2. inspect `collection_manifest.json` errors and warnings;
3. compare expected and actual source volume;
4. test cache reuse and deliberate refresh behavior;
5. run the complete collector set when a complete-corpus manifest is required.

A single-source invocation replaces the combined manifest with only that source.
The command can also return success despite reported collector errors, so exit
status alone is not acceptance.

## Maintenance Checklist

When changing a parser or upstream contract:

- update the source-specific details above only when stable behavior changed;
- retain full evidence and backward-stable document IDs;
- test malformed and changed upstream shapes;
- validate cross-source ID uniqueness;
- review downstream prompt compactors and pair caps;
- record scope or durable policy changes in `project_state/`;
- keep run-specific counts in manifests and [Current
  State](../current-state/index.md), not on this page.
