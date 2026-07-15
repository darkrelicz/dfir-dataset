import json
import re
from typing import Any


JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


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
