# Project 1: Building a Production-Grade DFIR Training Dataset

## Context

This project is part of a summer internship (May 11 – Aug 7, extendable) building **Shepherd**, a local on-premise DFIR AI investigation assistant. The project will be handed over to a full-time colleague, and the team intends to expand it for real operations.

The primary deliverable is not just a dataset — it is a **re-runnable dataset factory**: a documented, reproducible pipeline that the successor can iterate on, expand, and re-generate as the project evolves.

### Relationship to Shepherd

This dataset is designed to fine-tune the model powering Shepherd's reasoning layer. The task taxonomy is directly aligned with Shepherd's specialist agent architecture:

| Shepherd Component | Dataset Focus Area |
|---|---|
| Memory Agent | Volatility output interpretation, process triage, injection detection |
| Windows Event Log Agent | EVTX analysis, logon/auth event chain reasoning |
| Report Agent | Forensic report generation with evidence citations |
| Reviewer Agent | Overclaim detection, confidence calibration |
| Capability registry | Maps to instruction pair categories |

### Hardware

- **Training platform:** NVIDIA DGX Sparks (GB10 Grace Blackwell, 128GB unified memory)
- **Fine-tuning method:** LoRA SFT via Unsloth (CRAFT/RAFT deferred until Shepherd has a RAG layer)
- **Base model:** GLM-4.7-Flash (30B MoE, 3B active parameters)

### Timeline Position

| Weeks | Phase | This Document Covers |
|---|---|---|
| 1-2 (Jun 1-14) | Close Shepherd MVP 2, tag v0.2.0 | — |
| **3-8 (Jun 15 - Jul 26)** | **DFIR Dataset Pipeline** | **✅ This is the plan** |
| 9-10 (Jul 27 - Aug 7) | Fine-tune + evaluate on DGX Sparks | Validation phase |

---

## Phase 1: DFIR Artifact Taxonomy & Task Categories (Week 3, Days 1-3)

### 1.1 Complete DFIR Artifact Taxonomy

This taxonomy defines the full landscape of forensic artifacts the model should eventually understand. It serves two purposes:

1. **For this internship:** Identifies which artifact categories to cover now
2. **For the successor:** Provides the systematic expansion roadmap

#### Taxonomy Reference Sources

The following structured community sources should be consulted during Phase 1 to validate and refine the 57-category taxonomy. These are not collected during Phase 1 — they are used as cross-references to ensure the taxonomy accurately reflects the forensic artifact landscape.

| Source | What It Provides | How to Use in Phase 1 |
|---|---|---|
| **ForensicArtifacts/artifacts** (`ForensicArtifacts/artifacts`) | ~500+ machine-readable YAML forensic artifact definitions. Used by GRR, Plaso, and other major tools. Covers Windows, Linux, macOS artifact paths, registry keys, and WMI queries. Apache 2.0. | Cross-reference against W1-W10, L1-L8 categories to identify missing artifact types. Validate that artifact paths/registry keys in example tasks are accurate. |
| **MITRE ATT&CK Data Sources & Data Components** | ~40 data sources (Process, File, Network Traffic, etc.) mapped to ~100 data components (Process Creation, File Modification, etc.), which in turn map to techniques. Available via `mitreattack-python` STIX API. | Systematically validate §1.3 coverage mapping by checking which data sources/components each taxonomy category corresponds to. Identify artifact categories that map to zero data components (potential coverage gaps). |
| **OSSEM Data Dictionaries** (`OTRF/OSSEM-DD`) | Field-level documentation for Windows Security events, Sysmon events, and other log sources. MIT license. | Enrich event log categories (W8, W10, S1) with concrete field names and event structures for more realistic example tasks. |
| **Sigma logsource taxonomy** (within `SigmaHQ/sigma`) | Structured log source definitions by `product`, `category`, and `service`. | Run a distribution analysis of Sigma's logsource tags to empirically validate which artifact categories have strong vs weak detection rule coverage, rather than estimating §1.3 by hand. |

> [!WARNING]
> **ATT&CK Data Sources deprecation:** MITRE deprecated Data Sources in ATT&CK v18 (October 2025), replacing them with **Detection Strategies**, **Analytics**, and **Data Components** under a new `/detectionstrategies/` and `/datacomponents/` hierarchy. The legacy Data Sources page remains available for reference but will not receive updates. Despite the deprecation, the existing ~40 data sources and ~100 data components still provide the most complete structured mapping between "what forensic telemetry exists" and "what techniques it can detect." We use them as a **static taxonomy cross-reference** during Phase 1, not as a live data feed — so the deprecation does not affect their value here. The C1 collector (Phase 2) should extract both the legacy data sources AND the new Detection Strategies/Data Components to future-proof the dataset.

---

#### Windows Artifacts (W1-W10)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| W1 | **What executed?** | Prefetch, Amcache, ShimCache/AppCompatCache, SRUM, BAM/DAM, UserAssist, RecentApps, Event Logs (Security 4688, Sysmon 1), Memory (pslist, pstree, cmdline) | Prefetch `.pf` files, `Amcache.hve`, `AppCompatCache` registry key, `SRUM.dat` |
| W2 | **How did they persist?** | Registry Run keys, Services (7045), Scheduled Tasks (4698, Sysmon 11), Startup Folder, WMI Event Subscriptions, COM hijacking, DLL search order hijacking, Boot/Logon scripts, AppInit_DLLs, IFEO, BITSAdmin jobs | `NTUSER.DAT\...\Run`, `SYSTEM\CurrentControlSet\Services` |
| W3 | **Who authenticated?** | Event Logs (4624/4625/4634/4647/4648/4672), SAM, LSASS memory, Cached credentials, RDP logs (TerminalServices), NTLM/Kerberos artifacts | `Security.evtx`, SAM hive, Kerberos ticket cache |
| W4 | **What was accessed / modified on disk?** | MFT (`$MFT`), USN Journal (`$UsnJrnl`), `$I30` directory index, NTFS ADS, Zone.Identifier, Shellbags, LNK files, Jump Lists, Recent docs | `$MFT`, `$UsnJrnl:$J`, `*.lnk` files, Shellbags in `UsrClass.dat` |
| W5 | **What happened on the network?** | DNS cache, ARP cache, Browser history/cache/cookies, Event Logs (Sysmon 3, Firewall 5156), BITS transfer logs, Proxy logs, Memory (netscan/netstat) | `Dnscache`, Sysmon Event ID 3 |
| W6 | **What did the user do?** | Registry MRU lists, Typed paths/URLs, Explorer access history, PowerShell history (`ConsoleHost_history.txt`), Clipboard data, RDP bitmap cache, USB device history (SetupAPI) | `NTUSER.DAT` MRU keys, `ConsoleHost_history.txt`, `setupapi.dev.log` |
| W7 | **What's in memory?** | Processes, threads, handles, DLLs (loaded/injected), VADs, network connections, open files, registry hives, code injection artifacts, hooks, credential material, command history, clipboard | Volatility: `pslist`, `pstree`, `malfind`, `dlllist`, `netscan`, `handles`, `filescan`, `svcscan` |
| W8 | **What do the event logs say?** | Security, System, Application, Sysmon, PowerShell (4103/4104), TaskScheduler, WMI-Activity, TerminalServices-RDPClient, Windows Defender, BITS-Client, NTLM, Kerberos | `Security.evtx`, Sysmon Operational, PowerShell Operational |
| W9 | **What happened in Active Directory?** | NTDS.dit, Group Policy Objects, Replication metadata, Kerberos (Golden/Silver tickets, Kerberoasting, AS-REP roasting), SID history, AdminSDHolder, DCShadow/DCSync, Trust relationships | `NTDS.dit`, GPO folders, Event IDs 4662/4769/4771 |
| W10 | **What scripts/commands ran?** | PowerShell logs (4103/4104/ScriptBlock), WMI traces, WSH (cscript/wscript), MSHTA, VBA macro artifacts, BAT/CMD history, encoded command detection | PowerShell ScriptBlock log (4104), Sysmon Event ID 1 |

---

#### Linux Artifacts (L1-L8)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| L1 | **What executed?** | Shell history (`.bash_history`, `.zsh_history`), `auditd` logs (execve), syslog, `journalctl`, process accounting (`pacct`), core dumps, `/proc` (live) | `~/.bash_history`, `/var/log/audit/audit.log` |
| L2 | **How did they persist?** | Cron (`/etc/crontab`, `/var/spool/cron/`, user crontabs), systemd services/timers, `init.d`/`rc.local`, SSH `authorized_keys`, `.bashrc`/`.profile` modifications, `LD_PRELOAD`, PAM modules, kernel modules | `/etc/crontab`, `/etc/systemd/system/*.service`, `authorized_keys` |
| L3 | **Who authenticated?** | `/var/log/auth.log` (Debian) / `/var/log/secure` (RHEL), `/etc/passwd`, `/etc/shadow`, SSH logs, `sudo` logs, `wtmp`/`btmp`/`utmp`, PAM config, SSSD/LDAP logs, `lastlog`, `faillog` | `/var/log/auth.log`, `/var/log/wtmp` |
| L4 | **What was accessed / modified on disk?** | File timestamps (MACB via `stat`/`find`), inode analysis, `/tmp` and `/dev/shm` contents, package manager logs (`dpkg.log`, `yum.log`/`dnf.log`), integrity checks (`debsums`, `rpm -V`) | `stat` output, `/var/log/dpkg.log` |
| L5 | **What happened on the network?** | `iptables`/`nftables` logs, connection tracking (`conntrack`), `ss`/`netstat`/`lsof` output, `/etc/hosts`, `/etc/resolv.conf`, firewall logs | `/var/log/kern.log` (netfilter), `ss -tulnp` |
| L6 | **What's in the logs?** | `journalctl`/`syslog`/`rsyslog`, application logs (Apache, nginx, MySQL), container logs (Docker `json-file`, K8s pod logs), cloud-init logs, mail logs | `/var/log/syslog`, `/var/log/nginx/access.log` |
| L7 | **What's in memory?** | LiME/AVML memory dumps, `/proc/[pid]/maps`, `/proc/[pid]/cmdline`, `/proc/[pid]/environ`, loaded kernel modules, ptrace injection, `LD_PRELOAD` injection, rootkit detection | LiME `.lime` dump, `/proc/*/maps` |
| L8 | **What about containers / orchestration?** | Docker images/layers/history, container filesystem diffs, Kubernetes audit logs, pod specs, secrets, ConfigMaps, service account tokens, etcd snapshots | `docker history`, `docker diff`, K8s `audit.log` |

---

#### Network Forensics (N1-N6)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| N1 | **What communicated with what?** | Full PCAP, NetFlow/IPFIX, Zeek `conn.log`, firewall flow logs, session reconstruction | `.pcap`/`.pcapng`, Zeek `conn.log`, NetFlow records |
| N2 | **What was resolved / requested?** | DNS query logs, passive DNS, Zeek `dns.log`, DNS sinkhole logs, DHCP lease logs | Zeek `dns.log`, Windows DNS debug log |
| N3 | **What was the web/application traffic?** | HTTP request/response logs, proxy logs, Zeek `http.log`, WAF logs, TLS certificate metadata, JA3/JA4 fingerprints | Zeek `http.log`, proxy access logs |
| N4 | **Is there C2 / beaconing?** | Connection frequency analysis, jitter/interval patterns, data volume asymmetry, DNS tunneling indicators, TLS to unusual ports, DGA domain detection | Statistical analysis of `conn.log`, DNS query entropy |
| N5 | **Was data exfiltrated?** | Outbound data volume anomalies, large DNS TXT responses, HTTP POST sizes, encrypted channel volume, unusual protocols (ICMP tunneling), cloud storage uploads | Upload volume analysis, protocol anomaly detection |
| N6 | **What do email artifacts show?** | Email headers (SPF/DKIM/DMARC analysis), attachment metadata, URLs in email bodies, mail server logs (Exchange, Postfix), PST/OST/MBOX files, phishing indicators | `.eml` headers, Exchange message tracking logs |

---

#### SIEM / Log Aggregation (S1-S3)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| S1 | **What do aggregated logs show?** | Splunk queries (SPL), Elasticsearch/Kibana queries (KQL/Lucene), QRadar AQL, Chronicle YARA-L, Microsoft Sentinel KQL | SPL queries, KQL queries, saved searches |
| S2 | **What correlations exist across sources?** | SIEM correlation rules, alert timelines, cross-source pivoting, enrichment (GeoIP, threat intel feeds, asset inventory) | SIEM alert chains, correlation rule logic |
| S3 | **What's the detection coverage?** | Sigma rule mapping to SIEM, detection gap analysis, MITRE ATT&CK coverage heatmaps, false positive tuning | Sigma → SPL/KQL translations, coverage matrix |

