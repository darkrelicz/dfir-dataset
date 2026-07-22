<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Collectors</h1>

Collectors normalize upstream DFIR/security sources into the shared
`RawDocument` schema.

<puml src="../diagrams/collector-inheritance.puml" alt="Collector inheritance diagram" width="900" />

# BaseCollector

`collectors.base.BaseCollector` provides:

* abstract `collect()` and `manifest()` methods;
* `_clone_repo()` for shallow or full git clone reuse;
* `_write_documents()` for JSONL writing with `jsonlines`;
* `_parse_datetime()` for ISO timestamps.

Collectors track `errors`, `warnings`, `duration`, and `doc_count` locally, then
return a `CollectionManifest`.

`_clone_repo()` is cache reuse, not synchronization. If the clone path is
non-empty, collection uses it as-is: the helper does not verify that it is a Git
repository and does not fetch, pull, or record its revision. Most source URLs in
raw documents point at a default branch rather than the exact collected commit.

`_write_documents()` opens the canonical source JSONL in write mode. It does not
write to a temporary file and atomically replace the destination, so an
interrupted write can leave partial output.

# CLI Orchestration

`scripts.collect_all`:

1. loads `configs/collection.yaml`;
2. maps each source key to a collector class;
3. supports `--list` and `--source`;
4. runs collectors sequentially;
5. writes `data/raw/collection_manifest.json`;
6. prints a Rich summary table.

The combined manifest describes the current CLI invocation, not everything that
may exist under `data/raw/`. A single-source run therefore replaces the manifest
with one entry. The CLI also currently exits successfully after unknown-source
selection, collector-reported errors, or caught fatal exceptions. Treat the
manifest error fields and raw-corpus validation as required success checks.

`--list` reports available source keys, but it does not instantiate collectors, inspect
caches, contact upstreams, or validate collector-specific values. Use a
single-source collection in an isolated output/cache setup when a real preflight
is required.

# Collector Details

## `MitreAttackCollector`

Input: Enterprise ATT&CK STIX JSON from the configured URL/cache path.

Output:

* one `technique_definition` document per ATT&CK technique;
* `doc_id`: `mitre-attack-<TID>`;
* markdown includes tactics, platforms, description, procedures, mitigations,
  and detection strategies when present;
* metadata includes external references, parent technique, and contributors.

## `SigmaRulesCollector`

Input: `SigmaHQ/sigma` git repository under `rules/`.

Output:

* one `sigma_rule` document per rule at or above `min_rule_level`;
* `doc_id`: `sigma-<rule id>`;
* markdown includes logsource, detection YAML, tags, false positives, and
  references;
* metadata includes level, status, logsource fields, ATT&CK IDs, tactic tags,
  false positives, and author.

## `AtomicRedTeamCollector`

Input: `redcanaryco/atomic-red-team` `atomics/` YAML files.

Output:

* one `atomic_test` document per atomic test;
* `doc_id`: `atomic-rt-<auto_generated_guid>`;
* markdown includes input arguments, dependencies, executor, command, and cleanup
  command;
* metadata includes technique ID, test GUID/index, platforms, executor,
  elevation, cleanup, and dependency flags.

## `CISAAdvisoriesCollector`

Input: `cisagov/CSAF` `csaf_files/**/*.json`.

Output:

* one `threat_advisory` document per CSAF advisory;
* `doc_id`: `cisa-<tracking id lowercased>`;
* markdown includes document notes, vulnerabilities, CVSS/CWE details,
  remediation, and references;
* metadata includes advisory ID, category, IT/OT type, CVEs, publisher, and
  version.

## `Volatility3DocsCollector`

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

## `MitreAtlasCollector`

Input: `mitre-atlas/atlas-data` latest v6 YAML from `dist/manifest.yaml`.

Output:

* `technique_definition` documents for ATLAS techniques;
* `mitigation` documents for ATLAS mitigations;
* `case_study` documents for ATLAS cases;
* metadata includes ATLAS ID, UUID, collection/format versions, source file,
  source commit, modified date, and object-specific relationships.

The collector loads the repo's parser package in-process without importing the
full API/database stack.

