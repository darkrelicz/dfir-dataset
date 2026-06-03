# Project 1: Building a Production-Grade DFIR Training Dataset
## Context
This project is part of a summer internship (May 11 – Aug 7, extendable) building **Shepherd**, a local on-premise DFIR AI investigation assistant. The project will be handed over to a full-time colleague, and the team intends to expand it for real operations.
The primary deliverable is not just a dataset — it is a **re-runnable dataset factory**: a documented, reproducible pipeline that the successor can iterate on, expand, and re-generate as the project evolves.
### Relationship to Shepherd
This dataset is designed to fine-tune the model powering Shepherd's reasoning layer. The task taxonomy is directly aligned with Shepherd's specialist agent architecture:
| Shepherd Component | Dataset Focus Area |
|---|---|
| Memory Agent | Volatility output interpretation, process triage reasoning |
| Windows Event Log Agent | EVTX analysis, logon/auth event chain reasoning |
| Report Agent | Forensic report generation with evidence citations |
| Reviewer Agent | Overclaim detection, confidence calibration |
| Capability registry | Maps to instruction pair categories |
### Hardware
- **Training platform:** NVIDIA DGX Sparks (GB10 Grace Blackwell, 128GB unified memory)
- **Fine-tuning method:** LoRA or QLoRA SFT via Unsloth (CRAFT/RAFT deferred until Shepherd has a RAG layer)
- **Base model:** GLM-4.7-Flash (30B MoE, 3B active parameters)
### Timeline Position
| Weeks | Phase | This Document Covers |
|---|---|---|
| 1-2 (Jun 1-14) | Close Shepherd MVP 2, tag v0.2.0 | — |
| **3-8 (Jun 15 - Jul 26)** | **DFIR Dataset Pipeline** | **✅ This is the plan** |
| 9-10 (Jul 27 - Aug 7) | Fine-tune + evaluate on DGX Sparks | Validation phase |
---
## Phase 1: Define the DFIR Task Taxonomy (Week 3, Days 1-3)
The taxonomy defines what the fine-tuned model should be able to do. Every instruction pair maps to a category. This taxonomy is anchored to Shepherd's specialist agent architecture to ensure the dataset produces a model that integrates naturally into the existing system.
### Selected Task Categories (5 of 10)
For this version, focus on the 5 categories most relevant to Shepherd's current and near-term capabilities. The remaining 5 can be added by the successor.
| # | Category | Shepherd Alignment | Priority | Example Tasks |
|---|---|---|---|---|
| 1 | **Artifact Analysis** (incl. Deep Forensics) | Memory Agent, Disk/KAPE Agent | 🔴 Critical | Parse Volatility output, interpret process trees, analyze Windows event logs, decode prefetch files, VAD/injection analysis, handle/mutex enumeration, registry persistence analysis, MFT timeline analysis, event log chain reconstruction |
| 2 | **TTP Identification** | All specialist agents | 🔴 Critical | Map observed behaviors to MITRE ATT&CK techniques, identify attack chain stages, classify TTP severity |
| 3 | **Triage Decision-Making** | Orchestrator, Memory Agent | 🔴 Critical | Given initial indicators, prioritize investigation steps, recommend evidence collection, decide next pivots |
| 4 | **Detection Engineering** | Future detection capability | 🟡 High | Write/interpret Sigma rules, explain YARA rules, translate between detection languages |
| 5 | **Incident Report Generation** | Report Agent, Reviewer Agent | 🟡 High | Produce evidence-cited IR reports, calibrate confidence language, flag overclaims |
#### Artifact Analysis Sub-Categories (Deep Forensics)
| Sub-Category | Example Tasks | Primary Sources |
|---|---|---|
| Process Analysis | Process tree interpretation, suspicious parent-child, DKOM detection | MITRE ATT&CK, Volatility |
| Memory Structure Analysis | VAD analysis, injection detection via memory permissions, hollowed process indicators, malfind interpretation | MITRE ATT&CK (T1055.*) |
| Handle & Object Analysis | Mutex analysis, named pipe enumeration, suspicious handle patterns | MITRE ATT&CK (T1570, T1559) |
| Registry Forensics | Persistence keys (Run/RunOnce), service creation artifacts, shimcache interpretation | MITRE ATT&CK (T1547.*), Atomic Red Team |
| Filesystem Artifact Analysis | Prefetch parsing, MFT timeline analysis, ADS detection, $UsnJrnl interpretation | MITRE ATT&CK, CISA |
| Event Log Analysis | Logon chain reconstruction (4624/4625/4648), service install events (7045), PowerShell logging (4103/4104) | Sigma rules, MITRE ATT&CK |
### Categories Deferred to Successor
| Category | Why Deferred |
|---|---|
| Malware Analysis | Requires specialized source data (sandbox reports, RE writeups) |
| ~~Memory Forensics (deep)~~ | ~~Now included under Artifact Analysis as deep forensics sub-categories~~ |
| Threat Hunt Hypothesis Generation | Requires operational threat intel context that's hard to synthesize |
| Network Forensics | PCAP Agent is far on Shepherd's roadmap |
| Cross-Artifact Correlation | Depends on multi-artifact data that doesn't exist yet |
### Deliverables
- [ ] Finalized taxonomy document with 5-10 concrete example tasks per category
- [ ] Difficulty distribution targets: 30% junior, 50% mid, 20% senior
- [ ] Taxonomy review with team/mentor
---
## Phase 2: Source Collection Pipeline (Week 3 Day 4 – Week 5)
### 2.1 Design Principle: Collect from Structured, Licensed Sources First
The collection pipeline targets only sources that are:
1. **Programmatically accessible** (APIs, Git repos, structured feeds — no manual PDF scraping)
2. **Clearly licensed** for derivative use (open source, public domain, or CC-licensed)
3. **High operational signal** (practitioners use these, not just researchers)
### 2.2 Source Inventory
#### Primary Sources (Build collectors for these)
| # | Source | Documents | Content Type | Access Method | License | Collection Effort |
|---|---|---|---|---|---|---|
| 1 | **MITRE ATT&CK** | ~800 techniques + sub-techniques | TTP definitions, procedures, mitigations, detection guidance | `mitreattack-python` STIX API | Apache 2.0 ✅ | 2-3 days |
| 2 | **SigmaHQ Rules** | ~3,000+ detection rules | YAML rules with metadata, references, tags | `git clone` + YAML parsing | LGPL 2.1 ✅ | 1-2 days |
| 3 | **Atomic Red Team** | ~800+ test procedures | TTP test procedures with commands, expected output | `git clone` + YAML parsing | MIT ✅ | 1-2 days |
| 4 | **CISA Advisories** | ~500+ recent advisories | Government threat advisories, IOCs, mitigations | Web scrape (RSS/HTML) | Public domain ✅ | 2-3 days |
| 5 | **CISA KEV Catalog** | ~1,200+ exploited vulnerabilities | CVE records with vendor, product, ransomware flag, remediation deadlines | JSON download | Public domain ✅ | 0.5 day |
**Estimated raw document count: ~6,000+**
#### Supplementary Sources (Opportunistic — add if time permits)
| Source | Why Supplementary | Effort |
|---|---|---|
| **arXiv cs.CR preprints** | Open access academic research; useful for methodology depth | Medium (PDF parsing needed) |
| **YARA rules (YARA-Forge, awesome-yara)** | Complements Sigma for file-based detection | Low (structured YAML/text) |
| **StackExchange InfoSec** | Real Q&A pairs; CC BY-SA 4.0 | Medium (API + filtering) |
| **OSSEM** (Open Source Security Events Metadata) | Event schema documentation | Low (GitHub markdown) |
> [!IMPORTANT]
> **Do not collect from:** ScienceDirect (restrictive Elsevier ToS), paywalled sources, or sources requiring authentication. Stick to the 5 primary sources. They provide more than enough volume for 15-20K instruction pairs.
### 2.3 Pipeline Architecture
The collection pipeline is built as a set of independent, re-runnable Python scripts under a unified project structure.
```
dfir-dataset/
├── README.md
├── pyproject.toml
├── .env.example                    # API keys, output paths
│
├── collectors/                     # Phase 2: Source collection
│   ├── __init__.py
│   ├── base.py                     # BaseCollector ABC
│   ├── mitre_attack.py             # MITRE ATT&CK STIX collector
│   ├── sigma_rules.py              # SigmaHQ YAML collector
│   ├── atomic_red_team.py          # Atomic Red Team YAML collector
│   ├── cisa_advisories.py          # CISA advisory scraper
│   └── cisa_kev.py                 # CISA KEV catalog collector
│
├── synthesizers/                   # Phase 3: Instruction pair generation
│   ├── __init__.py
│   ├── base.py                     # BaseSynthesizer ABC
│   ├── teacher.py                  # Frontier model synthesis driver
│   ├── prompts/                    # Prompt templates by category
│   │   ├── artifact_analysis.md
│   │   ├── ttp_identification.md
│   │   ├── triage_decision.md
│   │   ├── detection_engineering.md
│   │   └── report_generation.md
│   └── formatters/                 # Output formatting
│       ├── chat_template.py        # Format for SFT training
│       └── evaluation.py           # Format for eval benchmarks
│
├── quality/                        # Phase 4: Quality assurance
│   ├── __init__.py
│   ├── scorer.py                   # Automated quality scoring
│   ├── filters.py                  # Threshold-based filtering
│   ├── dedup.py                    # Near-duplicate detection
│   ├── validators/
│   │   ├── mitre_validator.py      # ATT&CK technique ID validation
│   │   └── tool_validator.py       # Tool/command name validation
│   └── reports/                    # QA audit reports
│       └── distribution_audit.py   # Category/difficulty balance checks
│
├── packaging/                      # Phase 5: Dataset packaging
│   ├── __init__.py
│   ├── splitter.py                 # Train/val/test split by source doc
│   ├── exporter.py                 # Export to HuggingFace format
│   └── dataset_card.py             # Auto-generate dataset card
│
├── evaluation/                     # Phase 6: Benchmark
│   ├── __init__.py
│   ├── benchmark_runner.py         # Run model against eval set
│   └── metrics.py                  # Scoring functions
│
├── scripts/                        # Entry points
│   ├── collect_all.py              # Run all collectors
│   ├── synthesize.py               # Run synthesis pipeline
│   ├── filter_and_package.py       # QA + packaging
│   ├── run_evaluation.py           # Run benchmark
│   └── full_pipeline.py            # End-to-end: collect → package
│
├── data/                           # Output directory (gitignored)
│   ├── raw/                        # Raw collected documents
│   │   ├── mitre_attack/
│   │   ├── sigma_rules/
│   │   ├── atomic_red_team/
│   │   ├── cisa_advisories/
│   │   └── cisa_kev/
│   ├── synthesized/                # Generated instruction pairs
│   ├── filtered/                   # Quality-filtered pairs
│   ├── packaged/                   # Final train/val/test splits
│   └── evaluation/                 # Benchmark results
│
├── configs/                        # Pipeline configuration
│   ├── collection.yaml             # Source URLs, paths, filters
│   ├── synthesis.yaml              # Model, temperature, batch size
│   ├── quality.yaml                # Score thresholds, filter rules
│   └── packaging.yaml              # Split ratios, output format
│
└── docs/                           # Handover documentation
    ├── ARCHITECTURE.md             # Pipeline design decisions
    ├── ADDING_SOURCES.md           # How to add a new collector
    ├── PROMPT_GUIDE.md             # How to write/iterate synthesis prompts
    ├── QUALITY_RUBRIC.md           # Scoring criteria explained
    └── HANDOVER.md                 # Full handover document for successor
```
> [!TIP]
> **Why this structure matters for handover:** Your colleague can add a new source by creating one file in `collectors/`, adding one prompt in `synthesizers/prompts/`, and running `full_pipeline.py`. No architectural changes needed.
### 2.4 Raw Document Schema
Every collector outputs documents in a standardized JSON Lines format:
```json
{
  "doc_id": "mitre-attack-T1059.001",
  "source": "mitre_attack",
  "source_url": "https://attack.mitre.org/techniques/T1059/001/",
  "title": "Command and Scripting Interpreter: PowerShell",
  "date_collected": "2026-06-18",
  "date_published": "2024-04-23",
  "content_type": "technique_definition",
  "content_markdown": "...",
  "metadata": {
    "mitre_id": "T1059.001",
    "tactic": ["execution"],
    "platforms": ["Windows"],
    "data_sources": ["Process: Process Creation", "Command: Command Execution"],
    "detection": "...",
    "procedures": ["..."]
  },
  "license": "Apache-2.0",
  "word_count": 1850
}
```
### 2.5 Collector Design: BaseCollector
Each collector implements a simple interface:
```python
from abc import ABC, abstractmethod
from pathlib import Path
class BaseCollector(ABC):
    """Base class for all source collectors."""
    @abstractmethod
    def collect(self, output_dir: Path) -> int:
        """Collect documents and write to output_dir as JSONL.
        
        Returns the number of documents collected.
        """
        ...
    @abstractmethod
    def validate(self, output_dir: Path) -> dict:
        """Validate collected data integrity.
        
        Returns a validation report dict with counts, 
        errors, and warnings.
        """
        ...
    def manifest(self) -> dict:
        """Return collector metadata for reproducibility."""
        return {
            "collector": self.__class__.__name__,
            "version": self.VERSION,
            "source_url": self.SOURCE_URL,
            "license": self.LICENSE,
            "collected_at": datetime.utcnow().isoformat(),
        }
```
### 2.6 Collector Implementation Notes
#### MITRE ATT&CK Collector
```python
# Uses mitreattack-python to pull from STIX
# Collects: techniques, sub-techniques, procedures, mitigations, data sources
# Scope: Enterprise ATT&CK matrix only (Phase 2)
# Future: ICS ATT&CK and Mobile ATT&CK matrices (deferred to successor)
# Output: one document per technique/sub-technique
# Enrichment: link procedures to technique, include detection guidance
# Expected yield: ~800 documents (Enterprise only)
```
Key fields to extract per technique:
- Technique ID, name, description
- Tactic(s)
- Platforms
- Data sources for detection
- Procedure examples (from groups/software)
- Detection guidance
- Mitigations
#### SigmaHQ Collector
```python
# Clones SigmaHQ/sigma repo, parses YAML rules
# Collects: rule YAML + metadata (title, description, references, tags, logsource, detection)
# Output: one document per rule
# Enrichment: extract ATT&CK tags, log source requirements
# Expected yield: ~3,000+ documents
```
Key fields to extract per rule:
- Rule title, description, author
- Log source (product, category, service)
- Detection logic (selection, condition, filters)
- ATT&CK tags
- Level (informational, low, medium, high, critical)
- References (external links)
- False positive notes
#### Atomic Red Team Collector
```python
# Clones redcanaryco/atomic-red-team repo, parses YAML atomics
# Collects: test definitions per ATT&CK technique
# Output: one document per atomic test
# Enrichment: link to ATT&CK technique, include executor commands and cleanup
# Expected yield: ~800+ documents
```
Key fields to extract per test:
- ATT&CK technique ID
- Test name, description
- Supported platforms
- Executor type (command_prompt, powershell, bash, etc.)
- Attack commands
- Cleanup commands
- Input arguments
- Dependencies
#### CISA Advisories Collector
```python
# Scrapes CISA.gov advisories and alerts
# Collects: advisory text, IOCs, affected products, mitigations
# Output: one document per advisory
# Enrichment: extract CVEs, IOCs, affected software
# Expected yield: ~500+ documents
```
Key fields to extract:
- Advisory ID, title, date
- Affected products/vendors
- CVE references
- IOCs (IPs, domains, hashes, file paths)
- Recommended mitigations
- MITRE ATT&CK mappings (when provided)
#### CISA KEV Catalog Collector
```python
# Downloads CISA Known Exploited Vulnerabilities JSON catalog
# Collects: CVE records with vendor, product, remediation, ransomware flag
# Output: one document per vendor group (entries grouped by vendorProject)
# Enrichment: ransomware campaign flag, remediation deadlines, product lists
# Expected yield: ~200-300 documents (from ~1,200+ KEV entries)
```
Key fields to extract per vendor group:
- Vendor name, product list
- CVE IDs, descriptions
- Dates added to catalog
- Known ransomware campaign use flag
- Required remediation actions
- Due dates (federal agency deadlines)
### Phase 2 Deliverables
- [ ] `BaseCollector` ABC and common utilities
- [ ] MITRE ATT&CK collector — working and tested
- [ ] SigmaHQ collector — working and tested
- [ ] Atomic Red Team collector — working and tested
- [ ] CISA Advisories collector — working and tested
- [ ] CISA KEV catalog collector — working and tested
- [ ] `collect_all.py` script that runs all collectors and produces a manifest
- [ ] Validation: all 5 collectors produce valid JSONL with complete metadata
- [ ] Raw corpus: ~6,000+ documents in `data/raw/`
---
## Phase 3: Instruction Pair Synthesis (Week 5 Day 3 – Week 7)
### 3.1 Strategy: Single-Pass Teacher Synthesis with Category-Specific Prompts
Use a frontier model to generate instruction pairs from raw documents. Each task category has its own carefully designed prompt template that produces pairs matching that category's requirements.
```
                                ┌─────────────────────┐
                                │  Prompt Template     │
                                │  (per category)      │
                                └─────────┬───────────┘
                                          │
Raw Document ──→ Teacher Model ──→ Instruction Pairs ──→ data/synthesized/
                 (Claude Sonnet       (3-5 per doc)
                  or GPT-4o)
```
### 3.2 Synthesis Model Selection
| Model | Cost (per 1M tokens) | Quality | Recommendation |
|---|---|---|---|
| Gemini 2.5 Flash | ~$0.15 input / $0.60 output | Medium-High | ✅ **Selected** — sufficient quality for structured DFIR pairs at 20x lower cost, quality filtering downstream catches weak pairs |
| Claude 4 Sonnet | ~$3 input / $15 output | High | Fallback — only if Gemini Flash pilot pass rate is consistently below quality threshold |
| GPT-4o | ~$2.50 input / $10 output | High | Not used |
> [!NOTE]
> **Decision rationale:** Research (LIMA, DEITA, WizardLM/Evol-Instruct) shows that data diversity and quality filtering matter more than raw model capability for SFT data generation. Gemini 2.5 Flash provides sufficient diversity at ~$9 total cost. The Phase 4 quality pipeline (MITRE validator, tool validator, scoring rubric) catches any quality issues downstream. Only one API account (Google AI) is needed.
### 3.3 Prompt Templates
Each category gets a dedicated prompt template. All templates share a common structure but differ in their task-specific instructions and output expectations.
#### Common Template Structure
```markdown
## System Prompt
You are an expert DFIR practitioner and cybersecurity instructor creating 
training data for a specialized forensic AI assistant called Shepherd.
Shepherd helps investigators:
- Triage evidence from uploaded artifacts
- Understand forensic tool output (especially Volatility 3)
- Identify suspicious indicators and map them to MITRE ATT&CK
- Decide what to investigate next
- Write cautious, evidence-backed reports
Your job is to generate realistic instruction-response pairs that teach 
Shepherd how to reason about DFIR problems step-by-step.
## Rules
1. Instructions must sound like real questions from a SOC analyst or 
   incident responder during an active investigation
2. Responses MUST include explicit reasoning steps before the final answer
3. Reference specific tools, artifact locations, and evidence types
4. Map behaviors to MITRE ATT&CK technique IDs where applicable
5. Include caveats and uncertainty — real DFIR involves ambiguity
6. NEVER declare compromise without corroborating evidence
7. Vary difficulty: 30% junior-level, 50% mid-level, 20% senior-level
## Task Category: {category_name}
{category_specific_instructions}
## Source Document
{document_content}
## Output Format
Generate {n} instruction-response pairs as a JSON array:
[
  {
    "instruction": "...",
    "thinking": "step-by-step reasoning the model should perform",
    "response": "the final answer incorporating the reasoning",
    "category": "{category_name}",
    "difficulty": "junior|mid|senior",
    "mitre_techniques": ["T1xxx.xxx", ...],
    "tools_referenced": ["...", ...],
    "source_doc_id": "{doc_id}"
  }
]
```
#### Category-Specific Instructions (Summaries)
**Artifact Analysis (incl. Deep Forensics):**
Focus on interpreting forensic tool output across all depth levels. Generate questions about what specific artifacts mean, what's normal vs suspicious, how to correlate findings across multiple plugins. Include Volatility (pslist, pstree, cmdline, malfind, vadinfo, handles, hivelist, printkey, shimcachemem), EVTX (logon chains, service installs, PowerShell logging), registry (persistence keys, service creation), and filesystem artifacts (prefetch, MFT, ADS, $UsnJrnl). Vary depth from surface-level field interpretation (junior) to multi-artifact correlation and injection detection reasoning (senior).

