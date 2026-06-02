# Phase 1: Define the DFIR Task Taxonomy — Implementation Plan

## Goal

Stand up the project skeleton and produce a finalized, machine-readable task taxonomy that will drive every downstream phase (collection targeting, prompt template design, quality scoring, distribution auditing). This is **Week 3, Days 1–3** per the master plan.

## Scope

Phase 1 has three workstreams:

| # | Workstream | Effort | Why |
|---|---|---|---|
| 1 | **Project scaffolding** | ~2 hours | The repo is empty. We need the directory tree, `pyproject.toml`, configs, and `.gitignore` before any code lands |
| 2 | **Taxonomy document** | ~1 day | The core deliverable — a structured YAML defining all categories, sub-categories, example tasks, difficulty tiers, and Shepherd alignment |
| 3 | **Taxonomy validation & review prep** | ~0.5 day | A small Python script to validate the taxonomy YAML schema + a review checklist for team/mentor sign-off |

---

## Proposed Changes

### Workstream 1 — Project Scaffolding

Set up the full directory tree from `dfir_dataset_plan.md §2.3` so that subsequent phases can drop files into the right places without restructuring.

#### [NEW] [pyproject.toml](file:///home/hunta/dfir-dataset/pyproject.toml)

- Project metadata (`dfir-dataset`, version `0.1.0`, Python `>=3.11`)
- Dependencies for Phase 1–2 (initially minimal):
  - `pyyaml` — taxonomy and config parsing
  - `pydantic >=2.0` — schema validation for raw documents and taxonomy
  - `jsonlines` — JSONL I/O (used everywhere from Phase 2 onward)
  - `rich` — CLI output formatting
- Dev dependencies: `pytest`, `ruff`, `mypy`
- Script entry points: `dfir-collect = "scripts.collect_all:main"` (placeholder)

#### [MODIFY] [.gitignore](file:///home/hunta/dfir-dataset/.gitignore)

Expand to cover:
- `data/` (all collected/synthesized data — large, regenerable)
- `.env` (API keys)
- `__pycache__/`, `*.pyc`
- `.venv/`
- `dist/`, `*.egg-info`
- `.mypy_cache/`, `.ruff_cache/`
- `*.jsonl` at project root (scratch files)

#### [NEW] Directory structure

Create empty `__init__.py` and placeholder `README.md` files to establish:

```
collectors/          # Phase 2
synthesizers/        # Phase 3
  prompts/           # Phase 3
  formatters/        # Phase 3
quality/             # Phase 4
  validators/        # Phase 4
  reports/           # Phase 4
packaging/           # Phase 5
evaluation/          # Phase 6
scripts/             # Entry points
configs/             # Pipeline configuration
docs/                # Handover documentation
data/                # Output (gitignored)
  raw/
  synthesized/
  filtered/
  packaged/
  evaluation/
taxonomy/            # NEW — Phase 1 deliverable lives here
```

> [!NOTE]
> The `taxonomy/` directory is not in the original plan tree but is a natural home for the taxonomy YAML and its validation script. It keeps Phase 1 artifacts cleanly separated from Phase 2+ code.

#### [NEW] [configs/collection.yaml](file:///home/hunta/dfir-dataset/configs/collection.yaml)

Skeleton config referencing the 4 primary sources with placeholder URLs and output paths. This will be fleshed out in Phase 2 but having the file now establishes the config pattern.

#### [NEW] [configs/synthesis.yaml](file:///home/hunta/dfir-dataset/configs/synthesis.yaml)

Copy the synthesis config from `dfir_dataset_plan.md §3.4` verbatim. It's already well-defined and won't change until Phase 3.

#### [NEW] [configs/quality.yaml](file:///home/hunta/dfir-dataset/configs/quality.yaml)

Skeleton with score thresholds from `dfir_dataset_plan.md §4.1` (composite ≥ 3.5, duplicate Jaccard > 0.8).

#### [NEW] [configs/packaging.yaml](file:///home/hunta/dfir-dataset/configs/packaging.yaml)

