import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from synthesizers.io import load_raw_documents, write_jsonl
from synthesizers.prompt_builder import PromptBuilder
from synthesizers.sampler import sample_pilot_documents
from synthesizers.schemas import GenerationManifest
from synthesizers.validators import validate_raw_corpus


def safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return safe or "prompt"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def print_validation(raw_dir: Path) -> int:
    console = Console()
    result = validate_raw_corpus(raw_dir)

    table = Table(title="Raw Corpus Validation")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Files", str(result.file_count))
    table.add_row("Documents", str(result.document_count))
    table.add_row("Unique doc IDs", str(result.unique_doc_ids))
    table.add_row("Issues", str(len(result.issues)))
    console.print(table)

    source_table = Table(title="Source Counts")
    source_table.add_column("Source")
    source_table.add_column("Documents", justify="right")
    for source, count in result.source_counts.items():
        source_table.add_row(source, str(count))
    console.print(source_table)

    if result.issues:
        issue_table = Table(title="Validation Issues")
        issue_table.add_column("Path")
        issue_table.add_column("Line", justify="right")
        issue_table.add_column("Message")
        for issue in result.issues[:25]:
            issue_table.add_row(issue.path, str(issue.line or ""), issue.message)
        console.print(issue_table)

    return 0 if result.ok else 1


def build_prompt_records(args: argparse.Namespace) -> list[dict]:
    synthesis_config = load_yaml(Path(args.synthesis_config))
    task_config = load_yaml(Path(args.task_config))
    docs = load_raw_documents(Path(args.raw_dir))

    if args.source:
        docs = [doc for doc in docs if doc.source == args.source]

    if args.mode == "pilot":
        docs = sample_pilot_documents(docs)
    else:
        docs = sorted(docs, key=lambda doc: (doc.source, doc.doc_id))
        if args.limit is not None:
            docs = docs[: args.limit]

    builder = PromptBuilder(synthesis_config, task_config)
    return [builder.build(doc).model_dump(mode="json") for doc in docs]


def write_prompt_render(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    records = build_prompt_records(args)

    prompt_jsonl = output_dir / "prompts.jsonl"
    write_jsonl(prompt_jsonl, records)

    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        prompt_path = prompts_dir / f"{safe_filename(record['prompt_id'])}.md"
        prompt_path.write_text(record["prompt"], encoding="utf-8")

    manifest = GenerationManifest(
        run_id=f"dry-run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        mode=args.mode if args.mode in {"pilot", "full"} else "dry_run",
        model="none",
        created_at=datetime.now(timezone.utc),
        source_doc_count=len(records),
        prompt_count=len(records),
        output_dir=str(output_dir),
        config_path=args.synthesis_config,
        notes=["No model API calls were made."],
    )
    (output_dir / "generation_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    console = Console()
    console.print(f"Wrote {len(records)} prompt records to {prompt_jsonl}")
    console.print(f"Wrote individual prompt markdown files to {prompts_dir}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Data synthesizing")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-raw", help="Validate raw JSONL corpus")
    validate.add_argument("--raw-dir", default="data/raw")

    render = subparsers.add_parser(
        "render-prompts",
        help="Render synthesis prompts without model API calls",
    )
    render.add_argument("--raw-dir", default="data/raw")
    render.add_argument("--synthesis-config", default="configs/synthesis.yaml")
    render.add_argument("--task-config", default="configs/task_categories.yaml")
    render.add_argument("--output-dir", default="data/synthesized/dry_run")
    render.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    render.add_argument("--source")
    render.add_argument("--limit", type=int)

    args = parser.parse_args()
    if args.command == "validate-raw":
        raise SystemExit(print_validation(Path(args.raw_dir)))
    if args.command == "render-prompts":
        raise SystemExit(write_prompt_render(args))


if __name__ == "__main__":
    main()
