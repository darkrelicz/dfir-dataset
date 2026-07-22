import json
import re
from typing import Any

from evaluation.schemas import BenchmarkCase


JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def structured_output_instruction(
    case: BenchmarkCase,
    generation_config: dict[str, Any],
) -> str | None:
    """Return the target response contract for objective benchmark tasks."""

    config = generation_config.get("structured_outputs", {})
    if not bool(config.get("enabled", True)):
        return None
    output_format = case.target_output.format
    if output_format == "techniques_json":
        return (
            "Output format: Return one JSON object with `techniques` as an array of "
            "ATT&CK or ATLAS IDs and `answer` as your concise evidence-based explanation."
        )
    if output_format == "iocs_json":
        return (
            "Output format: Return one JSON object with `iocs` as an array of objects "
            "having `type` and `value`, plus `answer` as a concise explanation. Use "
            "normalized, refanged indicator values."
        )
    if output_format == "ranked_actions_json":
        return (
            "Output format: Return one JSON object with `ranked_actions` as an ordered "
            "array of action IDs and `answer` as your concise ranking rationale."
        )
    return None


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from a model response, tolerating a code fence."""

    candidates = [text.strip()]
    candidates.extend(match.group(1).strip() for match in JSON_FENCE_RE.finditer(text))
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            value = _raw_decode_first_object(candidate, decoder)
        if isinstance(value, dict):
            return value
    return None


def _raw_decode_first_object(
    text: str,
    decoder: json.JSONDecoder,
) -> Any:
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return value
    return None