Skeleton with split ratios (80/10/10) and output format (JSONL).

---

### Workstream 2 — Taxonomy Document

This is the core Phase 1 deliverable. The taxonomy is authored as a **structured YAML file** so it can be:
1. Version-controlled with meaningful diffs
2. Programmatically consumed by the synthesis pipeline (prompt template selection, category validation)
3. Used by the quality scorer (valid category/difficulty labels)
4. Used by the distribution auditor (target percentages)

#### [NEW] [taxonomy/dfir_taxonomy.yaml](file:///home/hunta/dfir-dataset/taxonomy/dfir_taxonomy.yaml)

Top-level structure:

```yaml
version: "1.0"
description: "DFIR Task Taxonomy for Shepherd fine-tuning dataset"
date_created: "2026-06-15"

difficulty_distribution:
  junior: 0.30
  mid: 0.50
  senior: 0.20

category_distribution:
  artifact_analysis: 0.30
  ttp_identification: 0.25
  triage_decision: 0.18
  detection_engineering: 0.14
  report_generation: 0.13

categories:
  - id: artifact_analysis
    name: "Artifact Analysis"
    description: "..."
    shepherd_alignment: ["Memory Agent", "Disk/KAPE Agent"]
    priority: critical
    sub_categories:
      - id: process_analysis
        name: "Process Analysis"
        # ... (6 sub-categories from plan §Phase 1)
    example_tasks: [...]  # 10 tasks, see below
    
  - id: ttp_identification
    # ...
```

**Example tasks per category (10 each, 50 total):**

Each example task includes:

```yaml
example_tasks:
  - id: "AA-001"
    instruction: "Given this Volatility pslist output showing svchost.exe (PID 1284) with PPID 612 (services.exe) and svchost.exe (PID 4012) with PPID 2340 (explorer.exe), which process is suspicious and why?"
    difficulty: junior
    mitre_techniques: ["T1036.005"]
    tools: ["Volatility 3", "pslist"]
    reasoning_focus: "Parent-child relationship validation"
    sub_category: process_analysis
```

Below are the 10 example tasks per category. These are designed to span the difficulty tiers (3 junior, 5 mid, 2 senior) and cover the sub-categories / key skills for each category.

##### Category 1: Artifact Analysis (incl. Deep Forensics)

| # | Difficulty | Sub-Category | Task Summary | Key ATT&CK |
|---|---|---|---|---|
| AA-01 | Junior | Process Analysis | Identify suspicious parent-child relationship in pslist output | T1036.005 |
| AA-02 | Junior | Event Log Deep Analysis | Interpret a 4624 logon event — what type is Logon Type 10? | T1021.001 |
| AA-03 | Junior | Filesystem Artifact | Parse prefetch file metadata — what does the execution count tell you? | T1059 |
| AA-04 | Mid | Process Analysis | Given pstree output with orphan process, determine if DKOM is likely | T1014 |
| AA-05 | Mid | Memory Structure | Interpret malfind output showing `PAGE_EXECUTE_READWRITE` in a non-image VAD — is this injection? | T1055.001 |
| AA-06 | Mid | Handle & Object | Analyze mutex names from handles plugin — identify known malware mutexes | T1106 |
| AA-07 | Mid | Registry Forensics | Examine Run/RunOnce keys from printkey output — classify persistence mechanism | T1547.001 |
| AA-08 | Mid | Event Log Deep Analysis | Reconstruct logon chain from 4624→4648→4672 sequence — what does this indicate? | T1078 |
| AA-09 | Senior | Memory Structure + Process | Correlate malfind + vadinfo + handles across multiple processes to confirm process hollowing | T1055.012 |
| AA-10 | Senior | Filesystem + Registry | Cross-correlate shimcache entries with $UsnJrnl timestamps to establish execution timeline | T1059.001 |

##### Category 2: TTP Identification

