import json
from pathlib import Path
from typing import Any, Iterable

import yaml


def load_yaml(path: Path | str, default: Any = None) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return default if data is None else data


def write_json(path: Path | str, data: Any, indent: int = 2) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=True, indent=indent),
        encoding="utf-8",
    )


def write_jsonl(path: Path | str, rows: Iterable[dict]) -> int:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
            count += 1
    return count


def append_jsonl(path: Path | str, row: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")