---

#### Cloud Forensics (C1-C6)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| C1 | **Who did what in the cloud control plane?** | AWS CloudTrail, Azure Activity Log, GCP Cloud Audit Logs, management console sign-in logs, API call history | CloudTrail `Event` JSON, Azure Activity Log entries |
| C2 | **What's the identity and access posture?** | AWS IAM (policies, roles, access keys), Azure AD/Entra ID (sign-in logs, audit logs, Conditional Access), GCP IAM, OAuth/OIDC tokens, service principals, SAML assertions | IAM credential report, Entra ID sign-in logs |
| C3 | **What happened in cloud compute?** | EC2/VM instance metadata, Lambda/Functions invocation logs, CloudWatch/Monitor/Logging, container service logs (ECS, AKS, GKE), SSM Session Manager logs | Lambda CloudWatch logs, SSM `StartSession` events |
| C4 | **What happened in cloud networking?** | AWS VPC Flow Logs, Azure NSG Flow Logs, GCP VPC Flow Logs, cloud firewall/WAF logs, DNS query logs, load balancer access logs | VPC Flow Log records, ALB/NLB access logs |
| C5 | **What alerts and detections fired?** | AWS GuardDuty, Azure Defender/Defender for Cloud, GCP Security Command Center, AWS Config rules | GuardDuty finding JSON, Defender alerts |
| C6 | **What happened in SaaS platforms?** | Microsoft 365 Unified Audit Log, Google Workspace Admin audit logs, Salesforce Event Monitoring, Slack/Okta audit logs | M365 UAL events, Okta `system.log` |

---

#### File Storage & Data Access (F1-F5)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| F1 | **What was accessed / exfiltrated from cloud storage?** | AWS S3 access logs & CloudTrail data events, Azure Blob Storage analytics, GCP Cloud Storage audit logs, presigned URL generation events | S3 server access log, CloudTrail `GetObject`/`PutObject` |
| F2 | **What file sharing activity occurred?** | SharePoint/OneDrive audit logs (via M365 UAL), Google Drive audit logs, Dropbox/Box activity logs | M365 UAL `FileDownloaded` events, Google Drive events |
| F3 | **What happened on on-prem file servers?** | Windows file server audit logs (Security Event IDs 5140/5145), SMB access logs, NFS audit logs, DFS Replication logs | Security 5145 (detailed file share access) |
| F4 | **What removable media was connected?** | Windows: SetupAPI logs, USB device registry keys (`USBSTOR`), Event Logs (6416, 20001). Linux: `dmesg`/`kern.log` USB events, `udisks` logs | `setupapi.dev.log`, `USBSTOR` registry, `dmesg` |
| F5 | **What database activity occurred?** | Database audit logs (SQL Server Audit, MySQL audit plugin, PostgreSQL `pgaudit`, Oracle Unified Auditing), query logs, data export commands | SQL Server `fn_get_audit_file()`, `pgaudit` logs |

---

#### AI / LLM Threats & Forensics (A1-A4)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| A1 | **Were AI/LLMs used to conduct the attack?** | AI-generated phishing detection (synthetic text markers), LLM-generated malware/scripts, deepfake voice/video in social engineering, AI-automated reconnaissance/exploitation | Email linguistic analysis, code generation fingerprints, deepfake detection metadata |
| A2 | **Was our LLM application compromised?** | Prompt injection attack logs, RAG poisoning indicators, tool-use/agent exploitation traces, data exfiltration via LLM outputs, jailbreak attempt patterns, guardrail trigger logs | LLM application audit logs, prompt/response logs, RAG retrieval logs, tool call traces |
| A3 | **Was the AI model supply chain tampered with?** | Malicious models on registries (HuggingFace, PyPI), pickle deserialization attacks via model files, model backdoor/trojan detection, training data poisoning, model provenance | Model file hashes, serialization format analysis, model card metadata |
| A4 | **Was our AI infrastructure compromised?** | GPU cluster access logs, training pipeline audit trails, model serving logs (vLLM, TGI, Ollama, llama.cpp), Jupyter notebook forensics, MLOps platform logs, secret/API key exposure | Jupyter `.ipynb` history, MLflow logs, GPU scheduler logs |

---

#### Mobile Device Forensics (M1-M3)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| M1 | **What happened on the mobile device?** | iOS: iTunes/Finder backups, keychain, SQLite databases, plist files, sysdiagnose, unified logs. Android: ADB dumps, logcat, SQLite databases, APK analysis | `manifest.db`, `keychain-2.db`, `consolidated.db` (iOS), `/data/data/` (Android) |
| M2 | **What apps and communications were used?** | App-specific databases (WhatsApp, Telegram, Signal, SMS/iMessage), call logs, contact lists, browser history, location history, photos/EXIF metadata | WhatsApp `msgstore.db`, iOS `sms.db`, Google Timeline |
| M3 | **Was the device managed or compromised?** | MDM enrollment/profiles, enterprise app deployment logs, spyware/stalkerware indicators, jailbreak/root detection artifacts, mobile threat defense logs | MDM configuration profiles, suspicious permission requests |

---

#### Anti-Forensics Detection (AF1-AF4)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| AF1 | **Did the attacker cover their tracks?** | Log clearing detection (Security 1102, 104), timestamp manipulation (timestomping via `$STANDARD_INFORMATION` vs `$FILE_NAME` MFT comparison), selective event deletion, log gap analysis | Event ID 1102 (audit log cleared), MFT timestamp inconsistencies |
| AF2 | **Was data intentionally destroyed?** | Secure deletion tool artifacts (SDelete, BleachBit, `shred`), disk wiping indicators, volume shadow copy deletion (`vssadmin delete shadows`), recycle bin analysis (`$I`/`$R` files) | VSS deletion events, `$Recycle.Bin` metadata |
| AF3 | **Did they use living-off-the-land techniques?** | LOLBin usage detection (certutil, bitsadmin, mshta, regsvr32, rundll32, wmic, msiexec), LOLBAS project mapping, dual-use tool identification | LOLBin execution in Sysmon/4688 logs, unusual parent-child chains |
| AF4 | **Is there hidden data?** | Steganography detection, NTFS alternate data streams, slack space analysis, encrypted container detection (VeraCrypt, BitLocker), hidden partitions | ADS enumeration, entropy analysis, encrypted volume headers |

---

#### Threat Intelligence Operations (TI1-TI2)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| TI1 | **How do we operationalize threat intel?** | IOC matching and enrichment workflows, STIX/TAXII feeds, threat intel platform data (MISP, OpenCTI), intelligence lifecycle management | STIX bundles, MISP events, IOC feeds (CSV/JSON) |
| TI2 | **Who is the threat actor?** | Threat actor attribution frameworks, campaign correlation, diamond model / kill chain mapping, TTP clustering, infrastructure overlap analysis | Attribution reports, campaign timelines |

---

#### IoT / OT / ICS Forensics (OT1-OT2)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| OT1 | **What happened in the OT/ICS environment?** | SCADA/ICS protocol captures (Modbus, DNP3, OPC-UA), PLC program forensics, historian database logs, HMI access logs, engineering workstation artifacts | Modbus traffic captures, PLC logic downloads |
| OT2 | **Were IoT devices compromised?** | IoT device logs, firmware extraction and analysis, network traffic from IoT segments, default credential exploitation indicators, botnet C2 patterns | Firmware binary analysis, IoT device syslog |

---

#### Virtualization / Hypervisor Forensics (V1)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| V1 | **What happened at the hypervisor layer?** | VMware ESXi logs (`hostd`, `vpxa`, `vobd`), Hyper-V event logs, virtual disk forensics (VMDK, VHD/VHDX), snapshot analysis, VM escape detection, vCenter audit logs | ESXi `hostd.log`, `vmware.log`, `.vmdk` analysis |

---

#### Supply Chain & Software Integrity (SC1)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| SC1 | **Was the software supply chain compromised?** | SBOM analysis, package manager compromise detection (npm, PyPI, Maven, NuGet), build pipeline forensics (CI/CD logs), code signing verification, dependency confusion indicators | `package-lock.json`, CI/CD logs, code signing certs |

---

#### Compliance / Legal / Chain of Custody (CL1-CL2)

| # | Forensic Question | Key Artifact Sources | Example Artifacts |
|---|---|---|---|
| CL1 | **Is the investigation legally sound?** | Evidence handling procedures, chain of custody documentation, legal hold processes, acquisition tool logs (FTK Imager, `dc3dd`), hash verification records | Acquisition logs, chain of custody forms |
| CL2 | **Are we meeting regulatory requirements?** | GDPR breach notification requirements, HIPAA breach assessment, PCI-DSS incident response, notification timelines, data classification for breach scope | Regulatory notification templates, breach scope assessment |

---

#### Taxonomy Summary

| Domain | Count | Range |
|---|---|---|
| Windows | 10 | W1-W10 |
| Linux | 8 | L1-L8 |
| Network | 6 | N1-N6 |
| SIEM | 3 | S1-S3 |
| Cloud | 6 | C1-C6 |
| File Storage & Data Access | 5 | F1-F5 |
| AI / LLM Threats | 4 | A1-A4 |
| Mobile | 3 | M1-M3 |
| Anti-Forensics | 4 | AF1-AF4 |
| Threat Intelligence | 2 | TI1-TI2 |
| IoT / OT / ICS | 2 | OT1-OT2 |
| Virtualization | 1 | V1 |
| Supply Chain | 1 | SC1 |
| Compliance / Legal | 2 | CL1-CL2 |
| **Total** | **57** | |

---

### 1.2 Task Categories for This Iteration

The dataset is structured around **5 task categories** — these define what the model should learn to *do*, using the artifact taxonomy as subject matter.

| # | Task Category | What It Teaches | Shepherd Alignment |
|---|---|---|---|
| 1 | **Artifact Analysis** | Interpret forensic tool output, identify anomalies, explain what artifacts mean. Covers surface-level triage through deep memory forensics. Includes anti-forensics detection (AF1, AF3) as a sub-topic. | All specialist agents |
| 2 | **TTP Identification** | Map observed behaviors to MITRE ATT&CK / ATLAS techniques, identify attack chain stages, classify severity. Includes threat intel operationalization (TI1) and AI/LLM threat identification (A1-A4) as sub-topics. | All specialist agents |
| 3 | **Triage & Threat Hunting** | Prioritize investigation steps, recommend evidence collection, decide next pivots given initial indicators. Includes proactive threat hunting: hypothesis generation, baseline deviation analysis, and hunt playbook execution. Includes supply chain triage (SC1) as a sub-topic. | Orchestrator, all specialist agents |
| 4 | **Detection Engineering** | Write/interpret Sigma rules, explain detection logic, translate between query languages, identify coverage gaps. Includes SIEM query operations (S1, S3) as a sub-topic. | Future detection capability |
| 5 | **Incident Report Generation** | Produce evidence-cited IR reports, calibrate confidence language, flag overclaims, structure findings. | Report Agent, Reviewer Agent |

#### How New Domains Fold Into Existing Categories

Rather than creating new task categories for every domain, the new taxonomy entries are absorbed as **sub-topics** within the existing 5 categories:

| New Domain | Absorbed Into | How |
|---|---|---|
| AI/LLM (A1-A4) | **TTP Identification** (A1 attack detection, A3 supply chain) + **Artifact Analysis** (A2 app forensics, A4 infra forensics) | ATLAS techniques treated like ATT&CK techniques; LLM app/infra artifacts treated like any other artifact |
| Anti-Forensics (AF1, AF3) | **Artifact Analysis** | Track-covering and LOLBins are artifact interpretation problems |
| Anti-Forensics (AF2, AF4) | Deferred | Requires specialized sources not in collection |
| Threat Intel (TI1) | **TTP Identification** | IOC enrichment and STIX operationalization are TTP workflows |
| Threat Intel (TI2) | Deferred | Attribution requires classified/sensitive context |
| Supply Chain (SC1) | **Triage & Threat Hunting** | Supply chain compromise triage is a prioritization problem |
| SIEM (S1, S3) | **Detection Engineering** | Sigma → SPL/KQL translation is core detection engineering |

> [!NOTE]
> **Threat Hunting sources (future):** The Triage & Threat Hunting category currently relies on prompt instructions to generate TH-specific pairs from existing sources (primarily ATT&CK, Sigma, and CISA). Dedicated TH sources to add in future iterations include: SANS Threat Hunting Summit materials, ThreatHunting-Keywords (`mthcht/ThreatHunting-Keywords`), Hunting ELK (HELK) documentation, SpecterOps BloodHound methodology, and community hunt playbooks (e.g., `ThreatHuntingProject/ThreatHunting`). These would enable richer hypothesis-driven hunting scenarios and baseline analysis training data.

