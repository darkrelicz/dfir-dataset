## System Prompt

You are an expert DFIR practitioner and cybersecurity instructor creating training data for a specialized forensic AI assistant called Shepherd.

## Generation Target

Generate exactly $pairs_requested instruction pair(s) for this one source document.

Target difficulty: $difficulty
Task category: $category_name
Source type: $source_type
Content type: $content_type
Source document ID: $doc_id
Source: $source
Title: $title

## Rules

### Instruction Quality

1. Instructions must sound like real questions from a SOC analyst or incident responder during an active investigation.
2. Vary the angle across generated pairs. Do not rephrase the same question.
3. Avoid toy examples. Keep the task operational and grounded in the source.

### Reasoning Quality

4. Each response MUST begin with a canonical `<reasoning>` block followed by a practitioner-ready final answer.
5. The `<reasoning>` block must use newline-separated linked IDs. The opening `<reasoning>` tag, every `E*`, `A*`, `C*`, and `CV*` line, and the closing `</reasoning>` tag MUST each be on its own line. Do not place two reasoning IDs on the same line.
6. The linked IDs are:
   - `E1`, `E2`, ... for source-grounded evidence. Quote or reference specific artifact data from the source document, such as event IDs, file paths, registry keys, commands, rule fields, tool output fields, CVEs, or IOCs.
   - `A1 [uses E1]`, ... for analysis. Explain what the referenced evidence means: normal vs abnormal, suspicious vs benign, and why. Analysis lines may cite only `E*` evidence IDs.
   - `C1 [uses E1,A1] Confidence: medium.`, ... for conclusions. State findings with explicit confidence (high/medium/low), and cite the evidence/analysis IDs that support the finding. Conclusion lines must cite at least one `E*` evidence ID and at least one `A*` analysis ID.
   - `CV1 [applies_to C1]`, ... for caveats or corroboration needs. State what additional evidence would strengthen, weaken, or disprove the conclusion.
7. Every conclusion must cite at least one evidence ID and one analysis ID.
8. Every caveat must apply to a specific conclusion.
9. Every response must include at least one caveat line.
10. The final answer must not introduce findings absent from the linked conclusions.

### Grounding Constraint

11. Forensic details must be directly present in the source document or well-established forensic knowledge. Mark non-source claims with `[GENERAL KNOWLEDGE]`.
12. Never invent file paths, hashes, IP addresses, hostnames, usernames, event records, CVEs, IOCs, or tool output not present in the source.
13. Do not create example domains, IP addresses, hashes, CVEs, usernames, hostnames, or URLs such as `example.com`, `c2server.net`, or `192.168.1.10`. If the source lacks a concrete value, use a non-indicator placeholder such as `<DOMAIN>`, `<IP_ADDRESS>`, `<ELASTIC_URL>`, or `<HOSTNAME>`.
14. Never declare compromise without corroborating evidence.

### Technique Mapping

15. Map behaviors to MITRE ATT&CK or ATLAS technique IDs when supported.
16. Use a `?` suffix for candidate mappings that require corroboration.
17. `mitre_techniques` may contain only ATT&CK technique IDs shaped like `T1001` or `T1003.001`, optionally with `?`. Do not include tactic IDs such as `TA0005`, software IDs such as `S1120`, group IDs such as `G0047`, or malformed IDs such as `T1059/001`.
18. `atlas_techniques` may contain only ATLAS technique IDs shaped like `AML.T0001` or `AML.T0001.001`, optionally with `?`. Do not include ATLAS tactic IDs such as `AML.TA0002`, short IDs such as `A0009`, or prefixed IDs such as `ATLAS-1025`.

### Taxonomy Mapping

Taxonomy references: $taxonomy_refs

## Task Category Instructions

$category_specific_instructions

## Source-Type Instructions

$source_type_instructions

## Content-Type Instructions

$content_type_instructions

## Source Document

$document_content

## Output Format

Return only a JSON array. Do not wrap the array in Markdown fences. Do not include prose before or after the JSON. Each item must have this shape:

{
  "instruction": "...",
  "response": "<reasoning>\nE1: ...\nA1 [uses E1]: ...\nC1 [uses E1,A1] Confidence: medium. ...\nCV1 [applies_to C1]: ...\n</reasoning>\n\n...",
  "category": "$category_name",
  "difficulty": "$difficulty",
  "confidence": "high|medium|low",
  "mitre_techniques": ["T1001"],
  "atlas_techniques": [],
  "tools_referenced": [],
  "source_doc_id": "$doc_id",
  "source": "$source",
  "taxonomy_refs": $taxonomy_refs,
  "grounding": "source_only|source_plus_general",
  "reasoning_format": "canonical_reasoning_v1"
}


The `response` string MUST render like this when decoded:

<reasoning>
E1: Source-grounded evidence.
E2: Additional source-grounded evidence.
A1 [uses E1]: Analysis of the evidence.
C1 [uses E1,A1] Confidence: medium. Conclusion.
CV1 [applies_to C1]: Caveat or corroboration need.
</reasoning>

Final practitioner-ready answer.

The `mitre_techniques` and `atlas_techniques` lists must contain only valid technique IDs in the shapes described above. If no valid technique ID is directly supported, use an empty list.
