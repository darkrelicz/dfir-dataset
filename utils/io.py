import json
import time
from logging import Logger
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


def load_json(path: Path, logger: Logger) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Could not parse JSON file: %s", path)
        return {}


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Missing required Phase 4 output: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def log_stage_complete(logger: Logger, stage: str, started_at: float, detail: str | None = None) -> None:
    elapsed = time.perf_counter() - started_at
    if detail:
        logger.info("%s in %.1fs (%s)", stage, elapsed, detail)
    else:
        logger.info("%s in %.1fs", stage, elapsed)