#### Categories Deferred to Successor

| Category | Why Deferred | What Successor Needs |
|---|---|---|
| Mobile (M1-M3) | No mobile forensic sources in collection | SANS mobile guides, iOS/Android forensic tool docs |
| IoT/OT (OT1-OT2) | Completely different domain, protocols, tools | ICS-CERT advisories, Dragos/Claroty reports |
| Virtualization (V1) | Niche; ESXi forensics not in sources | VMware KB articles, ESXi forensic guides |
| Anti-Forensics deep (AF2, AF4) | Specialized techniques beyond source coverage | Anti-forensic tool docs, forensic challenge writeups |
| Threat actor attribution (TI2) | Requires sensitive operational context | Mandiant/CrowdStrike public attribution reports |
| Compliance/Legal (CL1-CL2) | Procedural/legal knowledge, not technical forensics | Legal frameworks, regulatory guidelines |
| Cloud deep (C3-C6) | Limited cloud-specific sources | AWS/Azure/GCP docs, cloud IR reports |
| File Storage deep (F1-F5) | Limited file forensic sources | M365 UAL docs, S3 log docs |

---

### 1.3 Artifact Taxonomy Coverage Mapping

This maps which of the 57 artifact categories the current dataset iteration will cover, based on source availability across all 6 collectors.

#### Strong Coverage (Primary focus — instruction pairs explicitly generated)

| ID | Category | Primary Sources |
|---|---|---|
| W1 | What executed? | ATT&CK + Atomic RT + Sigma (Sysmon 1, 4688) |
| W2 | How did they persist? | ATT&CK persistence techniques + Sigma + Atomic RT |
| W3 | Who authenticated? | ATT&CK (T1078, T1110) + Sigma (4624/4625) + CISA |
| W5 | Network activity | ATT&CK C2 techniques + Sigma (Sysmon 3) + CISA IOCs |
| W7 | What's in memory? | ATT&CK injection/evasion + **Volatility 3 docs** |
| W8 | Event logs | Sigma rules (~3000 rules with event log references) |
| W9 | Active Directory | ATT&CK (Kerberoasting, DCSync) + Sigma AD rules + CISA |
| W10 | Scripts/commands | ATT&CK T1059.x + Sigma PowerShell rules + Atomic RT |
| L1 | Linux: what executed? | ATT&CK Linux techniques + Atomic RT Linux tests |
| L2 | Linux: persistence | ATT&CK (cron, systemd, SSH keys) + Atomic RT |
| L3 | Linux: authentication | ATT&CK (T1078, T1110) + Sigma Linux rules |
| AF1 | Track covering | ATT&CK T1070 + Sigma (1102/104) + Atomic RT |
| AF3 | Living off the land | ATT&CK LOLBin techniques + Sigma LOLBin rules + Atomic RT |
| S3 | Detection coverage | Sigma rules (direct source) + ATT&CK mapping |
| A1 | AI-assisted attacks | **ATLAS** reconnaissance/attack techniques |
| A2 | LLM app compromise | **ATLAS** ML attack staging techniques |
| A3 | AI supply chain | **ATLAS** supply chain techniques + ATT&CK T1195 |

#### Moderate Coverage (Appears in instruction pairs but not primary focus)

| ID | Category | How It Appears |
|---|---|---|
| W4 | Disk access/modification | Referenced in ATT&CK procedures, some Sigma rules |
| W6 | User activity | Referenced in ATT&CK, limited Sigma coverage |
| L4 | Linux: disk modification | ATT&CK Linux file-based techniques |
| L5 | Linux: network | ATT&CK Linux C2 techniques |
| L6 | Linux: logs | Sigma Linux rules (limited) |
| N2 | DNS | ATT&CK DNS techniques + CISA IOCs |
| N4 | C2/beaconing | ATT&CK C2 tactic + CISA advisories |
| S1 | SIEM queries | Sigma → SPL/KQL translation (Detection Engineering) |
| C1 | Cloud control plane | ATT&CK cloud techniques (growing) |
| C2 | Cloud identity/access | ATT&CK (T1078.004, T1098) + CISA cloud advisories |
| TI1 | Threat intel ops | ATT&CK IS threat intel + STIX is collection format |
| SC1 | Supply chain | ATT&CK T1195 + CISA supply chain advisories |
| A4 | AI infrastructure | **ATLAS** ML infrastructure techniques |

#### Weak/No Coverage (Deferred — taxonomy placeholder for successor)

| ID | Category | Successor Action |
|---|---|---|
| N1, N3, N5 | PCAP, web traffic, exfiltration | Add Zeek docs, PCAP analysis guides |
| N6 | Email artifacts | Add email header analysis guides |
| L7 | Linux memory | Add AVML/LiME docs |
| L8 | Containers/K8s | Add K8s audit log docs, Docker forensics |
| C3-C6 | Cloud compute/network/detection/SaaS | Add cloud provider docs, cloud IR reports |
| F1-F5 | File storage/data access | Add M365 UAL docs, S3 log docs |
| M1-M3 | Mobile device forensics | Add SANS mobile guides, iOS/Android tool docs |
| AF2, AF4 | Data destruction, hidden data | Add anti-forensic tool docs, forensic challenges |
| TI2 | Threat actor attribution | Add public attribution reports |
| OT1-OT2 | IoT/OT/ICS | Add ICS-CERT advisories, OT security guides |
| V1 | Virtualization/hypervisor | Add VMware KB, ESXi forensic guides |
| CL1-CL2 | Compliance/legal | Add legal frameworks, regulatory guidelines |

---

### 1.4 Expanded Artifact Analysis Scope

The Artifact Analysis task category is the broadest of the five — it covers all forensic artifact interpretation, not just memory analysis. This section breaks down the full scope by forensic discipline, tiered by source coverage available in this iteration.

> [!NOTE]
> Each discipline maps to specific taxonomy categories from §1.1. The tier assignments (A/B/C) reflect how well our committed and Tier 1 sources cover the topic, not how important the discipline is to DFIR practice.

---

#### 1.4.1 Event Log Analysis (W3, W8, W10)

The highest-volume discipline by source coverage. Sigma alone provides ~3,000+ detection rules, nearly all referencing specific event log channels and IDs. Hayabusa adds ~4,000+ more. This is the area where the model will have the deepest training signal.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Security logon events (4624/4625/4634/4648/4672) | T1078, T1021, T1110 | Sigma + ATT&CK + CISA + OSSEM field definitions |
| Service installation (7045) | T1543.003 | Sigma + ATT&CK + Atomic RT |
| PowerShell ScriptBlock logging (4103/4104) | T1059.001 | Sigma + ATT&CK + Atomic RT |
| Sysmon process creation (Event ID 1) | T1059, T1106 | Sigma + Sysmon config references |
| Sysmon network connection (Event ID 3) | T1071, T1095 | Sigma + ATT&CK |
| Sysmon file creation (Event ID 11) | T1105, T1036 | Sigma + ATT&CK |
| Sysmon registry events (Event ID 12/13/14) | T1547, T1112 | Sigma + ATT&CK |
| Audit log cleared (1102, 104) | T1070.001 | Sigma + ATT&CK + Atomic RT |
| Scheduled task creation (4698) | T1053.005 | Sigma + ATT&CK + Atomic RT |
| Kerberos/NTLM auth events (4768/4769/4771/4776) | T1558, T1110 | Sigma + ATT&CK AD rules |
| Windows Defender/AV events | T1562.001 | Sigma + Hayabusa |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| WMI-Activity operational log | T1047, T1546.003 | ATT&CK documents technique; limited Sigma rules for WMI event parsing |
| BITS-Client events | T1197 | Technique documented; few detection rules for BITS event log specifics |
| TerminalServices-RDPClient logs | T1021.001 | ATT&CK + some Sigma; event field interpretation requires deeper context |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Exchange/mail server logs | Requires M365/Exchange-specific source docs |
| DNS Server analytical logs | Requires Windows DNS server documentation |

---

#### 1.4.2 Memory Forensics (W7)

Deep analysis of volatile artifacts from memory dumps using Volatility 3 and similar tools. Source coverage comes primarily from ATT&CK technique descriptions and Volatility plugin documentation.

##### Tier A — Included Now

| Artifact / Plugin | Related ATT&CK | Source Coverage |
|---|---|---|
| Process triage (`pslist`, `pstree`, `cmdline`) | T1059, T1106 | ATT&CK + Volatility docs |
| Injected code detection (`malfind`) | T1055.x (12 sub-techniques) | ATT&CK + Atomic RT + Volatility docs |
| DLL analysis (`dlllist`, `ldrmodules`) | T1574.x | ATT&CK + Volatility docs |
| Network connections in memory (`netscan`) | T1071, T1095, T1572 | ATT&CK + CISA + Volatility docs |
| Service analysis (`svcscan`) | T1543.003 | ATT&CK + Sigma (7045) |
| Handle analysis (`handles`) | T1003 (LSASS handle) | ATT&CK + Volatility docs |
| File objects in memory (`filescan`) | T1083, T1036 | ATT&CK + Volatility docs |

##### Tier B — Stretch

| Artifact / Plugin | Related ATT&CK | Gap |
|---|---|---|
| Registry in memory (`printkey`, `hivelist`) | T1547, T1112 | Technique documented but in-memory analysis is tool-specific |
| Scheduled tasks from memory | T1053 | Same gap |

##### Tier C — Defer

| Artifact / Plugin | Why Defer |
|---|---|
| VAD tree analysis (`vadinfo`, `vadwalk`) | Requires Windows memory manager knowledge not in sources |
| Kernel object forensics (pools, drivers, SSDT, callbacks) | Niche specialty, no source data |

---

#### 1.4.3 Filesystem & Disk Forensics (W1, W4, W6)

Interpretation of on-disk artifacts that record execution history, file access, and user activity. KAPE target definitions and ForensicArtifacts provide the "what and where" for these artifacts; ATT&CK provides the "why it matters."

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Prefetch files (`.pf`) | T1059, T1204 | ATT&CK + KAPE targets + ForensicArtifacts |
| Amcache.hve | T1059, T1204 | ATT&CK + KAPE targets + ForensicArtifacts |
| ShimCache / AppCompatCache | T1059 | ATT&CK + KAPE targets |
| LNK files / Jump Lists / Recent docs | T1204 | KAPE targets + ForensicArtifacts |
| Shellbags (`UsrClass.dat`) | T1083, T1074 | KAPE targets + ForensicArtifacts |
| Recycle Bin (`$I`/`$R` files) | T1070.004 | ATT&CK + KAPE targets |
| Zone.Identifier / ADS | T1564.004 | ATT&CK + KAPE targets |
| UserAssist / RecentApps | T1204 | KAPE targets + ForensicArtifacts |
| BAM/DAM (Background Activity Moderator) | T1059 | KAPE targets |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| MFT (`$MFT`) timeline analysis | T1070.006, T1036 | ForensicArtifacts defines location; MFT parsing semantics are tool-specific (MFTECmd) |
| USN Journal (`$UsnJrnl:$J`) | T1070.006 | Same gap — file change journal interpretation requires tool doc context |
| `$I30` directory index parsing | T1070, T1564 | Niche forensic technique not well-covered in structured sources |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Slack space / unallocated space analysis | Requires disk imaging tool docs, not in any structured source |
| File carving and recovery | Tool-specific (Autopsy, Foremost), no structured source data |

---

#### 1.4.4 Registry Forensics (W2, W6)

Analysis of Windows registry hives for persistence, configuration changes, and user activity tracking. Registry is central to Windows forensics — nearly every persistence mechanism touches the registry.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Run/RunOnce persistence keys | T1547.001 | ATT&CK + Sigma + Atomic RT + KAPE |
| Services (`CurrentControlSet\Services`) | T1543.003 | ATT&CK + Sigma (7045) + Atomic RT |
| COM hijacking / CLSID keys | T1546.015 | ATT&CK + Atomic RT |
| Image File Execution Options (IFEO) | T1546.012 | ATT&CK + Atomic RT |
| AppInit_DLLs | T1546.010 | ATT&CK + Atomic RT |
| SRUM.dat (System Resource Usage Monitor) | T1059 | KAPE targets + ForensicArtifacts |
| MRU lists (TypedPaths, TypedURLs, RecentDocs) | T1083 | KAPE targets + ForensicArtifacts |
| USB device history (`USBSTOR`) | T1025, T1052 | KAPE targets + ForensicArtifacts |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| Boot Execute / Winlogon | T1547.004 | ATT&CK documents technique; limited detection rules |
| AppCompatFlags / PCA | — | KAPE defines targets; no ATT&CK mapping |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Deep hive recovery / deleted key analysis | Requires registry hive internals knowledge beyond source coverage |
| Transaction logs (.LOG1/.LOG2) | Niche recovery technique |

