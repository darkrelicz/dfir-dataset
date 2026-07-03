import json
import re
from dataclasses import dataclass
from typing import Any

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
HASH_RE = re.compile(r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b")
IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
DOMAIN_RE = re.compile(
    r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"(?:com|net|org|io|gov|edu|mil|co|uk|ru|cn|de|jp|br|au|ca|fr|nl|"
    r"info|biz|dev|cloud|app|tech|site|online)\b"
)
WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\[^\s\"'<>|]+")
REGISTRY_PATH_RE = re.compile(
    r"(?i)\b(?:HKLM|HKCU|HKCR|HKU|HKCC|HKEY_LOCAL_MACHINE|"
    r"HKEY_CURRENT_USER|HKEY_CLASSES_ROOT|HKEY_USERS|"
    r"HKEY_CURRENT_CONFIG)\\[A-Za-z0-9_\\/*.$%{}-]+"
)
UNIX_PATH_RE = re.compile(
    r"(?<![\w])/(?:etc|var|tmp|home|usr|bin|sbin|opt|root|Users|"
    r"Library|System|Applications|private|Volumes)/[^\s\"'<>]+"
)
EVENT_ID_RE = re.compile(r"\b(?:Event\s+ID|EID)\s*[:#-]?\s*(\d{3,5})\b", re.IGNORECASE)


@dataclass(frozen=True)
class IndicatorOptions:
    include_paths: bool = True
    include_event_ids: bool = True


BASIC_INDICATOR_OPTIONS = IndicatorOptions(include_paths=False, include_event_ids=False)
FULL_INDICATOR_OPTIONS = IndicatorOptions()


def extract_concrete_indicators(
    text: str,
    options: IndicatorOptions = FULL_INDICATOR_OPTIONS,
) -> set[str]:
    indicators: set[str] = set()
    indicators.update(value.upper() for value in CVE_RE.findall(text))
    indicators.update(value.lower() for value in HASH_RE.findall(text))
    indicators.update(IPV4_RE.findall(text))
    indicators.update(value.lower() for value in DOMAIN_RE.findall(text))
    if options.include_paths:
        indicators.update(normalize_indicator(value) for value in WINDOWS_PATH_RE.findall(text))
        indicators.update(normalize_indicator(value) for value in REGISTRY_PATH_RE.findall(text))
        indicators.update(normalize_indicator(value) for value in UNIX_PATH_RE.findall(text))
    if options.include_event_ids:
        indicators.update(f"event_id:{value}" for value in EVENT_ID_RE.findall(text))
    return {value for value in indicators if value}


def invented_indicators(
    output_text: str,
    source_text: str,
    options: IndicatorOptions = FULL_INDICATOR_OPTIONS,
) -> list[str]:
    source_indicators = extract_concrete_indicators(source_text, options)
    output_indicators = extract_concrete_indicators(output_text, options)
    return sorted(output_indicators - source_indicators)


def normalize_indicator(value: str) -> str:
    return value.strip(".,;:()[]{}'\"`").rstrip("\\/").lower()


def source_document_text(
    title: str,
    source_url: str,
    content_markdown: str,
    metadata: dict[str, Any],
) -> str:
    return "\n".join(
        [
            title,
            source_url,
            content_markdown,
            json.dumps(metadata, sort_keys=True),
        ]
    )
