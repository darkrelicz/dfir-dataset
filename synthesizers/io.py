import json
from pathlib import Path
from typing import Iterable

from collectors.schemas import RawDocument


def raw_jsonl_paths(raw_dir: Path) -> list[Path]:
    return sorted(path for path in raw_dir.glob("*/*.jsonl") if path.is_file())


def iter_raw_documents(raw_dir: Path) -> Iterable[tuple[Path, int, RawDocument]]:
    for path in raw_jsonl_paths(raw_dir):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                yield path, line_number, RawDocument.model_validate(json.loads(line))


def load_raw_documents(raw_dir: Path) -> list[RawDocument]:
    return [doc for _, _, doc in iter_raw_documents(raw_dir)]