---

#### 1.4.5 Network Artifact Forensics (W5, N2, N4)

Network-level forensic artifacts observable from host-based evidence and IOC matching. Full PCAP analysis (N1, N3, N5) is deferred, but host-observable network indicators are well-covered.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| DNS cache / resolution artifacts | T1071.004, T1568 | ATT&CK + CISA IOCs |
| C2 beaconing indicators (interval, jitter) | T1571, T1573 | ATT&CK C2 tactic + CISA advisories |
| IOC matching (IP, domain, hash) | — | CISA advisories + KEV catalog |
| Proxy / browser history artifacts | T1071.001 | ATT&CK + ForensicArtifacts |
| Sysmon network events (Event ID 3, 22) | T1071, T1568 | Sigma + ATT&CK |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| Firewall log analysis (5156/5157) | T1562.004 | Some Sigma rules; log format interpretation is tool-specific |
| BITS transfer artifacts | T1197 | ATT&CK + Atomic RT; limited structured detection content |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Full PCAP / Zeek log analysis (N1, N3, N5) | Requires Zeek docs, PCAP analysis guides — different toolchain |
| Email header analysis (N6) | Requires email-specific source docs |

---

#### 1.4.6 Anti-Forensics Detection (taxonomy AF1-AF4)

Detecting attacker attempts to cover tracks, destroy evidence, or hide data. Partially covered through ATT&CK T1070 sub-techniques and LOLBAS/GTFOBins.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Log clearing detection (1102, 104) | T1070.001 | ATT&CK + Sigma + Atomic RT |
| Timestomping detection (`$SI` vs `$FN` comparison) | T1070.006 | ATT&CK + Atomic RT |
| LOLBin abuse detection | Various | ATT&CK + Sigma + LOLBAS + GTFOBins |
| VSS shadow copy deletion | T1490 | ATT&CK + Sigma + Atomic RT |
| Indicator removal from tools | T1070.004 | ATT&CK + Sigma |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| Selective event log entry deletion | T1070.001 | Detection requires gap analysis methodology, not just rule matching |
| Process argument spoofing | T1564.010 | ATT&CK documents; few structured detection rules |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Steganography detection (AF4) | Requires specialized stego analysis tools and guides |
| Encrypted container detection (VeraCrypt, BitLocker) | Requires disk forensic tool documentation |
| Slack space hiding | Same as filesystem Tier C |

---

#### 1.4.7 Linux Forensics (L1-L6)

Linux artifact analysis is thinner than Windows in structured source coverage — fewer Sigma rules, no KAPE equivalent — but ATT&CK Linux techniques and Atomic Red Team Linux tests provide a solid foundation. ForensicArtifacts includes Linux artifact definitions.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Shell history (`.bash_history`, `.zsh_history`) | T1059.004 | ATT&CK + Atomic RT + ForensicArtifacts |
| Cron persistence (`/etc/crontab`, user crontabs) | T1053.003 | ATT&CK + Atomic RT + ForensicArtifacts |
| Systemd service/timer persistence | T1543.002 | ATT&CK + Atomic RT |
| SSH `authorized_keys` manipulation | T1098.004 | ATT&CK + Atomic RT |
| Auth logs (`/var/log/auth.log`, `/var/log/secure`) | T1078, T1110 | ATT&CK + Sigma Linux rules + ForensicArtifacts |
| `wtmp`/`btmp`/`utmp` login records | T1078 | ATT&CK + ForensicArtifacts |
| GTFOBins abuse | Various | GTFOBins |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| `auditd` / `execve` syscall logs | T1059.004 | ATT&CK documents; auditd rule interpretation requires OS-specific docs |
| Package manager logs (`dpkg.log`, `dnf.log`) | T1072 | ForensicArtifacts defines location; interpretation is tool-specific |
| LD_PRELOAD / PAM module injection | T1574.006 | ATT&CK + Atomic RT; detection is configuration-dependent |

##### Tier C — Defer

| Artifact Type | Why Defer |
|---|---|
| Linux memory forensics (LiME, AVML) | Requires separate tool documentation (L7) |
| Container/K8s forensics | Different domain — requires K8s audit log docs (L8) |

---

#### 1.4.8 Active Directory Forensics (W9)

AD-specific attack and artifact analysis. Well-covered through ATT&CK credential access / lateral movement techniques and Sigma's AD-focused rules.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| Kerberoasting (TGS-REP extraction) | T1558.003 | ATT&CK + Sigma + Atomic RT |
| AS-REP Roasting | T1558.004 | ATT&CK + Sigma + Atomic RT |
| DCSync detection | T1003.006 | ATT&CK + Sigma (4662) + Atomic RT |
| Golden/Silver Ticket usage | T1558.001, T1558.002 | ATT&CK + Sigma |
| Pass-the-Hash / Pass-the-Ticket | T1550.002, T1550.003 | ATT&CK + Sigma + CISA |
| AdminSDHolder / SID History abuse | T1134, T1207 | ATT&CK |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| DCShadow | T1207 | ATT&CK documents; very few detection rules |
| Group Policy Object abuse | T1484.001 | ATT&CK + limited Sigma coverage |
| NTDS.dit offline analysis | T1003.003 | ATT&CK documents extraction; offline parsing requires tool docs |

---

#### 1.4.9 Script & Command Forensics (W10)

Analysis of executed commands, scripts, and encoded payloads. Strong overlap with Detection Engineering but the Artifact Analysis angle focuses on *interpreting output and identifying malicious intent*, not writing rules.

##### Tier A — Included Now

| Artifact Type | Related ATT&CK | Source Coverage |
|---|---|---|
| PowerShell ScriptBlock reconstruction (4104) | T1059.001 | ATT&CK + Sigma + Atomic RT |
| Base64/encoded command detection | T1027, T1059.001 | ATT&CK + Sigma + Atomic RT |
| WMI command line analysis | T1047 | ATT&CK + Sigma + Atomic RT |
| `ConsoleHost_history.txt` analysis | T1059.001 | ATT&CK + ForensicArtifacts + KAPE |
| VBA/macro artifact detection | T1059.005 | ATT&CK + Sigma |
| `cscript`/`wscript`/`mshta` execution | T1059.005, T1059.007 | ATT&CK + Sigma + LOLBAS |

##### Tier B — Stretch

| Artifact Type | Related ATT&CK | Gap |
|---|---|---|
| Deobfuscation / script unpacking | T1140 | ATT&CK documents technique; practical deobfuscation methodology is experience-based |
| AMSI bypass detection | T1562.001 | ATT&CK + Atomic RT; detection is version-dependent |

### Phase 1 Deliverables
- [ ] Finalized 57-category taxonomy document
- [ ] Taxonomy cross-referenced against ForensicArtifacts repository and ATT&CK Data Sources/Components
- [ ] Coverage mapping reviewed with team/mentor
- [ ] Sigma logsource distribution analyzed to empirically validate coverage mapping
- [ ] 5-10 concrete example tasks per task category
- [ ] Difficulty distribution targets confirmed: 30% junior, 50% mid, 20% senior

---

## Phase 2: Source Collection Pipeline (Week 3 Day 4 – Week 5)

### 2.1 Source Inventory

Sources are organized into tiers. **Core** collectors focus on TTPs, detections, and threat advisories. **Artifact-Focused** collectors fill the gap in artifact-specific forensic knowledge — the "what does this artifact look like, what's normal vs suspicious, where does it live on disk" content that Core sources don't cover well.

> [!IMPORTANT]
> **Scope decision (confirmed):** This iteration implements **Core + Tier 1 + Tier 2** — all 16 collectors (C1-C7 + AF1-AF9). Tier 3 sources (AF10-AF15) are deferred to the successor.

#### Core Collectors (Committed)

| # | Source | Est. Docs | Content Type | Access Method | License | Effort |
|---|---|---|---|---|---|---|
| C1 | **MITRE ATT&CK** | ~800 | TTP definitions, procedures, mitigations, detection | `mitreattack-python` STIX API | Apache 2.0 ✅ | 2-3 days |
| C2 | **SigmaHQ Rules** | ~3,000+ | YAML detection rules with metadata, references, tags | `git clone` + YAML parsing | LGPL 2.1 ✅ | 1-2 days |
| C3 | **Atomic Red Team** | ~800+ | TTP test procedures with commands, expected output | `git clone` + YAML parsing | MIT ✅ | 1-2 days |
| C4 | **CISA Advisories** | ~500+ | Government threat advisories, IOCs, mitigations | Web scrape (RSS/HTML) | Public domain ✅ | 2-3 days |
| C5 | **Volatility 3 Docs** | ~50-100 | Plugin descriptions, output schemas, forensic semantics | `git clone` + markdown/RST parsing | GPL ✅ | 1 day |
| C6 | **MITRE ATLAS** | ~50-80 | AI/ML adversarial techniques, case studies, mitigations | STIX API or web scrape | Apache 2.0 ✅ | 1 day |
| C7 | **CISA KEV Catalog** | ~1,200+ | CVE records with vendor, product, ransomware flag, remediation deadlines | JSON download | Public domain ✅ | 0.5 day |

**Core subtotal: ~6,450-6,980 documents**

> [!NOTE]
> Core sources are strong for *attacks* (ATT&CK), *detections* (Sigma), and *procedures* (Atomic RT) — but they describe **what attackers do**, not **what forensic artifacts look like**. The artifact-focused sources below fill that gap.

---

#### Artifact-Focused Tier 1 — Must-Add (Structured, 1 day each, highest ROI)

These are Git-hosted, YAML/Markdown structured repos that reuse the same parsing patterns as Sigma/Atomic RT. They provide the artifact-specific knowledge that Core sources lack.

| # | Source | Repo | Est. Docs | What It Teaches | License | Effort |
|---|---|---|---|---|---|---|
| AF1 | **KAPE Targets & Modules** | `EricZimmermanTools/KapeFiles` | ~1,000+ | Defines *what* each Windows artifact is, where it lives on disk, and what tool processes it. Each `.tkape`/`.mkape` is a structured forensic artifact definition. | MIT ✅ | 1 day |
| AF2 | **Hayabusa Rules** | `Yamato-Security/hayabusa-rules` | ~4,000+ | Windows event log detection rules — complements Sigma with deeper Windows event coverage. More granular event ID + field combination rules. | GPL 3.0 ✅ | 1 day |
| AF3 | **LOLBAS + GTFOBins** | `LOLBAS-Project/LOLBAS` + `GTFOBins/GTFOBins.github.io` | ~600+ | Living Off The Land databases for Windows (LOLBAS) and Linux (GTFOBins). Documents how legitimate binaries are abused: abuse functions, detection opportunities, ATT&CK mappings. | GPL 3.0 ✅ | 1 day |
| AF4 | **ForensicArtifacts Repository** | `ForensicArtifacts/artifacts` | ~500+ | Community-vetted, machine-readable forensic artifact definitions — defines *what* each artifact is, where it lives on disk (file paths, registry keys, WMI queries), and which OS it applies to. The canonical reference used by GRR Rapid Response and Plaso/log2timeline. Directly validates and enriches W1-W6 (Windows disk/registry artifacts) and L1-L6 (Linux artifacts). | Apache 2.0 ✅ | 0.5-1 day |

**Tier 1 subtotal: ~6,100+ documents**

> [!TIP]
> **Why these 4 are "must-add":** ForensicArtifacts is the community-standard machine-readable artifact taxonomy — it defines the exact file paths, registry keys, and WMI queries for hundreds of forensic artifacts across Windows, Linux, and macOS. KAPE is the single best structured source for "what Windows forensic artifacts exist" in a collection context. Hayabusa nearly doubles your event log rule coverage beyond Sigma. LOLBAS/GTFOBins give the model concrete "this binary + these arguments = suspicious" training signal for both Windows and Linux. All four use the same `git clone` + YAML/Markdown parsing pattern you're already building for Sigma and Atomic RT.

---

#### Artifact-Focused Tier 2 — Committed (Structured, 1-2 days each)

