# Benchmark

## Benchmark case schema
```json
{
  "case_id": "phase6-ttp-001",
  "task_type": "ttp_identification",
  "difficulty": "mid",
  "prompt": "Question shown to the model being evaluated.",
  "context": "Optional evidence packet, logs, rule snippet, or scenario.",
  "expected_answer": {
    "required_concepts": [
      {
        "id": "atomic_concept_id",
        "aliases": [
          "short phrase that may appear in a correct answer",
          "another acceptable wording",
          "third paraphrase"
        ],
        "description": "Human-readable explanation of what this concept means."
      }
    ],
    "forbidden_concepts": [
      {
        "id": "forbidden_overclaim_id",
        "aliases": [
          "bad claim wording",
          "another bad wording"
        ],
        "description": "Human-readable explanation of the overclaim or error."
      }
    ],
    "must_include": [
      "backward-compatible short alias for current deterministic scorer"
    ],
    "acceptable_variants": [],
    "must_not_include": [
      "backward-compatible short forbidden phrase"
    ],
    "gold_labels": {}
  },
  "scoring": {
    "metric": "f1",
    "max_points": 5,
    "rubric": []
  },
  "tags": ["windows", "attack", "event_logs"],
  "notes_for_human_reviewer": "Why this case is useful."
}

```

### Answer Key Guidance

Use concept-style answer keys for rubric-scored cases. Do not put long prose
sentences in `must_include` or `must_not_include`.

For each required idea, create a `required_concepts` entry:

- `id`: short snake_case concept name.
- `aliases`: 3-6 short paraphrases that a correct model answer might use.
- `description`: what the concept means for a human reviewer.

For each important overclaim or error, create a `forbidden_concepts` entry:

- `id`: short snake_case concept name.
- `aliases`: 2-5 short bad-claim paraphrases.
- `description`: why this would be wrong.

Keep `must_include` and `must_not_include` populated for backward compatibility
with the current deterministic scorer:

- `must_include` should contain one short representative alias from each
  required concept.
- `must_not_include` should contain one short representative alias from each
  forbidden concept.

Keep structured labels in `gold_labels` whenever possible:

- ATT&CK/ATLAS IDs for TTP cases.
- Normalized IOCs for IOC extraction.
- Ordered action IDs or labels for triage ranking.
- Telemetry, artifacts, platforms, and detection concepts for rubric cases.

The evaluator may require structured model outputs for objective tasks:

- TTP cases: `{"techniques": [...], "answer": "..."}`.
- IOC cases: `{"iocs": [{"type": "...", "value": "..."}], "answer": "..."}`.
- Ranking cases: `{"ranked_actions": [...], "answer": "..."}`.

Keep report, reasoning, artifact-analysis, and other rubric-heavy answers in
natural language so the benchmark still measures analyst-facing response quality.

Rubric scoring should reward atomic evidence coverage, limitations, next pivots,
and avoidance of overclaims. The local judge receives each complete
`acceptable_variants` entry as an independently valid alternative. Judge scores
still need calibration and human review before final Phase 6 claims.

## Prompts

Review all test cases before using for benchmark

### Master prompt

You are creating a held-out benchmark for evaluating a DFIR AI assistant fine-tuned on cybersecurity and forensic instruction data.

Generate benchmark cases that are NOT copied from any training dataset, synthetic training prompt, public benchmark, or memorized Q&A. The cases should be realistic, answerable, and grounded in the evidence provided inside each case.

Each case must include:
- a model-facing prompt;
- any needed evidence/context;
- an expected answer key with `required_concepts`, `forbidden_concepts`,
  backward-compatible `must_include` / `must_not_include`, and `gold_labels`;
- scoring guidance;
- tags;
- notes for a human reviewer.

Do not make the answer depend on hidden knowledge unless the case explicitly asks for general DFIR knowledge. Prefer realistic but original scenarios.

For rubric-scored cases, write concept-style answer keys:
- Use `required_concepts` for ideas a correct answer must cover.
- Use `forbidden_concepts` for overclaims, hallucinations, or wrong inferences.
- Put short aliases in each concept instead of full prose sentences.
- Mirror one short alias per concept into `must_include` / `must_not_include`
  for backward compatibility with substring-based scoring.

Return JSONL only, one JSON object per line, using this schema:
{...schema...}


### TTP identification

Generate 10 DFIR benchmark cases for MITRE ATT&CK TTP identification.

Each case should provide a short incident scenario with process events, command lines, registry/file/network artifacts, or alert context. The evaluated model must identify likely ATT&CK technique IDs and explain the evidence.

Requirements:
- Include Windows, Linux, cloud, and living-off-the-land examples.
- Include at least 2 ambiguous cases where multiple techniques are plausible but only some are strongly supported.
- Include expected ATT&CK technique IDs in gold_labels.techniques.
- Include required_concepts for evidence links, such as specific command lines or artifacts.
- Include forbidden_concepts for common overclaims.
- Keep must_include and must_not_include as short backward-compatible aliases.
- Scoring metric: F1 over technique IDs, plus explanation quality notes.

Return JSONL only.

### IOC extraction

Generate 10 DFIR benchmark cases for IOC extraction.

Each case should contain a noisy incident note, log excerpt, email header, command output, proxy log, DNS log, or malware-analysis snippet. The evaluated model must extract only actionable indicators and classify them.

