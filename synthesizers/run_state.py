import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from synthesizers.schemas import PromptRecord


TERMINAL_PROMPT_FILES = ("accepted.jsonl", "rejected.jsonl")


def build_run_id(prefix: str, timestamp: datetime) -> str:
    return f"{prefix}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}"


def prompt_hash(prompt_record: PromptRecord) -> str:
    return hashlib.sha256(prompt_record.prompt.encode("utf-8")).hexdigest()


def prompt_hashes(prompt_records: Iterable[PromptRecord]) -> dict[str, str]:
    return {record.prompt_id: prompt_hash(record) for record in prompt_records}


def prompt_record_row(prompt_record: PromptRecord) -> dict:
    row = prompt_record.model_dump(mode="json")
    row["prompt_hash"] = prompt_hash(prompt_record)
    return row


def prompt_run_fields(prompt_record: PromptRecord, run_id: str) -> dict:
    return {
        "run_id": run_id,
        "prompt_id": prompt_record.prompt_id,
        "prompt_hash": prompt_hash(prompt_record),
        "source_doc_id": prompt_record.source_doc_id,
        "source": prompt_record.source,
    }


def completed_prompt_ids(
    output_dir: Path,
    expected_prompt_hashes: dict[str, str],
    model_name: str,
) -> set[str]:
    completed: set[str] = set()
    for name in TERMINAL_PROMPT_FILES:
        path = output_dir / name
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue

                prompt_id = row.get("prompt_id")
                if not prompt_id:
                    continue
                prompt_id = str(prompt_id)
                if row.get("prompt_hash") != expected_prompt_hashes.get(prompt_id):
                    continue
                if row.get("model") != model_name:
                    continue
                completed.add(prompt_id)
    return completed