| # | Source | Repo | Est. Docs | What It Teaches | License | Effort |
|---|---|---|---|---|---|---|
| AF5 | **Velociraptor Artifact Exchange** | `Velocidex/velociraptor-docs` | ~500+ | VQL artifact definitions with descriptions and queries. Covers Windows/Linux/macOS artifact collection. Teaches the model what each artifact collects and why. | AGPL ✅ | 1-2 days |
| AF6 | **HijackLibs** | `wietze/HijackLibs` | ~350+ | DLL hijacking database — documents which applications are vulnerable to DLL search order hijacking/side-loading. Directly supports W7 (DLL analysis) and ATT&CK T1574.x. | BSD ✅ | 1 day |
| AF7 | **LOLDrivers** | `magicsword-io/LOLDrivers` | ~400+ | Vulnerable and malicious Windows drivers (BYOVD). Covers driver-based kernel attacks — a gap none of the Core or Tier 1 sources touch. | Open ✅ | 1 day |
| AF8 | **OSSEM Data Dictionaries** | `OTRF/OSSEM-DD` | ~200-300 | Field-level documentation for Windows Security events, Sysmon events, and other security log sources. Each dictionary entry describes a single event ID with all its field names, types, and descriptions. Directly supports W8 (event logs), W10 (scripts/commands), and S1 (SIEM queries). | MIT ✅ | 1 day |
| AF9 | **Anthropic Cybersecurity Skills** | `mukul975/Anthropic-Cybersecurity-Skills` | ~450-500 (filtered) | 754 structured practitioner workflows across 26 security domains. Each skill contains step-by-step investigation/detection procedures with tool commands, key concepts, and scenarios. Pre-mapped to ATT&CK, ATLAS, D3FEND, NIST CSF, NIST AI RMF. Primary value: fills the Triage & Threat Hunting category gap with ~150 hunt-specific workflow skills. Filtered to skills with body ≥500 tokens to exclude thin boilerplate templates. | Apache 2.0 ✅ | 1 day |

**Tier 2 subtotal: ~1,900-2,050+ documents**

---

#### Artifact-Focused Tier 3 — Nice-to-Have (Add if time permits in Week 4)

| # | Source | Repo / URL | Est. Docs | What It Teaches | License | Effort |
|---|---|---|---|---|---|---|
| AF10 | **EVTX-ATTACK-SAMPLES** | `sbousseaden/EVTX-ATTACK-SAMPLES` | ~100+ | Real Windows event log samples from attack simulations, organized by ATT&CK technique. Gold standard for event log artifact analysis. | Open ✅ | 1-2 days |
| AF11 | **WADComs** | `WADComs/WADComs.github.io` | ~200+ | Windows/AD offensive command reference — enumeration, credential dumping, lateral movement commands. Supports W9 (AD) and W10 (scripts). | Open ✅ | 1 day |
| AF12 | **MalAPI.io** | `mrd0x/MALAPI` | ~200+ | Maps Windows API calls to ATT&CK techniques — shows which APIs indicate injection, evasion, hooking. Supports W7 (memory forensics). | Open ✅ | 0.5 day |
| AF13 | **LOTS Project** | `lots-project/lots-project.github.io` | ~150+ | Living Off Trusted Sites — documents legitimate cloud services abused for C2, exfiltration, phishing. Supports N4 (C2) and N5 (exfiltration). | Open ✅ | 0.5 day |
| AF14 | **Chainsaw Rules** | `WithSecureLabs/chainsaw` | ~100+ | Additional Windows event log analysis rules complementing Sigma/Hayabusa. | GPL 3.0 ✅ | 0.5 day |
| AF15 | **Sysmon Config References** | `SwiftOnSecurity/sysmon-config` + `olafhartong/sysmon-modular` | ~10-20 | Documented Sysmon configurations explaining what each event ID captures and why. Teaches telemetry design reasoning. | MIT ✅ | 0.5 day |

**Tier 3 subtotal: ~760+ documents**

---

#### Semi-Structured Sources — Deferred to Successor (Moderate-High effort)

These contain high-value artifact analysis content but require HTML scraping, PDF extraction, or more complex parsing.

| Source | What It Contains | Format | License | Est. Docs | Effort |
|---|---|---|---|---|---|
| **SANS DFIR Posters & Cheat Sheets** | Condensed forensic artifact reference guides — Windows, memory, network, timeline analysis | PDF (public download) | Free personal use ⚠️ | ~20-30 | Medium (PDF parsing) |
| **ForensicsWiki** | Community forensic artifact encyclopedia — file formats, artifact locations, parsing tools | MediaWiki HTML | CC-BY-SA ✅ | ~500+ | Medium (wiki scraping) |
| **UltimateWindowsSecurity.com** | Windows Event ID encyclopedia — detailed event descriptions and field definitions | HTML | Free reference ⚠️ | ~300+ | Medium (scraping) |
| **Eric Zimmerman Tool Docs** | EZ tool documentation — what each tool parses and what output fields mean | GitHub markdown + website | MIT ✅ | ~20-30 | Low-Medium |
| **Plaso / log2timeline Docs** | Timeline analysis parser documentation — what each parser extracts | GitHub RST/Markdown | Apache 2.0 ✅ | ~100+ | Medium |
| **MemProcFS Documentation** | Alternative memory forensics framework documentation | GitHub markdown | AGPL ✅ | ~20-30 | Low |
| **Digital Corpora** | Forensic test image metadata/descriptions (not the images) | Documentation | Public domain ✅ | ~50+ | Low |

#### Unstructured Sources — Deferred to Successor (High effort, high value)

| Source | What It Contains | Why Defer |
|---|---|---|
| **13Cubed** (YouTube transcripts) | Detailed forensic artifact video walkthroughs | Fair use concerns, transcript extraction complexity |
| **DFIR community blogs** (via AboutDFIR blogroll) | Practitioner blog posts, investigation walkthroughs | Heterogeneous formats, various licenses |
| **CyberDefenders lab writeups** | Step-by-step forensic investigation writeups with real evidence | Various licenses, HTML scraping |
| **Forensic CTF writeups** | Competition writeups showing artifact analysis methodology | Scattered across GitHub/blogs |
| **This Week in 4n6 archives** | Curated weekly DFIR link index — pointer to community content | Index only (points to other sources) |
| **Mandiant / CrowdStrike / Unit 42 blogs** | Real IR case studies, APT campaigns, cloud incidents | Complex scraping, copyright |
| **VirusTotal / ANY.RUN / MalwareBazaar** | Malware analysis data | API access, separate task category |
| **Cloud provider docs (AWS, Azure, GCP)** | Cloud forensics (C1-C6) | Large scope, separate effort |
| **M365 UAL / Google Workspace docs** | File storage forensics (F1-F2) | Vendor-specific documentation |
| **SANS mobile forensic guides** | Mobile forensics (M1-M3) | Different domain |
| **ICS-CERT advisories** | IoT/OT forensics (OT1-OT2) | Different domain |
| **OWASP LLM Top 10, AI incident databases** | Deeper AI/LLM threat coverage (A1-A4) | Emerging, small corpus |

---

#### Volume Summary by Tier Decision

| Scenario | Collectors | Est. Raw Docs | Est. Pairs (pre-filter) | Est. Pairs (post-filter ~70%) |
|---|---|---|---|---|
| Core only | C1-C7 | ~6,450 | ~22,570 | ~15,800 |
| Core + Tier 1 | C1-C7 + AF1-AF4 | ~12,550 | ~41,430 | ~29,000 |
| **► Core + Tier 1-2 (selected)** | **C1-C7 + AF1-AF9** | **~14,700** | **~49,160** | **~34,410** |
| Core + Tier 1-3 (maximum) | C1-C7 + AF1-AF15 | ~15,460 | ~51,670 | ~36,170 |

> [!NOTE]
> **Selected scenario: Core + Tier 1-2.** This yields ~14,700 raw documents and an estimated ~34,410 post-filter instruction pairs. Tier 2 adds ~1,900-2,050 documents for ~5 additional days of collector work — worthwhile for the artifact depth (Velociraptor VQL, DLL hijacking, driver attacks, event log field definitions) and practitioner workflow coverage (Cybersecurity Skills fills the Triage & Threat Hunting category gap). Tier 3 is deferred but can be added later with minimal effort using the same `YAMLCollector`/`MarkdownCollector` base classes.

### 2.2 Pipeline Architecture

```
dfir-dataset/
├── README.md
├── pyproject.toml
├── .env.example
│
├── collectors/
│   ├── __init__.py
│   ├── base.py                     # BaseCollector ABC
│   │
│   │   # ── Core Collectors ──
│   ├── mitre_attack.py             # C1: MITRE ATT&CK STIX collector
│   ├── sigma_rules.py              # C2: SigmaHQ YAML collector
│   ├── atomic_red_team.py          # C3: Atomic Red Team YAML collector
│   ├── cisa_advisories.py          # C4: CISA advisory scraper
│   ├── volatility3_docs.py         # C5: Volatility 3 plugin docs
│   ├── mitre_atlas.py              # C6: MITRE ATLAS AI/ML threats
│   │
│   │   # ── Artifact-Focused Tier 1 ──
│   ├── kape_files.py               # AF1: KAPE Targets & Modules
│   ├── hayabusa_rules.py           # AF2: Hayabusa event log rules
│   ├── lolbas_gtfobins.py          # AF3: LOLBAS + GTFOBins
│   ├── forensic_artifacts.py       # AF4: ForensicArtifacts Repository
│   │
│   │   # ── Artifact-Focused Tier 2 ──
│   ├── velociraptor_artifacts.py   # AF5: Velociraptor VQL artifacts
│   ├── hijacklibs.py               # AF6: HijackLibs DLL hijacking DB
│   ├── loldrivers.py               # AF7: LOLDrivers vulnerable drivers
│   ├── ossem_data_dicts.py         # AF8: OSSEM Data Dictionaries
│   └── cybersec_skills.py          # AF9: Anthropic Cybersecurity Skills
│
├── synthesizers/
│   ├── __init__.py
│   ├── base.py                     # BaseSynthesizer ABC
│   ├── teacher.py                  # Frontier model synthesis driver
│   ├── prompts/
│   │   ├── artifact_analysis.md
│   │   ├── ttp_identification.md
│   │   ├── triage_and_hunting.md
│   │   ├── detection_engineering.md
│   │   └── report_generation.md
│   └── formatters/
│       ├── chat_template.py
│       └── evaluation.py
│
├── quality/
│   ├── __init__.py
│   ├── scorer.py
│   ├── filters.py
│   ├── dedup.py
│   ├── validators/
│   │   ├── mitre_validator.py      # Validates ATT&CK AND ATLAS IDs
│   │   └── tool_validator.py
│   └── reports/
│       └── distribution_audit.py   # Includes taxonomy coverage heatmap
│
├── packaging/
│   ├── __init__.py
│   ├── splitter.py
│   ├── exporter.py
│   └── dataset_card.py
│
├── evaluation/
│   ├── __init__.py
│   ├── benchmark_runner.py
│   └── metrics.py
│
├── scripts/
│   ├── collect_all.py
│   ├── synthesize.py
│   ├── filter_and_package.py
│   ├── run_evaluation.py
│   └── full_pipeline.py
│
├── data/                           # gitignored
│   ├── raw/
│   │   ├── mitre_attack/           # C1
│   │   ├── sigma_rules/            # C2
│   │   ├── atomic_red_team/        # C3
│   │   ├── cisa_advisories/        # C4
│   │   ├── volatility3_docs/       # C5
│   │   ├── mitre_atlas/            # C6
│   │   ├── kape_files/             # AF1
│   │   ├── hayabusa_rules/         # AF2
│   │   ├── lolbas_gtfobins/        # AF3
│   │   ├── forensic_artifacts/     # AF4
│   │   ├── velociraptor_artifacts/ # AF5
│   │   ├── hijacklibs/             # AF6
│   │   ├── loldrivers/             # AF7
│   │   ├── ossem_data_dicts/       # AF8
│   │   └── cybersec_skills/        # AF9
│   ├── synthesized/
│   ├── filtered/
│   ├── packaged/
│   └── evaluation/
│
├── configs/
│   ├── collection.yaml
│   ├── synthesis.yaml
│   ├── quality.yaml
│   └── packaging.yaml
│
└── docs/
    ├── ARCHITECTURE.md
    ├── TAXONOMY.md                 # Full 57-category reference
    ├── COVERAGE_MAP.md
    ├── ADDING_SOURCES.md
    ├── PROMPT_GUIDE.md
    ├── QUALITY_RUBRIC.md
    └── HANDOVER.md
```

### 2.3 Raw Document Schema