| # | Difficulty | Task Summary | Key ATT&CK |
|---|---|---|---|
| TTP-01 | Junior | Identify technique from a scenario describing scheduled task creation | T1053.005 |
| TTP-02 | Junior | Map "attacker used PsExec to move to fileserver" to correct technique | T1021.002 |
| TTP-03 | Junior | Classify a PowerShell download cradle as initial access vs execution | T1059.001 |
| TTP-04 | Mid | Given a sequence of observed behaviors, construct partial attack chain with tactic progression | Multiple |
| TTP-05 | Mid | Distinguish between T1055.001 (DLL injection) and T1055.012 (process hollowing) from behavioral indicators | T1055.* |
| TTP-06 | Mid | Identify defense evasion technique from event log gap (cleared logs) | T1070.001 |
| TTP-07 | Mid | Map WMI-based lateral movement to sub-technique and identify prerequisite techniques | T1047 |
| TTP-08 | Mid | Identify data staging behavior from filesystem artifact pattern | T1074.001 |
| TTP-09 | Senior | Given a complex intrusion narrative, produce full ATT&CK navigator layer with confidence ratings | Multiple |
| TTP-10 | Senior | Analyze novel behavior that doesn't map cleanly to existing ATT&CK — propose closest technique + gaps | — |

##### Category 3: Triage Decision-Making

| # | Difficulty | Task Summary | Key Skill |
|---|---|---|---|
| TRI-01 | Junior | Given an AV alert on a workstation, list first 5 triage steps in priority order | Evidence collection |
| TRI-02 | Junior | Decide whether to isolate a host based on a single suspicious process | Risk assessment |
| TRI-03 | Junior | Prioritize between examining memory vs disk given a ransomware alert | Evidence volatility |
| TRI-04 | Mid | Given 3 simultaneous alerts across different hosts, prioritize investigation order with justification | Multi-host triage |
| TRI-05 | Mid | Determine which Volatility plugins to run next based on initial pslist anomalies | Tool selection |
| TRI-06 | Mid | Assess whether lateral movement has occurred based on initial indicators and recommend pivots | Pivot planning |
| TRI-07 | Mid | Evaluate evidence sufficiency — do we have enough to confirm compromise or need more collection? | Confidence calibration |
| TRI-08 | Mid | Given a partially analyzed memory image, identify the critical evidence gaps | Gap analysis |
| TRI-09 | Senior | Design a full triage workflow for a suspected supply chain compromise across 50 endpoints | Workflow design |
| TRI-10 | Senior | Given conflicting indicators (benign explanations vs malicious), reason through ambiguity and recommend path | Ambiguity resolution |

##### Category 4: Detection Engineering

| # | Difficulty | Task Summary | Key Skill |
|---|---|---|---|
| DE-01 | Junior | Explain what a given Sigma rule detects in plain English | Rule interpretation |
| DE-02 | Junior | Identify the log source required for a specific Sigma rule to fire | Log source mapping |
| DE-03 | Junior | Explain the difference between Sigma rule levels (low/medium/high/critical) | Severity classification |
| DE-04 | Mid | Write a Sigma rule to detect a specific ATT&CK technique given a description | Rule authoring |
| DE-05 | Mid | Identify detection gaps in an existing Sigma rule (evasion opportunities) | Gap analysis |
| DE-06 | Mid | Translate a Sigma rule's detection logic to a Splunk SPL query | Cross-platform translation |
| DE-07 | Mid | Explain a YARA rule's detection logic and identify what malware family it targets | YARA interpretation |
| DE-08 | Mid | Given a false positive report, modify a Sigma rule to reduce FP rate without losing coverage | Tuning |
| DE-09 | Senior | Design a detection strategy (multiple correlated rules) for a full attack chain | Detection architecture |
| DE-10 | Senior | Evaluate detection coverage across MITRE ATT&CK matrix and identify priority gaps to fill | Coverage assessment |

##### Category 5: Incident Report Generation

