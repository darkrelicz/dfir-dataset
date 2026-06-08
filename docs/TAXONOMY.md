# DFIR Artifact Taxonomy

## 1. Overview
This document serves as a reference for the 57-category artifact taxonomy.
It defines the full landscape of forensic artifacts the model should eventually understand.
This taxonomy is directly related to the 5 task categories, where artifact categories are absorbed as sub-topics.

## 2. Category Tables by Domain
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

## 3. Coverage Mapping
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

## 4. Expanded Scope per Discipline
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


## 5. Summary Table

| Domain | Count | Range | Coverage Tier | Current-Iteration Status |
|---|---|---|---|---|
| Windows | 10 | W1-W10 | Strong / Moderate | Included |
| Linux | 8 | L1-L8 | Strong / Moderate | Included |
| Network | 6 | N1-N6 | Weak | Deferred |
| SIEM | 3 | S1-S3 | Moderate | Included |
| Cloud | 6 | C1-C6 | Weak | Deferred |
| File Storage & Data Access | 5 | F1-F5 | Weak | Deferred |
| AI / LLM Threats | 4 | A1-A4 | Strong | Included |
| Mobile | 3 | M1-M3 | Weak | Deferred |
| Anti-Forensics | 4 | AF1-AF4 | Strong / Weak | Partial |
| Threat Intelligence | 2 | TI1-TI2 | Moderate / Weak | Partial |
| IoT / OT / ICS | 2 | OT1-OT2 | Weak | Deferred |
| Virtualization | 1 | V1 | Weak | Deferred |
| Supply Chain | 1 | SC1 | Moderate | Included |
| Compliance / Legal | 2 | CL1-CL2 | Weak | Deferred |
| **Total** | **57** | | | |