Requirements:
- Include IPv4, domains, URLs, hashes, file paths, registry keys, email addresses, mutexes, and process names where appropriate.
- Include benign lookalikes that should not be extracted as IOCs.
- Include normalized expected indicators in gold_labels.iocs with type and value.
- Include forbidden_concepts and must_not_include for false positives.
- Include required_concepts for normalization or classification requirements when useful.
- Scoring metric: precision, recall, and F1.

Return JSONL only.

### Triage ranking

Generate 8 DFIR benchmark cases for triage and threat hunting prioritization.

Each case should present 5-8 possible next investigative actions after an alert or early incident signal. The evaluated model must rank the top 5 actions and explain why.

Requirements:
- Cover endpoint, identity, network, cloud, and malware triage.
- Include at least 2 cases where an attractive action is lower priority because it is destructive, slow, or unsupported.
- Include gold_labels.ranked_actions as an ordered list.
- Include acceptable_variants for equivalent ordering when reasonable.
- Include required_concepts for the reasoning behind the highest-priority actions.
- Include forbidden_concepts for destructive, slow, or unsupported recommendations when relevant.
- Scoring metric: NDCG@5.

Return JSONL only.

### Detection rule interpretation

Generate 10 DFIR benchmark cases for detection engineering interpretation.

Each case should include a short Sigma-like, Hayabusa-like, YARA-like, KQL-like, or SIEM rule snippet. The evaluated model must explain:
- what activity the rule detects;
- required log source or telemetry;
- key detection fields;
- likely false positives;
- tuning or validation advice.

Requirements:
- Include at least 3 Windows event/Sysmon cases.
- Include at least 2 Linux audit/process cases.
- Include at least 2 cloud/SaaS cases.
- Include expected_answer.required_concepts with atomic concepts for detection logic,
  required telemetry, key fields, false positives, and tuning or validation points.
- Include forbidden_concepts for common wrong claims such as requiring the wrong
  telemetry source, claiming the rule proves compromise, or ignoring allowlists.
- Keep must_include and must_not_include populated with short representative aliases.
- Scoring metric: rubric accuracy out of 5.

Return JSONL only.

### Artifact analysis

Generate 8 DFIR benchmark cases for forensic artifact analysis.

Each case should give one or more artifacts such as Prefetch, Amcache, ShimCache, SRUM, browser history, shellbags, cron files, systemd units, auth logs, PowerShell logs, registry keys, memory process listings, or file metadata.

The evaluated model must interpret what the artifacts show, what they do not prove, and what corroborating evidence should be collected.

Requirements:
- Include Windows and Linux cases.
- Include at least 2 anti-forensics or uncertainty cases.
- Include expected_answer.required_concepts with atomic concepts for artifact
  meaning, limitations, corroborating evidence, and next pivots.
- Include forbidden_concepts for overconfident conclusions such as treating one
  artifact as proof of maliciousness, operator identity, or non-execution.
- Keep must_include and must_not_include populated with short representative aliases.
- Scoring metric: rubric accuracy out of 5.

Return JSONL only.

### Incident report generation

Generate 6 DFIR benchmark cases for incident report generation.

Each case should provide a compact evidence packet: timeline entries, alerts, hostnames, users, commands, network connections, and containment notes. The evaluated model must write a short incident summary suitable for an analyst handoff.

Requirements:
- Expected answer should include executive summary, timeline, impact, confidence, open questions, and recommended next actions.
- Include at least 1 case where evidence is insufficient for attribution.
- Include at least 1 false-positive or benign-admin case.
- Include required_concepts for required report sections and evidence-grounded conclusions.
- Include forbidden_concepts for unsupported attribution, inflated impact, or invented facts.
- Keep must_include and must_not_include populated with short representative aliases.
- Scoring metric: report quality rubric from 1-5.

Return JSONL only.

### Reasoning and grounding stress tests

Generate 8 DFIR benchmark cases that test reasoning quality, uncertainty, and grounding.

Each case should be designed so that a careless model may hallucinate or overclaim. The evaluated model must stay within the evidence, identify uncertainty, and avoid unsupported conclusions.

Requirements:
- Include incomplete logs, conflicting timestamps, missing host context, partial command lines, and ambiguous alerts.
- Include required_concepts for uncertainty statements, evidence boundaries, and required corroboration.
- Include forbidden_concepts for unsupported claims, certainty inflation, and invented evidence.
- Keep must_include and must_not_include populated with short representative aliases.
- Scoring metric: reasoning quality rubric from 1-5.

Return JSONL only.

### AI/LLM and ATLAS cases

Generate 8 benchmark cases for AI/LLM security and MITRE ATLAS-style incidents.

Each case should involve one of:
- prompt injection against an LLM app;
- data exfiltration through a retrieval system;
- malicious model or dependency supply-chain issue;
- suspicious model-serving infrastructure activity;
- credential exposure in notebooks or ML pipelines;
- AI agent tool misuse.

The evaluated model must identify likely risk, relevant ATLAS or ATT&CK-style behavior, evidence to collect, and containment steps.

Requirements:
- Include gold_labels.atlas_techniques where appropriate.
- Include required_concepts for evidence-based risk, likely ATLAS or ATT&CK-style behavior, evidence to collect, and containment.
- Include forbidden_concepts for hype, unsupported attribution, or claiming model compromise without evidence.
- Keep must_include and must_not_include populated with short representative aliases.
- Scoring metric: mixed rubric out of 5.

Return JSONL only.
