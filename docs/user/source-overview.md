<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Source Overview</h1>

Use this page when choosing which DFIR sources to collect. For collector
implementation details, schemas, and normalization behavior, see
[Source Internals](../developer/source-guide.md).

# Available Sources

The configured collection scope contains 16 sources:

| Source | Provides |
|---|---|
| `mitre_attack` | ATT&CK technique definitions |
| `sigma_rules` | Sigma detection rules |
| `atomic_red_team` | Atomic tests |
| `cisa_advisories` | CISA threat advisories |
| `volatility3_docs` | Volatility plugins and documentation |
| `mitre_atlas` | ATLAS techniques, mitigations, and case studies |
| `cisa_kev` | Known exploited vulnerabilities |
| `kape_files` | KAPE targets and modules |
| `hayabusa_rules` | Hayabusa detection rules |
| `lolbas_gtfobins` | Windows LOLBins and Linux GTFOBins techniques |
| `forensic_artifacts` | Forensic artifact definitions |
| `velociraptor_artifacts` | Velociraptor artifacts |
| `hijacklibs` | DLL hijacking data |
| `loldrivers` | Vulnerable and malicious driver data |
| `ossem_data_dicts` | Security event dictionaries |
| `cybersec_skills` | Practitioner workflows |

# Select Sources

List the configured collectors:

```bash
python -m scripts.collect_all --list
```

Collect every configured source:

```bash
python -m scripts.collect_all
```

Collect one source:

```bash
python -m scripts.collect_all --source mitre_attack
```

For complete execution details, output locations, and success checks, see
[Running The Pipeline](running-the-pipeline.md#data-collection).

# Cache And Freshness

Git-backed sources are cached under `data/raw/.repos/`; ATT&CK STIX is cached
under `data/raw/.cache/`. Collection reuses a non-empty local cache and does not
automatically fetch newer upstream content. A normal rerun therefore reproduces
the local cache, which may not be the latest upstream version.

When freshness matters, deliberately refresh the exact source cache and record
the upstream revision used. The collection manifest records collection time,
not a general upstream revision for every source.

# Interpreting Collection Results

Raw rows are written below `data/raw/<source>/`, and the combined result is
summarized in `data/raw/collection_manifest.json`.

A single-source collection replaces the combined manifest with a one-source
manifest. Collection can also exit successfully while reporting source errors,
so inspect manifest errors and warnings and run raw-corpus validation before
synthesis:

```bash
python -m scripts.synthesize validate-raw --raw-dir data/raw
```
