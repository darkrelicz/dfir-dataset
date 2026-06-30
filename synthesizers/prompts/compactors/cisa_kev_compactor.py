from datetime import date

from collectors.schemas import RawDocument
from synthesizers.prompts.compactors.prompt_compactors import (
    COMPACTED_SOURCE_NOTE,
    limit_text,
)


MAX_CVE_IDS = 80
MAX_DETAILS = 20
MAX_PRODUCTS = 45
DETAIL_CHAR_LIMIT = 760
DESCRIPTION_CHAR_LIMIT = 360
NOTES_CHAR_LIMIT = 240
ACTION_CHAR_LIMIT = 260


def compact_cisa_kev_for_prompt(doc: RawDocument, content: str) -> str:
    metadata = doc.metadata
    vendor = str(metadata.get("vendor") or doc.title.removeprefix("CISA KEV: "))
    products = [str(value) for value in metadata.get("products", []) if value]
    cve_ids = [str(value) for value in metadata.get("cve_ids", []) if value]
    cve_count = int(metadata.get("cve_count", len(cve_ids)))
    ransomware_count = int(metadata.get("ransomware_linked_count", 0))

    lines: list[str] = [f"# CISA KEV: {vendor}", ""]
    lines.append(f"**Vendor**: {vendor}")
    if products:
        lines.append(
            f"**Products**: {', '.join(products[:MAX_PRODUCTS])}"
            + more_suffix(len(products), MAX_PRODUCTS)
        )
    if cve_count:
        lines.append(f"**Total CVEs**: {cve_count}")
    lines.append(f"**Ransomware-linked**: {ransomware_count}")
    catalog_version = metadata.get("catalog_version")
    if catalog_version:
        lines.append(f"**Catalog version**: {catalog_version}")
    if cve_ids:
        lines.append(
            f"**CVE IDs sampled**: {', '.join(cve_ids[:MAX_CVE_IDS])}"
            + more_suffix(len(cve_ids), MAX_CVE_IDS)
        )
    lines.append("")

    details = parse_kev_details(content)
    if details:
        selected = select_kev_details(details)
        lines.append("## Selected Vulnerabilities")
        lines.append(
            f"Selected {len(selected)} of {len(details)} KEV detail block(s), "
            "prioritizing ransomware-linked and recent catalog additions."
        )
        lines.append("")
        for detail in selected:
            lines.append(format_kev_detail(detail))
            lines.append("")

    lines.append(COMPACTED_SOURCE_NOTE)

    compacted = "\n".join(lines).strip()
    if len(compacted) >= len(content):
        return content
    return compacted


compact_for_prompt = compact_cisa_kev_for_prompt


def parse_kev_details(content: str) -> list[dict[str, str]]:
    details_body = content.split("## Details", 1)[-1]
    blocks: list[str] = []
    current: list[str] = []

    for line in details_body.splitlines():
        if line.startswith("### "):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return [parse_kev_block(block) for block in blocks if block.strip()]


def parse_kev_block(block: str) -> dict[str, str]:
    detail: dict[str, str] = {}
    lines = block.splitlines()
    if lines:
        heading = lines[0].removeprefix("### ").strip()
        if ":" in heading:
            cve, name = heading.split(":", 1)
            detail["cve"] = cve.strip()
            detail["name"] = name.strip()
        else:
            detail["cve"] = heading

    for line in lines[1:]:
        if not line.startswith("- **") or "**:" not in line:
            continue
        label, value = line.removeprefix("- **").split("**:", 1)
        normalized = normalize_label(label)
        detail[normalized] = value.strip()
    return detail


def normalize_label(label: str) -> str:
    label = label.lower().strip()
    if "ransomware" in label:
        return "ransomware"
    return label.replace(" ", "_")


def select_kev_details(details: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(details) <= MAX_DETAILS:
        return details

    scored = [
        (kev_detail_score(detail), index, detail) for index, detail in enumerate(details)
    ]
    scored.sort(key=lambda item: (-item[0][0], item[0][1], item[1]))
    selected = scored[:MAX_DETAILS]
    selected.sort(key=lambda item: item[1])
    return [detail for _, _, detail in selected]


def kev_detail_score(detail: dict[str, str]) -> tuple[int, int]:
    score = 0
    if detail.get("ransomware", "").lower() == "yes":
        score += 10_000

    added = parse_iso_date(detail.get("date_added", ""))
    if added:
        score += added.toordinal()

    return score, -due_date_ordinal(detail)


def due_date_ordinal(detail: dict[str, str]) -> int:
    due = parse_iso_date(detail.get("due_date", ""))
    if not due:
        return 0
    return due.toordinal()


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_kev_detail(detail: dict[str, str]) -> str:
    lines = [f"### {detail.get('cve', 'CVE')}: {detail.get('name', 'Unknown')}"]
    for label, key, limit in (
        ("Product", "product", 220),
        ("Date Added", "date_added", 80),
        ("Due Date", "due_date", 80),
        ("Ransomware", "ransomware", 40),
        ("Required Action", "required_action", ACTION_CHAR_LIMIT),
        ("CWEs", "cwes", 180),
        ("Notes", "notes", NOTES_CHAR_LIMIT),
        ("Description", "description", DESCRIPTION_CHAR_LIMIT),
    ):
        value = detail.get(key)
        if value:
            lines.append(f"- **{label}**: {limit_text(value, limit)}")
    return limit_text("\n".join(lines), DETAIL_CHAR_LIMIT)


def more_suffix(total: int, shown: int) -> str:
    omitted = total - shown
    if omitted <= 0:
        return ""
    return f" (+{omitted} more)"
