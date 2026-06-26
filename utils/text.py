import hashlib
import re
from collections.abc import Hashable, Iterable
from typing import Any, TypeVar


WORD_RE = re.compile(r"\b\w+\b")
T = TypeVar("T", bound=Hashable)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def to_markdown(text: str) -> str:
    if not text:
        return ""
    return text.strip()


def as_list(
    value: Any,
    *,
    stringify: bool = False,
    drop_empty: bool = True,
) -> list[Any] | list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple | set):
        items = list(value)
    else:
        items = [value]

    if drop_empty:
        items = [item for item in items if item not in (None, "", [])]
    if stringify:
        return [str(item) for item in items]
    return items


def slugify(value: Any, fallback: str = "") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or fallback


def unique_preserve_order(values: Iterable[T], *, drop_empty: bool = True) -> list[T]:
    seen: set[T] = set()
    unique_values: list[T] = []
    for value in values:
        if drop_empty and value in (None, ""):
            continue
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def meets_order_threshold(value: str, minimum: str, order: list[str]) -> bool:
    min_index = order.index(minimum) if minimum in order else 0
    value_index = order.index(value) if value in order else -1
    return value_index >= min_index


def safe_filename(value: str, fallback: str = "prompt") -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return safe or fallback


def stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo
