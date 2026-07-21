<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Source Guide</h1>

The selected scope is Core + Tier 1 + Tier 2: all 16 collectors in
`scripts/collect_all.py`.

All collectors emit `RawDocument` rows with this common shape:

```json
{
  "doc_id": "stable-source-specific-id",
  "source": "source_key",
  "source_url": "https://...",
  "title": "Human-readable title",
  "date_collected": "YYYY-MM-DD",
  "date_published": null,
  "content_type": "specific_content_label",
  "content_markdown": "Normalized source content",
  "metadata": {},
  "word_count": 0
}
```

# Current Sources

| Source | Collector | Content Types | Current Docs | Notes |
|---|---|---|---:|---|
| `mitre_attack` | `MitreAttackCollector` | `technique_definition` | 697 | Downloads ATT&CK STIX cache and emits one document per technique. |
| `sigma_rules` | `SigmaRulesCollector` | `sigma_rule` | 3,111 | Parses Sigma YAML rules at or above configured level. |
| `atomic_red_team` | `AtomicRedTeamCollector` | `atomic_test` | 1,811 | Emits one document per atomic test. |
| `cisa_advisories` | `CISAAdvisoriesCollector` | `threat_advisory` | 3,849 | Parses CSAF JSON advisories from the CISA CSAF repo. |
| `volatility3_docs` | `Volatility3DocsCollector` | `tool_plugin`, `tool_documentation` | 194 | Parses plugin AST details plus selected RST docs. |
| `mitre_atlas` | `MitreAtlasCollector` | `technique_definition`, `mitigation`, `case_study` | 262 | Loads ATLAS v6 YAML with the local ATLAS parser package. |
| `cisa_kev` | `CISAKEVCollector` | `vulnerability_catalog` | 270 | Downloads KEV JSON and groups entries by vendor. |
| `kape_files` | `KapeFilesCollector` | `artifact_definition`, `tool_module` | 811 | Parses `.tkape` targets and `.mkape` modules. |
| `hayabusa_rules` | `HayabusaRulesCollector` | `hayabusa_rule` | 4,839 | Parses one or more YAML docs per rule file, skips duplicate IDs. |
| `lolbas_gtfobins` | `LOLBASGTFOBinsCollector` | `lolbas_windows_lolbin`, `gtfobins_linux_abuse_function`, `gtfobins_linux_alias` | 720 | Combines Windows LOLBAS and Linux GTFOBins entries. |
| `forensic_artifacts` | `ForensicArtifactsCollector` | `artifact_definition` | 731 | Uses the `artifacts` library to parse artifact YAML definitions. |
| `velociraptor_artifacts` | `VelociraptorArtifactsCollector` | Velociraptor-specific artifact labels | 437 | Extracts embedded artifact YAML from generated documentation pages. |
| `hijacklibs` | `HijackLibsCollector` | `abuse_database` | 590 | Parses DLL hijacking entries and vulnerable executable metadata. |
| `loldrivers` | `LOLDriversCollector` | `abuse_database` | 656 | Parses vulnerable/malicious Windows driver YAML records. |
| `ossem_data_dicts` | `OSSEMDataDictsCollector` | `event_dictionary` | 699 | Keeps best event dictionary candidate by event/version/field richness. |
| `cybersec_skills` | `CybersecSkillsCollector` | `practitioner_workflow` | 670 | Filters skills below 500 body tokens to avoid thin templates. |

# Source Cache Rules

Git-backed collectors clone to `data/raw/.repos/`. ATT&CK STIX is cached at
`data/raw/.cache/enterprise-attack.json`. These paths are generated data and
are ignored by git.

Collectors reuse an existing non-empty clone path rather than recloning.
They do not fetch or pull changes, verify that the directory is a valid clone,
or compare it with the upstream revision. The ATT&CK collector likewise reuses
an existing cache file. A normal rerun therefore reproduces the local cache,
not necessarily the latest upstream source.

When freshness is required, refresh or replace the exact source-specific clone
or cache before collection, then record the resulting upstream commit or feed
version outside the current collection manifest. Do not assume `collected_at`
identifies the upstream revision: the manifest records collection time and
collector package version, but has no general source-revision or configuration
fingerprint fields.

# Thin Source Handling

Thin source controls happen later in synthesis:

* source profiles can set `thin_source: true`;
* content-type profiles can set `thin_source: true` or `max_pairs`;
* documents under 250 words generate one pair;
* prompt compactors reduce prompt size without mutating raw documents.

# Source-Specific Notes

`volatility3_docs` and `mitre_atlas` pin GitHub blob URLs to the collected
commit when possible. Most other git-backed collectors use the public default
branch names configured in code.

`ossem_data_dicts` applies include/exclude path filters from
`configs/collection.yaml` and deduplicates event dictionaries by platform,
log source, and event ID.

`velociraptor_artifacts` derives content types from artifact type, tags, reports,
and whether VQL is present.