| # | Difficulty | Task Summary | Key Skill |
|---|---|---|---|
| IR-01 | Junior | Given a list of findings, write a 1-paragraph executive summary | Summarization |
| IR-02 | Junior | Identify which findings in a draft report lack evidence citations | Citation checking |
| IR-03 | Junior | Rewrite an overclaiming statement with appropriate confidence language | Calibration |
| IR-04 | Mid | Given raw Volatility output + event log findings, write a structured investigation summary | Report writing |
| IR-05 | Mid | Add appropriate caveats and confidence levels to a set of forensic conclusions | Uncertainty quantification |
| IR-06 | Mid | Organize findings by ATT&CK tactic phase into a timeline narrative | Temporal organization |
| IR-07 | Mid | Write recommendations section based on identified TTPs and gaps | Actionable recommendations |
| IR-08 | Mid | Review a draft report and identify logical gaps, unsupported conclusions, and missing next steps | Report review |
| IR-09 | Senior | Produce a full IR report from a complex multi-host investigation with evidence appendix | Full report |
| IR-10 | Senior | Write both technical and executive versions of the same incident, calibrating detail level appropriately | Audience adaptation |

> [!IMPORTANT]
> These 50 example tasks serve **two purposes**: (1) they guide the synthesis prompt templates in Phase 3 by showing the *type* of questions each category should produce, and (2) a subset can seed the **hand-curated evaluation benchmark** in Phase 6 (the plan explicitly says the benchmark should NOT come from synthesis).

#### [NEW] [taxonomy/README.md](file:///home/hunta/dfir-dataset/taxonomy/README.md)

Brief explanation of the taxonomy structure, how it's consumed by downstream phases, and how the successor can extend it (add categories, add sub-categories, adjust distribution targets).

---

### Workstream 3 — Taxonomy Validation & Review Prep

#### [NEW] [taxonomy/validate_taxonomy.py](file:///home/hunta/dfir-dataset/taxonomy/validate_taxonomy.py)

A small Pydantic-based validation script that:
1. Loads `dfir_taxonomy.yaml`
2. Validates schema (all required fields present, correct types)
3. Checks distribution targets sum to 1.0 (±0.01 tolerance)
4. Checks difficulty distribution sums to 1.0
5. Checks each category has ≥ 10 example tasks
6. Checks difficulty distribution of example tasks approximates targets (warn if >10% deviation)
7. Checks all referenced MITRE technique IDs match `T[0-9]{4}(\.[0-9]{3})?` format
8. Outputs a summary report (pass/fail per check, warnings)

Pydantic models:

```python
class ExampleTask(BaseModel):
    id: str
    instruction: str
    difficulty: Literal["junior", "mid", "senior"]
    mitre_techniques: list[str] = []
    tools: list[str] = []
    reasoning_focus: str
    sub_category: str | None = None

class SubCategory(BaseModel):
    id: str
    name: str
    description: str
    primary_sources: list[str] = []
    example_tasks_prefix: str  # e.g., "process_analysis" links to AA tasks

class Category(BaseModel):
    id: str
    name: str
    description: str
    shepherd_alignment: list[str]
    priority: Literal["critical", "high", "medium"]
    sub_categories: list[SubCategory] = []
    example_tasks: list[ExampleTask]

class Taxonomy(BaseModel):
    version: str
    description: str
    date_created: str
    difficulty_distribution: dict[str, float]
    category_distribution: dict[str, float]
    categories: list[Category]
```

#### [NEW] [taxonomy/review_checklist.md](file:///home/hunta/dfir-dataset/taxonomy/review_checklist.md)

A checklist for the team/mentor taxonomy review covering:
- [ ] All 5 categories adequately represent Shepherd's specialist agent needs
- [ ] Example tasks are realistic (would a SOC analyst actually ask this?)
- [ ] Difficulty distribution is appropriate (not too easy, not too esoteric)
- [ ] MITRE ATT&CK coverage: all 14 tactics represented across example tasks
- [ ] Deep forensics sub-categories are sufficiently granular
- [ ] No critical DFIR skill gaps (e.g., timeline analysis, evidence handling)
- [ ] Deferred categories are correctly scoped (not needed for Shepherd MVP)