Every collector outputs standardized JSON Lines:

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
    "framework": "attack",
    "tactic": ["execution"],
    "platforms": ["Windows"],
    "data_sources": ["Process: Process Creation", "Command: Command Execution"]
  },
  "license": "Apache-2.0",
  "word_count": 1850
}
```

For ATLAS documents, the `framework` field is `"atlas"` and `mitre_id` uses ATLAS IDs (e.g., `"AML.T0043"`).

### 2.4 BaseCollector Interface

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
        Returns a report dict with counts, errors, warnings.
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

### 2.5 Collector Implementation Notes

#### C1: MITRE ATT&CK Collector
- `mitreattack-python` STIX API
- One document per technique/sub-technique
- Enrichment: procedures, detection guidance, mitigations
- Expected yield: ~800 documents

#### C2: SigmaHQ Collector
- `git clone SigmaHQ/sigma` + YAML parsing
- One document per rule
- Enrichment: ATT&CK tags, log source requirements, false positive notes
- Expected yield: ~3,000+ documents

#### C3: Atomic Red Team Collector
- `git clone redcanaryco/atomic-red-team` + YAML parsing
- One document per atomic test
- Enrichment: link to ATT&CK technique, executor commands, cleanup commands
- Expected yield: ~800+ documents

#### C4: CISA Advisories Collector
- Web scrape CISA.gov advisories via RSS/HTML
- One document per advisory
- Enrichment: CVEs, IOCs, affected software, ATT&CK mappings
- Expected yield: ~500+ documents

#### C5: Volatility 3 Documentation Collector
- `git clone volatilityfoundation/volatility3`
- Plugin docstrings, README files, documentation pages
- Enrichment: link plugin to output schema, tag with ATT&CK techniques
- Expected yield: ~50-100 documents

#### C6: MITRE ATLAS Collector
- ATLAS STIX data or structured web content from `atlas.mitre.org`
- One document per technique + case studies
- Enrichment: link to ATT&CK techniques where overlap exists, include ML-specific mitigations
- Expected yield: ~50-80 documents

> [!TIP]
> The ATLAS collector can reuse much of the ATT&CK collector's code since both use STIX format. The main differences are the STIX source URL and the technique ID format (`AML.Txxx` instead of `Txxx`).

#### C7: CISA KEV Catalog Collector
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

---

#### AF1: KAPE Targets & Modules Collector
- `git clone EricZimmermanTools/KapeFiles` + YAML parsing (`.tkape`, `.mkape`)
- One document per target/module definition
- Enrichment: artifact category, file paths, associated forensic tool, OS platform
- Expected yield: ~1,000+ documents
- **Parsing pattern:** Same YAML → JSONL pattern as Sigma/Atomic RT

#### AF2: Hayabusa Rules Collector
- `git clone Yamato-Security/hayabusa-rules` + YAML parsing
- One document per detection rule
- Enrichment: ATT&CK mappings, event log channel/ID, severity level
- Expected yield: ~4,000+ documents
- **Parsing pattern:** Nearly identical to Sigma collector — same YAML structure with minor field differences

#### AF3: LOLBAS + GTFOBins Collector
- `git clone LOLBAS-Project/LOLBAS` (YAML) + `git clone GTFOBins/GTFOBins.github.io` (Markdown)
- One document per binary
- Enrichment: abuse functions, detection notes, ATT&CK mappings, OS platform
- Expected yield: ~600+ documents (combined)
- **Note:** Two repos, but one collector class with a unified schema

#### AF4: ForensicArtifacts Repository Collector
- `git clone ForensicArtifacts/artifacts` + YAML parsing
- One document per artifact definition
- Enrichment: artifact name, description, OS platform, artifact paths (file, registry, WMI), supported collectors
- Expected yield: ~500+ documents
- **Parsing pattern:** Same YAML → JSONL pattern as Sigma/Atomic RT. Each `.yaml` file in the `artifacts/` directory contains one or more artifact definitions with a well-defined schema (see [artifact specification](https://artifacts.readthedocs.io/en/latest/)).
- **Unique value:** Unlike KAPE (which defines *how to collect*), ForensicArtifacts defines *what the artifact is and where it lives*. Both are complementary — KAPE provides collection context, ForensicArtifacts provides identification/definition context.

#### AF5: Velociraptor Artifact Exchange Collector
- `git clone Velocidex/velociraptor-docs` or artifact exchange API
- One document per VQL artifact definition
- Enrichment: artifact description, VQL query, parameters, OS platform
- Expected yield: ~500+ documents

#### AF6: HijackLibs Collector
- `git clone wietze/HijackLibs` + YAML/JSON parsing
- One document per vulnerable application
- Enrichment: DLL name, hijack type, ATT&CK T1574.x mapping, vendor
- Expected yield: ~350+ documents

#### AF7: LOLDrivers Collector
- `git clone magicsword-io/LOLDrivers` + YAML parsing
- One document per driver
- Enrichment: driver hash, CVEs, abuse type (BYOVD, vulnerable), vendor
- Expected yield: ~400+ documents

#### AF8: OSSEM Data Dictionaries Collector
- `git clone OTRF/OSSEM-DD` + YAML/Markdown parsing
- One document per event ID dictionary entry
- Enrichment: event ID, provider/channel, field names and descriptions, OS platform
- Expected yield: ~200-300 documents
- **Note:** OSSEM is organized as git submodules (`OSSEM-DD`, `OSSEM-CDM`, `OSSEM-DM`). We only collect from `OSSEM-DD` (Data Dictionaries) — the CDM and DM submodules provide normalization schemas that are useful for reference but don't contain collectible forensic content.

#### AF9: Anthropic Cybersecurity Skills Collector
- `git clone mukul975/Anthropic-Cybersecurity-Skills` + YAML frontmatter + Markdown body parsing
- One document per `SKILL.md` file in `skills/` directory
- **Content-length filter:** Only collect skills with Markdown body ≥ 500 tokens (~2,000 chars). Skills below this threshold are thin boilerplate templates that would produce hallucinated padding during synthesis.
- Enrichment: skill name, description, domain, subdomain, tags, ATT&CK IDs, ATLAS IDs, D3FEND IDs, NIST CSF categories, workflow steps, tools referenced, scenarios
- Expected yield: ~450-500 documents (from 754 total, after filtering thin templates)
- **Note:** This is a single-author repo (not community-curated like SigmaHQ). ATT&CK IDs in frontmatter may contain inaccuracies — the Phase 4 MITRE validator will catch these. Cross-validate frontmatter mappings against the body content during pilot review. Primary value is for the Triage & Threat Hunting category where ~150 skills directly map to structured hunt workflows.

> [!NOTE]
> **Tier 3 sources (AF10-AF15)** do not need dedicated collector classes initially. If selected, they follow the same `git clone` + YAML/Markdown parsing pattern. They can be added as configuration-driven collectors inheriting from a shared `YAMLCollector` or `MarkdownCollector` base class.

### Phase 2 Deliverables
- [ ] `BaseCollector` ABC and common utilities
- [ ] C1: MITRE ATT&CK collector — working and tested
- [ ] C2: SigmaHQ collector — working and tested
- [ ] C3: Atomic Red Team collector — working and tested
- [ ] C4: CISA Advisories collector — working and tested
- [ ] C5: Volatility 3 Docs collector — working and tested
- [ ] C6: MITRE ATLAS collector — working and tested
- [ ] C7: CISA KEV Catalog collector — working and tested
- [ ] AF1: KAPE Targets & Modules collector — working and tested
- [ ] AF2: Hayabusa Rules collector — working and tested
- [ ] AF3: LOLBAS + GTFOBins collector — working and tested
- [ ] AF4: ForensicArtifacts Repository collector — working and tested
- [ ] AF5: Velociraptor Artifact Exchange collector — working and tested
- [ ] AF6: HijackLibs collector — working and tested
- [ ] AF7: LOLDrivers collector — working and tested
- [ ] AF8: OSSEM Data Dictionaries collector — working and tested
- [ ] AF9: Anthropic Cybersecurity Skills collector — working and tested
- [ ] `collect_all.py` script that runs all 16 collectors and produces a manifest
- [ ] Validation: all collectors produce valid JSONL with complete metadata
- [ ] Raw corpus: ~14,700 documents in `data/raw/` (Core + Tier 1-2)

---

## Phase 3: Instruction Pair Synthesis (Week 5 Day 3 – Week 7)

### 3.1 Strategy

Single-pass teacher synthesis using a frontier model with category-specific prompt templates.

```
                                ┌─────────────────────┐
                                │  Prompt Template     │
                                │  (per category)      │
                                └─────────┬───────────┘
                                          │
Raw Document ──→ Teacher Model ──→ Instruction Pairs ──→ data/synthesized/
                 (Claude Sonnet       (3-5 per doc)
                  or Gemini Flash)
```

### 3.2 Synthesis Model Selection
| Model | Cost (per 1M tokens) | Quality | Recommendation |
|---|---|---|---|
| Gemini 2.5 Flash | ~$0.15 input / $0.60 output | Medium-High | ✅ **Selected** — sufficient quality for structured DFIR pairs at 20x lower cost, quality filtering downstream catches weak pairs |
| Claude 4 Sonnet | ~$3 input / $15 output | High | Fallback — only if Gemini Flash pilot pass rate is consistently below quality threshold |
| GPT-4o | ~$2.50 input / $10 output | High | Not used |
> [!NOTE]
> **Decision rationale:** Research (LIMA, DEITA, WizardLM/Evol-Instruct) shows that data diversity and quality filtering matter more than raw model capability for SFT data generation. Gemini 2.5 Flash provides sufficient diversity at ~$9 total cost. The Phase 4 quality pipeline (MITRE validator, tool validator, scoring rubric) catches any quality issues downstream. Only one API account (Google AI) is needed. 

### 3.3 Prompt Template Structure

All 5 category templates share a common base structure. Each template also includes **source-type-specific instructions** (§3.3.2) that adapt reasoning expectations to the richness of the source document.

> [!WARNING]
> **Reasoning accuracy is the critical risk in synthesis.** The fixes below address 5 identified failure modes: reasoning-response drift, ungrounded evidence fabrication, source diversity mismatch, pairs/doc padding, and overconfident outputs. See prompt template analysis artifact for full rationale.

#### 3.3.1 Base Template

```markdown
## System Prompt

You are an expert DFIR practitioner and cybersecurity instructor
creating training data for a specialized forensic AI assistant
called Shepherd.

## Rules

### Instruction Quality
1. Instructions must sound like real questions from a SOC analyst
   or incident responder during an active investigation
2. Vary difficulty: 30% junior, 50% mid, 20% senior

### Reasoning Quality
3. Responses MUST begin with a canonical `<reasoning>` block followed by a
   practitioner-ready final answer. The `<reasoning>` block is not private
   scratchpad text; it is an auditable, source-grounded rationale.

4. The `<reasoning>` block MUST use explicit linked reasoning IDs:
   - `E1`, `E2`, ... for evidence. Quote or reference specific artifact data
     from the source document, such as event IDs, file paths, registry keys,
     commands, rule fields, tool output fields, CVEs, or IOCs.
   - `A1 [uses E1]`, `A2 [uses E1,E2]`, ... for analysis. Explain what the
     referenced evidence means: normal vs abnormal, suspicious vs benign,
     and why.
   - `C1 [uses E1,A1]`, ... for conclusions. State findings with explicit
     confidence (high/medium/low), and cite the evidence/analysis IDs that
     support the finding.
   - `CV1 [applies_to C1]`, ... for caveats. State what additional evidence
     would strengthen, weaken, or disprove the conclusion.

5. Every conclusion MUST cite at least one evidence ID and one analysis ID.
   Every caveat MUST apply to a specific conclusion. The final answer MUST NOT
   introduce findings that are absent from the linked conclusions.

6. Reasoning that reaches conclusions without citing evidence IDs is INVALID.

### Grounding Constraint
7. All forensic details (e.g. file paths, registry keys, event IDs, tool output 
   fields) MUST be either:
   a) Directly stated in the source document, OR
   b) Well-established forensic facts (standard Windows/Linux artifact paths,
      documented event ID meanings, known tool behaviors)
   
   If you reference forensic details beyond the source document, mark them
   with [GENERAL KNOWLEDGE] to distinguish from source-grounded facts.
   
   NEVER invent specific file paths, hash values, IP addresses, or tool
   output that isn't in the source document or isn't standard forensic
   knowledge.

### Technique Mapping
8. Map behaviors to MITRE ATT&CK or ATLAS technique IDs
9. For ambiguous technique mappings where evidence is not conclusive, use
   the suffix '?' to indicate a candidate technique requiring corroboration:
   e.g., "mitre_techniques": ["T1055?", "T1574.002"]

### Uncertainty Calibration
10. NEVER declare compromise without corroborating evidence
11. At least 20% of generated pairs MUST demonstrate uncertainty or ambiguity.
   Examples of well-calibrated uncertainty:
   - "This COULD indicate T1055 process injection, but the same pattern
     also appears in legitimate .NET JIT compilation. Check for unsigned
     DLLs loaded from TEMP directories to differentiate."
   - "Based on Event ID 4688 alone, we cannot distinguish between an
     administrator's legitimate PsExec use and lateral movement. Correlate
     with 4624 Type 3 logon events on the target host."