**TTP Identification:**
Focus on mapping observed behaviors to ATT&CK techniques. Generate questions that present a scenario and ask the model to identify the technique, explain why, and suggest related techniques that might also be present.

**Triage Decision-Making:**
Focus on investigation prioritization. Present a set of initial indicators and ask the model to rank next steps, justify priorities, identify evidence gaps, and recommend what artifact to examine next.

**Detection Engineering:**
Focus on detection rule creation and interpretation. Generate questions about Sigma rule logic, ask for rule translations between query languages, explain detection coverage and gaps.

**Incident Report Generation:**
Focus on producing analyst-facing summaries. Present raw findings and ask the model to write a professional investigation summary with evidence citations, confidence levels, caveats, and recommended next steps.

### 3.4 Synthesis Pipeline Configuration
```yaml
# configs/synthesis.yaml
model:
  primary: "gemini-2.5-flash"      # Sole model — sufficient quality at ~$9 total
  fallback: "claude-sonnet-4"      # Only if Flash pilot pass rate < 65%
generation:
  pairs_per_document:
    mitre_attack: 5        # Rich source, generate more
    sigma_rules: 3         # Structured but narrow
    atomic_red_team: 4     # Good for TTP + detection pairs
    cisa_advisories: 5     # Rich narrative content
  temperature: 0.7
  max_retries: 2
  batch_size: 20           # Documents per API batch
  category_distribution:   # Target mix per batch (adjusted for deep forensics)
    artifact_analysis: 0.30      # Increased from 0.25 to accommodate deep forensics sub-categories
    ttp_identification: 0.25     # Unchanged
    triage_decision: 0.18        # Slightly reduced
    detection_engineering: 0.14  # Slightly reduced
    report_generation: 0.13     # Slightly reduced
  difficulty_distribution:
    junior: 0.30
    mid: 0.50
    senior: 0.20
output:
  format: "jsonl"
  dir: "data/synthesized/"
  manifest: true           # Write generation manifest per batch
```
### 3.5 Volume Targets
| Source | Raw Documents | Pairs per Doc | Total Pairs | Notes |
|---|---|---|---|---|
| MITRE ATT&CK | ~800 | 5 | ~4,000 | Highest quality source |
| SigmaHQ Rules | ~3,000 | 3 | ~9,000 | Largest volume source |
| Atomic Red Team | ~800 | 4 | ~3,200 | Strong for TTP + detection |
| CISA Advisories | ~500 | 5 | ~2,500 | Good for triage + reporting |
| **Total** | **~5,100** | | **~18,700** | |
| **After quality filtering (~70% pass rate)** | | | **~13,000** | Target: 10,000-15,000 |
### 3.6 Cost Estimate
| Scenario | Input Tokens | Output Tokens | Estimated Cost |
|---|---|---|---|
| Pilot (100 docs, Gemini 2.5 Flash) | ~400K | ~200K | ~$0.18 |
| Full run (5,100 docs, Gemini 2.5 Flash) | ~20M | ~10M | ~$9 |
| 3× full re-runs (prompt iteration) | ~60M | ~30M | ~$27 |
| **Expected total (1 pilot + 1-2 full runs)** | | | **~$9-18** |
> [!NOTE]
> These costs assume an average of ~4K input tokens and ~2K output tokens per document. Gemini 2.5 Flash is cheap enough to re-run the entire pipeline multiple times during prompt iteration — no need to ration API calls.
### 3.7 Pilot Protocol (Week 5, Days 3-5)
Before running the full synthesis:
1. **Select 25 documents per source** (100 total) — balanced across content types
2. **Run synthesis with Gemini 2.5 Flash** — all 5 prompt templates (including deep forensics artifact analysis)
3. **Manually review 100% of pilot output** (~400 pairs)
4. **Score each pair** on the 5-point rubric (see Phase 4)
5. **Iterate on prompts** — fix systematic issues (vague instructions, missing ATT&CK IDs, overclaiming, etc.)
6. **Re-run pilot** if pass rate < 60% — re-runs cost ~$0.18 each, so iterate aggressively
7. **Document prompt changes** in version-controlled prompt files
**Gate:** Do not proceed to full synthesis until pilot pass rate ≥ 65% on the quality rubric. If Gemini Flash consistently fails to meet this threshold after 3+ prompt iterations, escalate to Claude Sonnet as fallback.
### Phase 3 Deliverables
- [ ] 5 prompt templates (one per category) — tested and iterated via pilot
- [ ] Synthesis pipeline script (`synthesize.py`) — handles batching, retries, rate limits
- [ ] Pilot results documented with quality scores
- [ ] Full synthesis run complete: ~18,000 raw instruction pairs in `data/synthesized/`
- [ ] Generation manifest: model, prompts used, costs, timestamp per batch
---
## Phase 4: Quality Assurance (Week 7 – Week 8 Day 3)
### 4.1 Automated Quality Scoring
Every generated pair is scored on 5 criteria (1-5 scale):
| Criterion | Weight | What It Measures | Automated? |
|---|---|---|---|
| **Factual Accuracy** | 25% | Reasoning is technically correct for the domain | Partial — validate ATT&CK IDs, tool names |
| **Reasoning Quality** | 25% | Chain-of-thought is logical, complete, step-by-step | Yes — check for reasoning markers, step count |
| **Operational Relevance** | 20% | A real DFIR practitioner would ask this question | Heuristic — check for tool/artifact references |
| **Specificity** | 15% | Avoids vague/generic responses | Yes — check response length, named entity count |
| **Completeness** | 15% | Includes ATT&CK mappings, caveats, next steps where appropriate | Yes — check for required fields |
**Composite score = weighted average. Threshold: ≥ 3.5 to pass.**
### 4.2 Automated Validators
#### MITRE ATT&CK Validator
```python
# Validates that all referenced technique IDs exist in ATT&CK
# Cross-references technique-to-tactic mappings
# Flags deprecated techniques
# Source: mitreattack-python STIX data (already collected)
```
#### Tool Name Validator
```python
# Validates that referenced tools are real DFIR tools
# Maintains an allowlist of known tools
# Flags hallucinated tool names
# Allowlist: Volatility, Autopsy, KAPE, Velociraptor, Sigma, YARA, 
#            Wireshark, strings, etc.
```
#### Structural Validator
```python
# Checks JSON schema compliance
# Verifies required fields are present and non-empty
# Checks difficulty label is valid
# Checks category label matches expected set
```
### 4.3 Near-Duplicate Detection
Use `datasketch` MinHash to detect near-duplicate instruction pairs:
- **Threshold:** Jaccard similarity > 0.8 = duplicate
- **Scope:** Within each category (cross-category duplicates are acceptable)
- **Action:** Keep the higher-scoring pair, discard the other
### 4.4 Distribution Audit
After filtering, verify the dataset isn't skewed:
```python
# Check category distribution (target: within ±5% of plan)
# Check difficulty distribution (target: 30/50/20 ±5%)
# Check MITRE tactic coverage (all 14 tactics represented)
# Check source balance (no single source > 50%)
# Check response length distribution (flag outliers)
```
If any axis is severely skewed, generate additional pairs for underrepresented categories using targeted synthesis runs.
### 4.5 Manual Spot-Check Protocol
- **Sample:** 100 randomly selected pairs from the quality-filtered set
- **Reviewer:** You (and mentor/team if available)
- **Process:** Score each pair on the same 5-point rubric used for automated scoring
- **Goal:** Validate that automated scores correlate with human judgment
- **Document:** Record inter-rater agreement if multiple reviewers
> [!WARNING]
> **If manual scores diverge significantly from automated scores** (Cohen's κ < 0.4), your automated scorer needs recalibration. Do not skip this step — it's your quality insurance.
### Phase 4 Deliverables
- [ ] Automated quality scorer (`scorer.py`) — scores all pairs on 5 criteria
- [ ] MITRE ATT&CK validator — flags invalid technique IDs
- [ ] Tool name validator — flags hallucinated tools
- [ ] Near-duplicate detector — removes duplicates within categories
- [ ] Distribution audit report — confirms balanced dataset
- [ ] Manual spot-check results — 100 pairs reviewed with scores
- [ ] Filtered dataset: ~10,000-15,000 quality pairs in `data/filtered/`
---
## Phase 5: Dataset Packaging (Week 8, Days 3-5)
### 5.1 Output Schema
The final dataset is packaged in JSON Lines format, stored locally on the DGX Sparks filesystem and loaded via `datasets.load_dataset("json", data_files=...)` for Unsloth training:
```json
{
  "id": "dfir-00001",
  "conversations": [
    {
      "role": "system",
      "content": "You are Shepherd, a DFIR AI assistant specialized in digital forensics, incident response, and threat hunting. You help investigators analyze evidence, identify threats, and make investigation decisions. Always reason step-by-step, cite evidence, map to MITRE ATT&CK where applicable, and include caveats about confidence levels."
    },
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "<think>\n{step-by-step reasoning}\n</think>\n\n{final response}"
    }
  ],
  "metadata": {
    "category": "artifact_analysis",
    "difficulty": "mid",
    "mitre_techniques": ["T1059.001", "T1055"],
    "tools_referenced": ["Volatility 3", "strings"],
    "source_doc_id": "mitre-attack-T1059.001",
    "source": "mitre_attack",
    "quality_score": 4.2
  }
}
```
> [!IMPORTANT]
> The `<think>...</think>` wrapper in the assistant response teaches the model to use GLM-4.7-Flash's reasoning/thinking mode. This format is critical — it trains the model to show its work, which is essential for forensic trustworthiness and aligns with Shepherd's Reviewer Agent (which checks for overclaiming).
### 5.2 Train/Validation/Test Split
| Split | Proportion | Estimated Size | Purpose |
|---|---|---|---|
| Train | 80% | ~8,000-12,000 | Fine-tuning |
| Validation | 10% | ~1,000-1,500 | Hyperparameter tuning, early stopping |
| Test | 10% | ~1,000-1,500 | Final evaluation (never seen during training) |
**Split strategy:** Split by **source document ID**, not by individual pairs. All pairs generated from the same source document go into the same split. This prevents data leakage.
### 5.3 Dataset Card
Auto-generate a dataset card covering:
- Dataset description and intended use
- Source breakdown with licensing
- Generation methodology (models used, prompt versions, quality thresholds)
- Task category and difficulty distribution (with charts)
- MITRE ATT&CK tactic coverage map
- Known limitations and biases
- Ethical considerations (no active malware, no real victim data, no PII)
- Reproduction instructions (`python scripts/full_pipeline.py`)
### Phase 5 Deliverables
- [ ] Chat-formatted JSONL files for train/val/test splits
- [ ] Dataset card (auto-generated markdown + manually reviewed) — stored alongside dataset on DGX
- [ ] Dataset stored locally on DGX Sparks at versioned path (e.g., `/data/dfir-dataset/v1.0/`)
- [ ] `load.py` thin wrapper providing `datasets.Dataset` interface from local files
- [ ] Version tag: `v1.0.0`
- [ ] Reproduction instructions tested end-to-end
- [ ] Data path and loading instructions documented in `HANDOVER.md`
---
## Phase 6: Fine-Tuning Validation (Weeks 9-10)
> [!NOTE]
> This phase validates that the dataset produces measurable improvement. It is NOT about producing the final production model — that's iterative work for your successor.
### 6.1 Training Setup
| Parameter | Value | Rationale |
|---|---|---|
| **Platform** | DGX Sparks (128GB unified memory) | More than sufficient for 30B MoE |
| **Framework** | Unsloth | Native GLM-4.7-Flash support, memory-efficient |
| **Method** | LoRA SFT | DGX Sparks has headroom for full LoRA, no need for QLoRA |
| **LoRA rank** | 32-64 | Start with 32, increase if underfitting |
| **LoRA alpha** | 64-128 | Typically 2× rank |
| **Learning rate** | 2e-5 | Standard for LoRA SFT |
| **Epochs** | 2-3 | Small dataset, avoid overfitting |
| **Batch size** | Tune to fill memory | Unsloth auto-optimizes this |
| **Warmup** | 10% of steps | Standard |
| **Scheduler** | Cosine | Standard |
### 6.2 Training Protocol
1. **Run 1 (Day 1-2):** Train with default hyperparameters. Evaluate.
2. **Analyze results (Day 2-3):** Identify where the model improved and where it didn't.
3. **Run 2 (Day 3-4):** Adjust LoRA rank or learning rate if needed. Evaluate.
4. **Export (Day 4-5):** Convert best checkpoint to GGUF for llama.cpp deployment.
5. **Integration test (Day 5-6):** Swap into Shepherd's llama.cpp backend, run memory triage workflow.
### 6.3 Evaluation Benchmark
Build a small, hand-curated benchmark of **50-100 test examples** that are:
- **NOT generated by the synthesis pipeline** (avoids measuring synthesis quality instead of model quality)
- **Manually written** based on real DFIR scenarios you understand
- **Balanced** across the 5 task categories
- **Difficulty-tiered** to test junior through senior capabilities
#### Evaluation Metrics
| Task Type | Metric | How Measured |
|---|---|---|
| TTP Identification | F1 Score | Compare predicted ATT&CK IDs against ground truth |
| IOC Extraction | Precision / Recall | Extract IOCs from text, compare against labeled set |
| Triage Ranking | NDCG@5 | Compare investigation step rankings |
| Detection Rule Interpretation | Accuracy | Multiple-choice on rule behavior |
| Report Quality | LLM-as-Judge (1-5) | Use frontier model to score report quality |
| Reasoning Quality | LLM-as-Judge (1-5) | Use frontier model to score reasoning chain |
#### Before/After Comparison
| Model | Eval Score | Notes |
|---|---|---|
| GLM-4.7-Flash (base) | ? | Baseline — run before any fine-tuning |
| GLM-4.7-Flash (fine-tuned v1) | ? | After training on dataset v1.0 |
> [!IMPORTANT]
> **Run the baseline evaluation BEFORE fine-tuning.** You need the "before" score to demonstrate improvement. Do this on Day 1 of Week 9.
### Phase 6 Deliverables
- [ ] Hand-curated evaluation benchmark (50-100 examples)
- [ ] Baseline scores on un-finetuned GLM-4.7-Flash
- [ ] Fine-tuned model checkpoint (LoRA adapter)
- [ ] Fine-tuned model exported to GGUF
- [ ] Before/after evaluation comparison
- [ ] Integration test: fine-tuned model running in Shepherd via llama.cpp
- [ ] Training recipe documented (exact config, hyperparameters, results)
---
## Handover Package
When the internship ends, deliver the following to your successor:
### Code
- [ ] `dfir-dataset/` repo — all collection, synthesis, QA, and packaging code
- [ ] Shepherd repo — tagged at `v0.2.0` with `PAUSE_STATE.md`
- [ ] Fine-tuned model checkpoint + GGUF export
### Documentation
- [ ] `HANDOVER.md` — what's done, what's next, known issues, decision rationale
- [ ] `ARCHITECTURE.md` — pipeline design decisions and tradeoffs
- [ ] `ADDING_SOURCES.md` — step-by-step guide for adding new data sources
- [ ] `PROMPT_GUIDE.md` — how to iterate on synthesis prompts
- [ ] Dataset card (markdown, stored alongside dataset on DGX)
- [ ] Training recipe document
### Recommended Next Steps for Successor
| Priority | Task | Why |
|---|---|---|
| 1 | Add Tier 2 sources (public threat intel blogs: Mandiant, CrowdStrike, Unit 42) | Increases dataset diversity and operational realism |
| 2 | Expand MITRE ATT&CK collection to ICS and Mobile matrices | ICS covers OT/SCADA environments; Mobile covers endpoint threats on managed devices. Both use the same `mitreattack-python` STIX API — only the STIX JSON URL changes |
| 3 | Expand to 10 task categories (add malware analysis, memory forensics, etc.) | Covers the full Shepherd specialist agent roster |
| 4 | Implement two-pass teacher-verifier synthesis | Improves quality ceiling |
| 5 | Scale to 50K+ pairs | Better model performance with more data |
| 6 | Implement CRAFT/RAFT after Shepherd has a RAG layer (MVP 4) | Trains model to work with retrieved documents |
| 7 | Build continuous evaluation pipeline | Measures improvement across dataset iterations |
---
## Risk Register
| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Synthesis prompt quality is poor, producing low-signal pairs | High | Medium | Pilot protocol (100 docs) validates prompts before full run. Gemini Flash is cheap enough to re-run pilots aggressively (~$0.18 each) |
| Gemini Flash quality insufficient for reasoning chains | Medium | Low | Escalate to Claude Sonnet as fallback if pilot pass rate stays below 65% after 3+ iterations. Budget impact: ~$210 if full fallback needed |
| Quality filtering removes too many pairs (< 60% pass rate) | High | Low | Iterate on prompts, not thresholds. If prompts are good, pass rate should be ≥ 70% |
| Fine-tuned model shows no improvement over base | High | Medium | This indicates dataset issues, not training issues. Document gaps for successor |
| CISA scraper breaks due to site changes | Low | Medium | CISA is supplementary; can be dropped without impact |
| Time overrun on Phase 2 (collection) | Medium | Low | Primary sources are structured and API-accessible — collection is the easiest phase |
| Time overrun on Phase 3 (synthesis) | Medium | Low | Gemini Flash eliminates API cost/speed concerns. Full run completes in hours, not days. Re-runs are cheap |
| Deep forensics sub-categories lack source coverage | Low | Low | MITRE ATT&CK T1055.* and Sigma rules cover memory injection well. Gap may exist for advanced registry/MFT — supplement with targeted source collection if needed |
---
## Week-by-Week Schedule
| Week | Dates | Phase | Key Activities | Gate |
|---|---|---|---|---|
| **3** | Jun 15-21 | Phase 1 + Phase 2 start | Finalize taxonomy. Build `BaseCollector`. Implement MITRE ATT&CK + Sigma collectors | Taxonomy reviewed |
| **4** | Jun 22-28 | Phase 2 | Implement Atomic RT + CISA collectors. Run all collectors. Validate raw corpus | ~5,000 docs collected |
| **5** | Jun 29 - Jul 5 | Phase 2 finish + Phase 3 start | Finalize collection. Design prompt templates. **Run pilot (100 docs)** | Pilot pass rate ≥ 65% |
| **6** | Jul 6-12 | Phase 3 | Full synthesis run (batched). Monitor quality per batch | ~18,000 raw pairs |
| **7** | Jul 13-19 | Phase 3 finish + Phase 4 | Finish synthesis. Build quality scorer. Run automated filtering | Filtered set ≥ 10,000 pairs |
| **8** | Jul 20-26 | Phase 4 finish + Phase 5 | Manual spot-check. Distribution audit. Package dataset locally on DGX | Dataset v1.0.0 tagged |
| **9** | Jul 27 - Aug 2 | Phase 6 | Baseline eval. Training run 1. Analyze results. Training run 2 | Before/after scores |
| **10** | Aug 3-7 | Phase 6 finish + Handover | GGUF export. Integration test in Shepherd. Write handover docs | Handover package complete |
---
## Resolved Decisions (formerly Open Questions)
> Resolved 2026-06-02.
1. **API access:** ✅ Setting up a Google AI account for Gemini 2.5 Flash. Single model, single account. No Claude/GPT-4o accounts needed unless Flash quality is insufficient (fallback plan documented in §3.7).
2. **Dataset hosting:** ✅ Local-only on DGX Sparks filesystem. No HuggingFace. Data loaded via `datasets.load_dataset("json", data_files=...)` — functionally identical to HF hosting for Unsloth training. Data path documented in `HANDOVER.md` for successor.
3. **Shepherd MVP 2 status:** ✅ 3 core MVP 2 items remaining (process_plugin_mismatch finding, report provenance citations, parser/finding tests). 5 refactor gate items deferred to v0.2.1. Tag v0.2.0 after the 3 core items are complete.
4. **Scope:** ✅ 5 task categories confirmed. Artifact Analysis expanded with 6 deep forensics sub-categories (memory structure analysis, handle/object analysis, registry forensics, filesystem artifact analysis, event log analysis). Category distribution adjusted: artifact_analysis 30%, ttp_identification 25%, triage_decision 18%, detection_engineering 14%, report_generation 13%.
5. **DGX Sparks access:** ✅ Dedicated. No scheduling conflicts. Can run 3-4 LoRA rank experiments (16, 32, 64, 128) during weeks 9-10.
6. **Synthesis approach:** ✅ Full LLM generation using Gemini 2.5 Flash for all pairs (~$9 total). No hybrid/template approach — research (LIMA, DEITA, Evol-Instruct) shows diversity from LLM generation outperforms template-based data for SFT, and the cost difference is negligible at Flash pricing.