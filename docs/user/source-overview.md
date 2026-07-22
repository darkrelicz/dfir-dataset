<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">Source Overview</h1>

> This page documents the high level overview of the current configured sources. For implementation details, schemas, and normalization behavior, see [Source Internals](../developer/source-guide.md).

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


# Cache And Freshness

Git-backed sources are cached under `data/raw/.repos/`. ATT&CK STIX is cached under `data/raw/.cache/`. 

Collection reuses a non-empty local cache and does not automatically fetch newer upstream content. A normal rerun therefore reproduces the local cache, which may not be the latest upstream version.

<box type="warning" seamless header="">
<md>
When freshness matters, deliberately refresh the exact source cache and record the upstream revision used. The collection manifest records collection time, not a general upstream revision for every source.
</md>
</box>