## Task Category: {category_name}
{category_specific_instructions}

## Source Type: {source_type}
{source_type_instructions}

## Source Document
{document_content}

## Output Format
[
  {
    "instruction": "...",
    "response": "<reasoning>\nE1: [source-grounded evidence]\nA1 [uses E1]: [analysis of evidence]\nC1 [uses E1,A1] Confidence: medium. [conclusion]\nCV1 [applies_to C1]: [caveat or corroboration need]\n</reasoning>\n\n[Practitioner-ready final answer]",
    "category": "{category_name}",
    "difficulty": "junior|mid|senior",
    "confidence": "high|medium|low",
    "mitre_techniques": ["T1xxx.xxx", ...],
    "atlas_techniques": ["AML.T00xx", ...],
    "tools_referenced": ["...", ...],
    "source_doc_id": "{doc_id}",
    "taxonomy_refs": ["W7", "A2"],
    "grounding": "source_only|source_plus_general"
  }
]
```

> [!NOTE]
> **Key change from original template:** The separate `thinking` and `response` fields are merged into a single `response` field using canonical `<reasoning>` tags. The reasoning is an auditable linked rationale, not hidden chain-of-thought. ID references (`E1`, `A1`, `C1`, `CV1`) prevent reasoning-response drift by making every conclusion traceable to evidence and analysis. A packaging exporter MAY convert `<reasoning>` to `<think>` only for a model-specific training view if GLM-4.7-Flash benefits from that exact tag.

#### 3.3.2 Source-Type-Specific Instructions

These are injected via the `{source_type_instructions}` variable based on the source document's origin. They calibrate the teacher model's reasoning depth to match the available evidence.

**Detection Rules** (Sigma, Hayabusa):
```markdown
The source is a detection rule. Focus questions on:
- What does this rule detect and why is this behavior suspicious?
- What would a true positive vs false positive look like?
- What corroborating evidence should an analyst look for?

