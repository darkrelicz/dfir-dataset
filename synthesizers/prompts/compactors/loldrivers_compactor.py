from collections.abc import Iterable

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    limit_text,
    markdown_sections,
    section_body,
)


MAX_HASHES = 30
MAX_RESOURCES = 8
MAX_SAMPLES = 14
SAMPLE_CHAR_LIMIT = 620


def compact_loldriver_for_prompt(doc: RawDocument, content: str) -> str:
    metadata = doc.metadata
    driver_name = str(metadata.get("driver_name") or doc.title.removeprefix("LOLDriver: "))
    lines: list[str] = [f"# LOLDriver: {driver_name}", ""]

    append_metadata_line(lines, "Driver ID", metadata.get("driver_id"))
    append_metadata_line(lines, "Category", metadata.get("category"))
    append_metadata_line(lines, "Tags", metadata.get("tags"))
    append_metadata_line(lines, "MITRE ATT&CK", metadata.get("mitre_id"))
    append_metadata_line(lines, "CVEs", metadata.get("cves"))
    append_metadata_line(lines, "Verified", metadata.get("verified"))
    append_metadata_line(lines, "Use Case", metadata.get("usecase"))
    append_metadata_line(lines, "Privileges", metadata.get("privileges"))
    append_metadata_line(lines, "OS", metadata.get("operating_system"))
    append_metadata_line(lines, "Vendors", metadata.get("vendors"))
    append_metadata_line(lines, "Products", metadata.get("products"))
    sample_count = int(metadata.get("sample_count") or 0)
    if sample_count:
        lines.append(f"**Known sample count**: {sample_count}")
    lines.append("")

    _, sections = markdown_sections(content)
    abuse_details = section_body(sections, "Abuse Details")
    if abuse_details:
        lines.append("## Abuse Details")
        lines.append(abuse_details.strip())
        lines.append("")

    hashes = list_values(metadata.get("hashes"))
    if hashes:
        lines.append("## Hashes")
        lines.append(f"Selected {min(len(hashes), MAX_HASHES)} of {len(hashes)} hash value(s).")
        for hash_value in hashes[:MAX_HASHES]:
            lines.append(f"- `{hash_value}`")
        omitted = len(hashes) - MAX_HASHES
        if omitted > 0:
            lines.append(f"- [{omitted} additional hash value(s) omitted]")
        lines.append("")

    samples = select_samples(metadata.get("samples") or [])
    if samples:
        lines.append("## Known Vulnerable Samples")
        lines.append(
            f"Selected {len(samples)} of {sample_count or len(samples)} sample block(s), "
            "prioritizing distinct names, hashes, HVCI notes, and PE metadata."
        )
        lines.append("")
        for sample in samples:
            lines.append(format_sample(sample))
            lines.append("")

    detections = metadata.get("detections") or []
    if detections:
        lines.append("## Detection")
        for detection in detections:
            if not isinstance(detection, dict):
                continue
            detection_type = detection.get("type")
            detection_value = detection.get("value")
            if detection_type and detection_value:
                lines.append(f"- **{detection_type}**: {detection_value}")
        lines.append("")

    resources = list_items(section_body(sections, "Resources"))
    if resources:
        lines.append("## Resources")
        for resource in resources[:MAX_RESOURCES]:
            lines.append(f"- {resource}")
        omitted = len(resources) - MAX_RESOURCES
        if omitted > 0:
            lines.append(f"- [{omitted} additional resource(s) omitted]")
        lines.append("")

    lines.append(
        "[Prompt compaction note: repeated LOLDrivers sample blocks and long hash "
        "lists were capped. Full driver entry remains in the raw corpus.]"
    )

    compacted = "\n".join(lines).strip()
    if len(compacted) >= len(content):
        return content
    return compacted


compact_for_prompt = compact_loldriver_for_prompt


def append_metadata_line(lines: list[str], label: str, value: object) -> None:
    values = list_values(value)
    if values:
        lines.append(f"**{label}**: {', '.join(values)}")


def list_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def select_samples(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    scored: list[tuple[int, int, dict]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, sample in enumerate(value):
        if not isinstance(sample, dict):
            continue
        key = (
            str(sample.get("filename") or ""),
            str(sample.get("machine_type") or ""),
            str(sample.get("imphash") or ""),
            str((sample.get("hashes") or {}).get("sha256") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        scored.append((sample_score(sample), index, sample))

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = scored[:MAX_SAMPLES]
    selected.sort(key=lambda item: item[1])
    return [sample for _, _, sample in selected]


def sample_score(sample: dict) -> int:
    score = 0
    if str(sample.get("loads_despite_hvci", "")).lower() == "true":
        score += 8
    for field in ("original_filename", "internal_name", "product", "company"):
        if sample.get(field):
            score += 1
    if sample.get("machine_type"):
        score += 1
    if sample.get("imphash"):
        score += 2
    if sample.get("hashes", {}).get("sha256"):
        score += 2
    return score


def format_sample(sample: dict) -> str:
    lines = [f"### {sample.get('filename') or 'Unknown sample'}"]
    for label, key in (
        ("Description", "description"),
        ("Original Filename", "original_filename"),
        ("Internal Name", "internal_name"),
        ("Company", "company"),
        ("Publisher", "publisher"),
        ("Product", "product"),
        ("Product Version", "product_version"),
        ("File Version", "file_version"),
        ("Machine Type", "machine_type"),
        ("Creation Timestamp", "creation_timestamp"),
        ("Imphash", "imphash"),
        ("Loads Despite HVCI", "loads_despite_hvci"),
    ):
        value = sample.get(key)
        if value not in ("", None, []):
            lines.append(f"- **{label}**: {value}")

    hashes = sample.get("hashes") or {}
    for hash_type in ("sha256", "sha1", "md5"):
        hash_value = hashes.get(hash_type)
        if hash_value:
            lines.append(f"- **{hash_type.upper()}**: `{hash_value}`")

    return limit_text("\n".join(lines), SAMPLE_CHAR_LIMIT)


def list_items(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- "):
            items.append(line.removeprefix("- ").strip())
    return items