## `CISAKEVCollector`

Input: CISA KEV JSON feed.

Output:

* one `vulnerability_catalog` document per vendor group;
* `doc_id`: `kev-<vendor slug>`;
* markdown includes vendor/product summary, vulnerability table, and details;
* metadata includes products, CVE IDs/count, ransomware-linked count, and
  catalog version.

## `KapeFilesCollector`

Input: `EricZimmerman/KapeFiles`.

Output:

* `artifact_definition` documents from `.tkape` targets;
* `tool_module` documents from `.mkape` modules;
* disabled KAPE files under `!Disabled` paths are skipped;
* metadata records target paths/categories or module tools/processors.

## `HayabusaRulesCollector`

Input: `Yamato-Security/hayabusa-rules`.

Output:

* one `hayabusa_rule` document per YAML rule document;
* skips non-rule YAML documents and duplicate IDs;
* markdown includes logsource, detection YAML, alert details, tags, false
  positives, samples, and references;
* metadata includes rule level, status, logsource fields, tags, references,
  author, modified date, rule type, and details format.

## `LOLBASGTFOBinsCollector`

Input:

* `LOLBAS-Project/LOLBAS`;
* `GTFOBins/GTFOBins.github.io`.

Output:

* `lolbas_windows_lolbin` for LOLBAS entries;
* `gtfobins_linux_abuse_function` for GTFOBins entries with functions;
* `gtfobins_linux_alias` for thin alias entries;
* metadata captures binary names, platforms, functions/categories, MITRE IDs,
  command counts, full paths, detection details, contexts, and related fields.

## `ForensicArtifactsCollector`

Input: `ForensicArtifacts/artifacts` YAML data.

Output:

* one `artifact_definition` document per artifact definition;
* markdown includes supported OS, description, source types, paths, registry
  keys/values, WMI queries, commands, artifact groups, and references;
* metadata includes artifact name, supported OS, source types/count, file paths,
  and registry keys.

## `VelociraptorArtifactsCollector`

Input: generated Velociraptor artifact reference Markdown pages.

Output:

* Velociraptor-specific content types such as `velociraptor_client_artifact`,
  `velociraptor_event_artifact`, `velociraptor_vql_artifact`, and related
  labels;
* extracts embedded YAML from HTML code blocks;
* normalizes that embedded block into fenced Markdown;
* metadata records artifact family, platform, type, tags, parameters, sources,
  VQL presence, permissions, references, tools, and relative path.

## `HijackLibsCollector`

Input: `wietze/HijackLibs` YAML entries.

Output:

* one `abuse_database` document per DLL hijacking entry;
* markdown includes expected locations, vulnerable executables, hijack type,
  conditions, variables, hashes, elevation flags, CVEs, and resources;
* metadata includes DLL name, vendor, hijack types, executable paths, expected
  locations, CVEs, and vulnerable executable metadata.

## `LOLDriversCollector`

Input: `magicsword-io/LOLDrivers` YAML entries.

Output:

* one `abuse_database` document per driver entry;
* markdown includes abuse details, known vulnerable samples, detections, and
  resources;
* metadata includes driver ID/name, category, tags, CVEs, vendors, products,
  MITRE ID, sample hashes, detections, and sample metadata.

## `OSSEMDataDictsCollector`

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

## `CybersecSkillsCollector`

Input: `mukul975/Anthropic-Cybersecurity-Skills` `SKILL.md` files.

Output:

* one `practitioner_workflow` document per skill above the body-token threshold;
* filters body text under `min_body_tokens` from config;
* parses YAML frontmatter and Markdown body;
* metadata includes domain, subdomain, tags, framework mappings, version,
  license, body size, workflow steps, scenarios, tools referenced, and source
  path.

# Adding A Collector

Use [Extension Points](extension-points.md) for the full change checklist.
At minimum, add:

1. source settings in `configs/collection.yaml`;
2. a collector module under `collectors/`;
3. a `collector_map` entry in `scripts/collect_all.py`;
4. source and content-type synthesis profiles;
5. prompt templates or compactors only when the source behavior needs them;
6. project-state doc updates when the source changes scope or decisions.