DO NOT invent forensic artifact details beyond what the rule references.
For corroborating evidence, state what TYPE of evidence (e.g., "check for
persistence mechanisms") rather than fabricating specific paths unless you
are certain of the standard path.
```

**Artifact Definitions** (KAPE, ForensicArtifacts, OSSEM):
```markdown
The source is an artifact definition. Focus questions on:
- What is this artifact and what does it tell an investigator?
- What's normal vs abnormal in this artifact?
- How does it relate to attack techniques?

Since the source defines artifact location/structure only, you MAY draw on
general forensic knowledge for interpretation, but mark any non-source claims
with [GENERAL KNOWLEDGE]. Your reasoning should explain WHY this artifact is
forensically relevant, not just describe what it is.

Generate fewer pairs (1-2) for thin definitions to avoid padding with
invented content.
```

**TTP Descriptions** (ATT&CK, ATLAS, Atomic Red Team):
```markdown
The source is a technique/procedure description. Focus on practical
investigation: given evidence of this technique, what should an analyst
do next?

Use the detection guidance in the source document. The source provides
rich context — generate multiple pairs covering different investigation
angles (detection, triage, response, reporting).
```

**Threat Advisories** (CISA, KEV):
```markdown
The source is a threat advisory or vulnerability catalog entry. Focus on:
- Triage: how to prioritize this threat in an active environment
- IOC operationalization: how to search for these indicators
- Response: what containment/remediation steps are appropriate

Use the specific IOCs, CVEs, and remediation guidance from the source.
DO NOT invent IOC values not present in the source document.
```

**Abuse Databases** (LOLBAS, GTFOBins, HijackLibs, LOLDrivers):
```markdown
The source documents how a legitimate binary/library/driver can be abused.
Focus questions on:
- How would this abuse appear in forensic artifacts?
- What detection logic would catch this misuse?
- What distinguishes legitimate use from malicious use?

For HijackLibs/LOLDrivers entries with minimal fields, generate 1-2 pairs
maximum. Do not pad with invented scenarios.
```

**Tool Documentation** (Volatility 3, Velociraptor VQL):
```markdown
The source is forensic tool documentation. Focus questions on:
- Interpreting tool output: what do specific fields/values mean?
- When and why to use this tool/plugin during an investigation
- How to correlate this tool's output with other evidence sources

Use the plugin descriptions, parameters, and output schemas from the source.
```

**Practitioner Workflows** (Cybersecurity Agent Skills):
```markdown
The source is a structured practitioner workflow with step-by-step
investigation/detection procedures. Focus questions on:
- Decision-making: why choose this approach over alternatives?
- Interpretation: what do specific outputs/results mean?
- Troubleshooting: what if the expected evidence isn't found?
- Adaptation: how does this workflow change in different environments?

DO NOT generate pairs about technique definitions — use the workflow's
step-by-step procedure as the primary source material. The technique
context is available in other sources (ATT&CK, Sigma).

The source may contain tool-specific commands. Generate pairs that
test understanding of the commands and their output, not just
copy-paste of the procedure.
```

#### 3.3.3 Category-Specific Instructions

These are injected via the `{category_specific_instructions}` variable based on the assigned task category. The four original categories (Artifact Analysis, TTP Identification, Detection Engineering, Incident Report Generation) use straightforward task-focused instructions in their respective prompt template files. Below are the instructions for the two additions.

**Triage & Threat Hunting** (`triage_and_hunting.md`):
```markdown
Generate instruction pairs covering BOTH reactive triage AND proactive
threat hunting.

### Reactive Triage (60% of pairs for this category)
- Given an initial indicator (alert, IOC, user report), what should the
  analyst investigate first, second, third?
- What evidence should be collected and preserved?
- How should the analyst prioritize competing investigation threads?
- What are the escalation criteria?

### Proactive Threat Hunting (40% of pairs for this category)
- Given a technique or threat actor profile, formulate a hunting hypothesis
  Example: "If an attacker used T1053.005 (Scheduled Task), what artifacts
  would exist and how would I search for them proactively?"
- Design hunt queries: what would you search for in logs/SIEM/EDR to detect
  this technique WITHOUT a prior alert?
- Baseline analysis: what does NORMAL look like for this artifact/behavior,
  and what deviations indicate compromise?
- Hunt playbook steps: systematic approach to validate or refute a hypothesis

### Threat Hunting Pair Examples
- "How would you proactively hunt for Kerberoasting in an environment with
  no prior alerts?" → systematic approach using 4769 events, service account
  enumeration, ticket encryption downgrade detection
- "What baseline would you establish for PowerShell usage before hunting for
  malicious scripts?" → normal script paths, common cmdlets, expected users,
  execution policy settings, then deviation indicators
- "Given intelligence that APT29 targets your sector, what hunt hypotheses
  would you prioritize?" → map APT29 TTPs to available telemetry, prioritize
  by detection coverage gaps

### Calibration
- Hunting pairs should assume NO prior alert — the analyst is proactively
  searching based on threat intelligence, technique knowledge, or anomaly
  detection
- Include at least one pair per source document that demonstrates the
  difference between "investigating an alert" (triage) vs "hunting without
  an alert" (threat hunting)
```
---

#### 3.3.4 Phase 3 Inline Rejection Gates

Do not rely on Phase 4 to catch obvious generation failures. Phase 3 must
reject bad model output before writing it to `data/synthesized/`.

Reject a generation batch if any of the following are true:

- Model output is not strict JSON or not a JSON array.
- Number of generated pairs differs from the requested `pairs_requested`.
- Any pair fails the `InstructionPair` schema.
- `source_doc_id`, `source`, `category`, or `difficulty` does not match the
  prompt/source document.
- `<reasoning>` is missing, has empty evidence/analysis lines, has conclusions
  without evidence and analysis IDs, or has caveats that do not apply to a
  conclusion.
- Final answer text after `</reasoning>` is empty.
- `taxonomy_refs` include IDs outside the 57-category taxonomy.
- MITRE ATT&CK or ATLAS IDs have invalid formats.
- Concrete indicators (CVEs, hashes, IPs, or domains) appear in the generated
  pair but not in the source document.

Pair counts are also source-richness aware:

```python
if doc.word_count < 250:
    pairs = 1
elif doc.content_type in {"artifact_definition", "event_dictionary", "abuse_database"}:
    pairs = min(configured_pairs, 2)
else:
    pairs = configured_pairs
```

This is a Phase 3 cleanliness gate. Phase 4 still performs deeper quality
scoring, deduplication, distribution audits, and manual spot checks.

### 3.4 Volume Targets

**Core + Tier 1-2 (confirmed scope):**

| Source | Raw Docs | Pairs/Doc | Total Pairs | Rationale |
|---|---|---|---|---|
| C1: MITRE ATT&CK | ~800 | 5 | ~4,000 | Rich source — multiple investigation angles |
| C2: SigmaHQ Rules | ~3,000 | 3 | ~9,000 | Largest volume, focused content |
| C3: Atomic Red Team | ~800 | 4 | ~3,200 | TTP procedures + detection |
| C4: CISA Advisories | ~500 | 5 | ~2,500 | Rich triage + reporting content |
| C5: Volatility 3 Docs | ~75 | 4 | ~300 | Memory forensics tool docs |
| C6: MITRE ATLAS | ~65 | 4 | ~260 | AI/LLM threats |
| C7: CISA KEV Catalog | ~250 | 3 | ~750 | Vulnerability context |
| AF1: KAPE Targets | ~1,000 | 2 | ~2,000 | Thin source — artifact path definitions only |
| AF2: Hayabusa Rules | ~4,000 | 2 | ~8,000 | Overlap with Sigma → lower pairs/doc |
| AF3: LOLBAS + GTFOBins | ~600 | 3 | ~1,800 | Moderate richness (abuse functions + detection) |
| AF4: ForensicArtifacts | ~500 | 2 | ~1,000 | Thin source — YAML artifact definitions only |
| AF5: Velociraptor | ~500 | 3 | ~1,500 | VQL queries + descriptions |
| AF6: HijackLibs | ~350 | 1-2 | ~525 | Very thin — 3-5 fields per entry |
| AF7: LOLDrivers | ~400 | 1-2 | ~600 | Very thin — hash + metadata per entry |
| AF8: OSSEM Dicts | ~250 | 1-2 | ~375 | Field definitions only |
| AF9: Cybersecurity Skills | ~475 | 3 | ~1,425 | Rich practitioner workflows (filtered ≥500 tokens) |
| **Core + Tier 1-2 Total** | **~13,565** | | **~37,235** | |
| **After quality filtering (~70%)** | | | **~26,065** | Target: 20,000-25,000 |

> [!NOTE]
> **Variable pairs/doc rationale:** Thin sources (KAPE, ForensicArtifacts, HijackLibs, LOLDrivers, OSSEM) get 1-2 pairs/doc because forcing 3+ pairs from a document with only a few structured fields causes the teacher model to pad with invented content — the primary source of hallucinated forensic details in the training data. Rich sources (ATT&CK, CISA advisories) get 4-5 pairs/doc because they contain enough material for multiple legitimate investigation angles.

### 3.5 Pilot Protocol (Week 5, Days 3-5)

1. Select pilot sample covering all source types and richness levels:
   - 25 docs per Core source (C1-C4) + all ATLAS (C6) + ~10 Volatility docs (C5) + ~10 KEV entries (C7)
   - 20 KAPE targets (AF1) + 30 Hayabusa rules (AF2) + 15 LOLBAS/GTFOBins (AF3)
   - 15 ForensicArtifacts (AF4) + 10 Velociraptor (AF5) + 10 HijackLibs (AF6) + 10 LOLDrivers (AF7) + 10 OSSEM (AF8)
   - 15 Cybersecurity Skills (AF9) — mix of rich/thin to validate content-length filter
   - **Total: ~315 source documents**
2. Run synthesis with Gemini 2.5 Flash (primary) + Claude Sonnet (comparison subset of 50 docs)
3. Manually review 100% of pilot output (~700-900 pairs)
4. Score on quality rubric with **specific attention to:**
   - [ ] **Grounding check:** Do responses cite evidence from the source doc, or fabricate details?
   - [ ] **Reasoning coherence:** Does the `<reasoning>` trace use valid evidence/analysis/conclusion/caveat links, and does the final answer follow the linked conclusions?
   - [ ] **Uncertainty calibration:** Are ≥20% of pairs appropriately uncertain/ambiguous?
   - [ ] **Thin-source quality:** Are pairs from KAPE/ForensicArtifacts/HijackLibs realistic, or padded?
5. **Cross-source dedup check:** verify Sigma vs Hayabusa pairs don't produce near-duplicates
6. Iterate prompts, re-run if pass rate < 65%

**Gate:** Pilot pass rate ≥ 65% before proceeding to full synthesis.

### Phase 3 Deliverables
- [ ] 5 category prompt templates + 8 source-type sub-templates — tested and iterated via pilot
- [ ] Inline rejection gates for invalid JSON, source mismatch, bad reasoning links, invalid taxonomy refs, invented indicators, and pair-count violations
- [ ] Synthesis pipeline script with batching, retries, rate limits
- [ ] Pilot results documented (including grounding/reasoning/uncertainty audit)
- [ ] Full synthesis run: ~37,200 raw instruction pairs (Core + Tier 1-2)
- [ ] Generation manifest per batch

---

## Phase 4: Quality Assurance (Week 7 – Week 8 Day 3)

### 4.1 Automated Quality Scoring

| Criterion | Weight | Automated? |
|---|---|---|
| **Factual Accuracy** | 25% | Partial (validate ATT&CK + ATLAS IDs, tool names) |
| **Reasoning Quality** | 25% | Yes (linked reasoning markers, reference integrity, step count) |
| **Operational Relevance** | 20% | Heuristic (tool/artifact references) |
| **Specificity** | 15% | Yes (response length, named entities) |
| **Completeness** | 15% | Yes (required field checks) |

**Threshold: ≥ 3.5 composite score to pass.**

### 4.2 Validators

- **MITRE Validator:** Validates both ATT&CK technique IDs AND ATLAS technique IDs against their respective STIX datasets
- **Tool Name Validator:** Validates against allowlist of known DFIR tools
- **Structural Validator:** JSON schema compliance, required fields, valid labels
- **Taxonomy Validator:** Validates `taxonomy_refs` against the 57-category taxonomy
- **Reasoning Link Validator:** Validates `<reasoning>` structure, evidence ID references, conclusion support, caveat links, and final-answer consistency

### 4.3 Distribution Audit

After filtering, verify:
- Task category distribution (within ±5% of plan)
- Difficulty distribution (30/50/20 ±5%)
- ATT&CK tactic coverage (all 14 tactics)
- ATLAS tactic coverage (validate AI/ML technique distribution)
- **Taxonomy coverage heatmap** (which of 57 categories are represented, at what density)
- Source balance (no single source > 50%)

### 4.4 Manual Spot-Check

- 100 randomly selected pairs from filtered set
- Score on same rubric, validate automated scores

### Phase 4 Deliverables
- [ ] Quality scorer with ATT&CK + ATLAS validation
- [ ] Near-duplicate detector
- [ ] Distribution audit with 57-category taxonomy heatmap
- [ ] Manual spot-check (100 pairs)
- [ ] Filtered dataset: ~10,000-15,000 quality pairs

---

## Phase 5: Dataset Packaging (Week 8, Days 3-5)

### 5.1 Output Schema

```json
{
  "id": "dfir-00001",
  "conversations": [
    {
      "role": "system",
      "content": "You are Shepherd, a DFIR AI assistant..."
    },
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "<reasoning>\n{linked_reasoning}\n</reasoning>\n\n{response}"
    }
  ],
  "metadata": {
    "category": "ttp_identification",
    "difficulty": "mid",
    "mitre_techniques": ["T1059.001"],
    "atlas_techniques": [],
    "tools_referenced": ["Volatility 3"],
    "taxonomy_refs": ["W7", "W10"],
    "source_doc_id": "mitre-attack-T1059.001",
    "source": "mitre_attack",
    "quality_score": 4.2
  }
}
```

Canonical packaged data uses `<reasoning>`. A model-specific exporter may create
a GLM training view that maps `<reasoning>` to `<think>`, but the canonical
dataset keeps `<reasoning>` for auditability and validator compatibility.

### 5.2 Train/Validation/Test Split

| Split | Proportion | Estimated Size |
|---|---|---|
| Train | 80% | ~8,000-12,000 |
| Validation | 10% | ~1,000-1,500 |
| Test | 10% | ~1,000-1,500 |

**Split by source document ID** to prevent data leakage.

### 5.3 Dataset Card

Includes: source breakdown, generation methodology, task/difficulty distributions, ATT&CK tactic coverage, ATLAS technique coverage, **57-category taxonomy heatmap**, known limitations, ethical considerations, reproduction instructions.

### Phase 5 Deliverables
- [ ] Chat-formatted JSONL (train/val/test) with canonical `<reasoning>`
- [ ] Optional GLM-specific export view if `<think>` tags are required by the training recipe
- [ ] Dataset card with taxonomy coverage heatmap
- [ ] Local dataset package on DGX Sparks filesystem
- [ ] Version tag: `v1.0.0`

---

## Phase 6: Fine-Tuning Validation (Weeks 9-10)

### 6.1 Training Setup

| Parameter | Value |
|---|---|
| **Platform** | DGX Sparks (128GB unified memory) |
| **Framework** | Unsloth |
| **Method** | LoRA SFT |
| **LoRA rank** | 32-64 |
| **LoRA alpha** | 64-128 |
| **Learning rate** | 2e-5 |
| **Epochs** | 2-3 |
| **Warmup** | 10% of steps |
| **Scheduler** | Cosine |

### 6.2 Training Protocol

1. **Day 1:** Baseline evaluation on un-finetuned GLM-4.7-Flash
2. **Day 1-2:** Training run 1
3. **Day 2-3:** Analyze results
4. **Day 3-4:** Training run 2 (adjusted)
5. **Day 4-5:** Export best checkpoint to GGUF
6. **Day 5-6:** Integration test in Shepherd

### 6.3 Evaluation Benchmark

50-100 hand-curated examples (NOT from synthesis pipeline):

| Task Type | Metric |
|---|---|
| TTP Identification (incl. ATLAS) | F1 Score |
| IOC Extraction | Precision / Recall |
| Triage Ranking | NDCG@5 |
| Detection Rule Interpretation | Accuracy |
| Report Quality | LLM-as-Judge (1-5) |
| Reasoning Quality | LLM-as-Judge (1-5) |

> [!IMPORTANT]
> Run baseline evaluation BEFORE fine-tuning. Include 5-10 AI/LLM-specific test cases to validate ATLAS coverage impact.

### Phase 6 Deliverables
- [ ] Hand-curated benchmark (50-100 examples, including AI/LLM cases)
- [ ] Baseline scores
- [ ] Fine-tuned LoRA adapter + GGUF export
- [ ] Before/after comparison
- [ ] Integration test in Shepherd
- [ ] Training recipe documented

---

## Handover Package

### Code
- [ ] `dfir-dataset/` repo — full pipeline (9+ collectors, 5 synthesizers, QA, packaging)
- [ ] Shepherd repo — tagged `v0.2.0` with `PAUSE_STATE.md`
- [ ] Fine-tuned model checkpoint + GGUF

### Documentation
- [ ] `HANDOVER.md` — what's done, what's next, decision rationale
- [ ] `ARCHITECTURE.md` — pipeline design
- [ ] `TAXONOMY.md` — full 57-category reference with coverage status
- [ ] `COVERAGE_MAP.md` — what's covered, what sources to add per gap
- [ ] `ADDING_SOURCES.md` — step-by-step for new collectors
- [ ] `PROMPT_GUIDE.md` — prompt iteration guide
- [ ] `QUALITY_RUBRIC.md` — scoring criteria
- [ ] Dataset card on HuggingFace
- [ ] Training recipe

### Successor Roadmap

| Priority | Task | What It Unlocks |
|---|---|---|
| 1 | Add Tier 3 artifact sources (AF10-AF15) | EVTX samples, WADComs, MalAPI, LOTS, Chainsaw, Sysmon configs |
| 2 | Add semi-structured sources (SANS posters, ForensicsWiki, EZ tool docs) | Rich forensic reference content |
| 3 | Add unstructured blog sources (Mandiant, CrowdStrike, Unit 42) | Real IR case studies, richer scenarios |
| 4 | Expand to all task categories (add Malware Analysis, etc.) | Full specialist agent coverage |
| 5 | Add cloud provider docs | Cloud forensics C1-C6 |
| 6 | Add M365 UAL / Google Workspace docs | File storage F1-F5 |
| 7 | Add OWASP LLM Top 10, AI incident databases | Deeper AI/LLM coverage A1-A4 |
| 8 | Add mobile/IoT/OT sources | Mobile M1-M3, IoT/OT OT1-OT2 |
| 9 | Implement two-pass teacher-verifier synthesis | Higher quality ceiling |
| 10 | Scale to 50K+ pairs | Better model performance |
| 11 | Implement CRAFT/RAFT after Shepherd RAG (MVP 4) | Retrieval-augmented training |

---

## Week-by-Week Schedule

| Week | Dates | Phase | Key Activities | Gate |
|---|---|---|---|---|
| **3** | Jun 15-21 | P1 + P2 start | Finalize taxonomy. `BaseCollector`. ATT&CK + Sigma + ATLAS collectors | Taxonomy reviewed |
| **4** | Jun 22-28 | P2 | Atomic RT + CISA + Vol3 collectors. **KAPE + Hayabusa + LOLBAS/GTFOBins** (Tier 1). Run all 9. Validate | ~10,850 docs collected |
| **5** | Jun 29 - Jul 5 | P2 finish + P3 start | Tier 2 collectors (if selected). Prompt templates. **Pilot (~230 docs)** | Pilot ≥ 65% pass |
| **6** | Jul 6-12 | P3 | Full synthesis run (batched) | ~32,000 raw pairs |
| **7** | Jul 13-19 | P3 finish + P4 | Finish synthesis. Quality scoring. Dedup (Sigma/Hayabusa). Filtering | Filtered ≥ 20,000 |
| **8** | Jul 20-26 | P4 finish + P5 | Spot-check. Distribution audit. Package. Upload to HF | v1.0.0 tagged |
| **9** | Jul 27 - Aug 2 | P6 | Baseline eval. Train run 1. Analyze. Train run 2 | Before/after scores |
| **10** | Aug 3-7 | P6 finish + Handover | GGUF export. Integration test. Handover docs | Package complete |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Synthesis prompt quality is poor | High | Medium | Pilot validates before full run |
| API rate limits delay synthesis | Medium | Medium | Exponential backoff; Gemini Flash fallback |
| Quality filter removes too many (< 60%) | High | Low | Iterate prompts, not thresholds |
| Fine-tuned model shows no improvement | High | Medium | Documents gaps for successor iteration |
| CISA scraper breaks | Low | Medium | Supplementary source; can drop |
| ATLAS source too small for meaningful AI/LLM coverage | Medium | Medium | Expected — establishes foundation; successor adds OWASP LLM Top 10 |
| Coverage skews Windows-heavy | Medium | High | Expected and documented; Linux/Cloud improve with Tier 2 sources |
| Sigma/Hayabusa rule duplication inflates pair count | Medium | High | Cross-source dedup in pilot + Phase 4; Hayabusa pairs/doc capped at 2 |
| Tier 1 collector effort exceeds 3-day estimate | Low | Low | All three use identical YAML parsing pattern as Sigma; reuse is trivial |
| Synthesis API cost doubles with Tier 1 sources | Medium | Medium | Gemini Flash for bulk; monitor spend per source; can drop Hayabusa pairs/doc to 1 |

---

## Resolved Decisions (formerly Open Questions)
> Resolved 2026-06-02.
1. **API access:** ✅ Setting up a Google AI account for Gemini 2.5 Flash. Single model, single account. No Claude/GPT-4o accounts needed unless Flash quality is insufficient (fallback plan documented in §3.7).
2. **Dataset hosting:** ✅ Local-only on DGX Sparks filesystem. No HuggingFace. Data loaded via `datasets.load_dataset("json", data_files=...)` — functionally identical to HF hosting for Unsloth training. Data path documented in `HANDOVER.md` for successor.
3. **Shepherd MVP 2 status:** ✅ 3 core MVP 2 items remaining (process_plugin_mismatch finding, report provenance citations, parser/finding tests). 5 refactor gate items deferred to v0.2.1. Tag v0.2.0 after the 3 core items are complete.
4. **DGX Sparks access:** ✅ Dedicated. No scheduling conflicts. Can run 3-4 LoRA rank experiments (16, 32, 64, 128) during weeks 9-10.
5. **Synthesis approach:** ✅ Full LLM generation using Gemini 2.5 Flash for all pairs (~$9 total). No hybrid/template approach — research (LIMA, DEITA, Evol-Instruct) shows diversity from LLM generation outperforms template-based data for SFT, and the cost difference is negligible at Flash pricing.

## Open Questions

1. **Task category confirmation:** Are the 5 categories (including the Triage & Threat Hunting expansion) right for near-term needs?
2. **ATLAS priority:** Should AI/LLM pairs be weighted higher than their source volume suggests, given Shepherd is itself an LLM application?
3. **Taxonomy review:** Should any of the 57 categories be split, merged, or renamed for your team's vocabulary?