#### [NEW] [taxonomy/gap_analysis.py](file:///home/hunta/dfir-dataset/taxonomy/gap_analysis.py)

A script that cross-references example tasks' `mitre_techniques` fields against the full ATT&CK tactic list to produce a coverage heatmap:

```
Tactic Coverage:
  Reconnaissance         ████░░░░░░  2/10 techniques
  Initial Access          ██████░░░░  3/10 techniques
  Execution               ████████░░  8/10 techniques
  Persistence             ██████████  6/10 techniques
  ...
```

This helps identify blind spots before Phase 2 collection begins. If a tactic has zero example tasks, that's a signal we may need to adjust source collection priorities.

---

### Workstream 0 — Documentation

#### [MODIFY] [README.md](file:///home/hunta/dfir-dataset/README.md)

Replace the placeholder with a proper project README covering:
- Project purpose (DFIR training dataset for Shepherd)
- Current status (Phase 1)
- Quick-start (how to install, validate taxonomy)
- Project structure overview
- Link to `dfir_dataset_plan.md` for full context

#### [NEW] [docs/ARCHITECTURE.md](file:///home/hunta/dfir-dataset/docs/ARCHITECTURE.md)

Skeleton with Phase 1 decisions documented:
- Why YAML for taxonomy (machine-readable, diffable, extensible)
- Why Pydantic for validation (type safety, clear error messages)
- Directory layout rationale

---

## User Review Required

> [!IMPORTANT]
> **Taxonomy as YAML vs Markdown:** The master plan implies the taxonomy is a document. I'm proposing a **structured YAML file** instead because it can be programmatically consumed by the synthesis pipeline (Phase 3 picks prompt templates by category ID), the quality scorer (Phase 4 validates category labels), and the distribution auditor (Phase 4 checks against target percentages). A separate Markdown rendering can be auto-generated for human review. **Do you agree with YAML as the source of truth?**

> [!IMPORTANT]
> **`taxonomy/` directory:** This directory isn't in the original plan tree. It's a clean home for Phase 1 artifacts. The alternative is putting `dfir_taxonomy.yaml` directly in `configs/`. **Preference?**

> [!IMPORTANT]
> **50 example tasks:** I've drafted 10 per category (tables above). These are intentionally detailed enough to seed Phase 3 prompt templates and Phase 6 evaluation benchmarks. **Review the task summaries above — are there critical DFIR scenarios missing?**

---

## Verification Plan

### Automated Tests

```bash
# 1. Validate taxonomy schema
python taxonomy/validate_taxonomy.py

# 2. Run gap analysis
python taxonomy/gap_analysis.py

# 3. Lint all Python files
ruff check .

# 4. Type-check validation script
mypy taxonomy/

# 5. Run pytest (taxonomy validation tests)
pytest tests/test_taxonomy.py -v
```

#### [NEW] [tests/test_taxonomy.py](file:///home/hunta/dfir-dataset/tests/test_taxonomy.py)

Unit tests for taxonomy validation:
- `test_taxonomy_loads` — YAML parses without error
- `test_all_categories_present` — 5 categories exist
- `test_difficulty_distribution_sums_to_one` — 0.30 + 0.50 + 0.20 = 1.0
- `test_category_distribution_sums_to_one` — 0.30 + 0.25 + 0.18 + 0.14 + 0.13 = 1.0
- `test_each_category_has_minimum_examples` — ≥ 10 per category
- `test_mitre_ids_are_valid_format` — regex validation
- `test_difficulty_balance_per_category` — within 10% of targets

### Manual Verification

- [ ] Walk through taxonomy YAML to confirm all 50 example tasks are coherent
- [ ] Verify MITRE technique IDs are real (spot-check 10 against attack.mitre.org)
- [ ] Share `taxonomy/review_checklist.md` with team/mentor for sign-off
- [ ] Confirm taxonomy gap analysis shows no critical blind spots (all 14 tactics represented)
