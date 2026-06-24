import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from collectors.schemas import RawDocument
from synthesizers.clients.base import ModelClient, ModelResponse
from synthesizers.clients.gemini import GeminiClient
from synthesizers.io import load_raw_documents, write_jsonl
from synthesizers.prompt_builder import PromptBuilder
from synthesizers.sampler import sample_pilot_documents
from synthesizers.schemas import GenerationManifest, PromptRecord
from synthesizers.validators import (valid_taxonomy_refs_from_quality_config,
                                     validate_generated_pairs,
                                     validate_raw_corpus)


def safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return safe or "prompt"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")


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


def select_documents(args: argparse.Namespace) -> list[RawDocument]:
    docs = load_raw_documents(Path(args.raw_dir))

    if args.source:
        docs = [doc for doc in docs if doc.source == args.source]

    if args.mode == "pilot":
        docs = sample_pilot_documents(docs)
    else:
        docs = sorted(docs, key=lambda doc: (doc.source, doc.doc_id))
        if args.limit is not None:
            docs = docs[: args.limit]

    max_prompts = getattr(args, "max_prompts", None)
    if max_prompts is not None:
        docs = docs[:max_prompts]

    return docs


def build_prompt_record_models(
    args: argparse.Namespace,
    synthesis_config: dict | None = None,
    task_config: dict | None = None,
) -> tuple[list[RawDocument], list[PromptRecord]]:
    synthesis_config = synthesis_config or load_yaml(Path(args.synthesis_config))
    task_config = task_config or load_yaml(Path(args.task_config))
    docs = select_documents(args)
    builder = PromptBuilder(synthesis_config, task_config)
    return docs, [builder.build(doc) for doc in docs]


def build_prompt_records(args: argparse.Namespace) -> list[dict]:
    _, records = build_prompt_record_models(args)
    return [record.model_dump(mode="json") for record in records]


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


def client_from_config(synthesis_config: dict) -> ModelClient:
    model_config = synthesis_config.get("model", {})
    provider = str(model_config.get("provider", "google_genai"))
    if provider != "google_genai":
        raise ValueError(f"Unsupported model provider: {provider}")
    return GeminiClient(model_config, synthesis_config.get("generation", {}))


def completed_prompt_ids(output_dir: Path) -> set[str]:
    completed: set[str] = set()
    for name in ("accepted.jsonl", "rejected.jsonl", "raw_outputs.jsonl"):
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
                if prompt_id:
                    completed.add(str(prompt_id))
    return completed


def generate_with_retries(
    client: ModelClient,
    prompt_record: PromptRecord,
    max_retries: int,
) -> tuple[ModelResponse | None, int, str | None]:
    attempts = 0
    for attempt in range(1, max_retries + 2):
        attempts = attempt
        try:
            return client.generate(prompt_record), attempts, None
        except Exception as exc:
            if attempt > max_retries:
                return None, attempts, str(exc)
            time.sleep(min(2 ** (attempt - 1), 30))
    return None, attempts, "Generation failed without an exception"


def apply_run_overrides(args: argparse.Namespace, synthesis_config: dict) -> None:
    model_config = synthesis_config.setdefault("model", {})
    if args.model:
        model_config["primary"] = args.model
    if args.thinking_level:
        model_config["thinking_level"] = args.thinking_level


def rejection_circuit_breaker_reason(
    args: argparse.Namespace,
    attempted_prompts: int,
    rejected_prompts: int,
) -> str | None:
    if args.disable_rejection_circuit_breaker:
        return None
    if attempted_prompts < args.min_rejection_check:
        return None

    rejection_rate = rejected_prompts / attempted_prompts
    if rejection_rate < args.max_rejection_rate:
        return None

    return (
        "Rejection circuit breaker tripped: "
        f"{rejected_prompts}/{attempted_prompts} attempted prompt(s) rejected "
        f"({rejection_rate:.1%}) at threshold {args.max_rejection_rate:.1%}"
    )


def validate_rejection_circuit_breaker_args(args: argparse.Namespace) -> str | None:
    if args.min_rejection_check < 1:
        return "--min-rejection-check must be at least 1"
    if not 0 <= args.max_rejection_rate <= 1:
        return "--max-rejection-rate must be between 0 and 1"
    return None


def run_generation(args: argparse.Namespace) -> int:
    console = Console()
    load_env_file(Path(args.env_file))

    circuit_breaker_arg_error = validate_rejection_circuit_breaker_args(args)
    if circuit_breaker_arg_error:
        console.print(f"[red]{circuit_breaker_arg_error}[/red]")
        return 1

    raw_validation = validate_raw_corpus(Path(args.raw_dir))
    if not raw_validation.ok:
        console.print("[red]Raw corpus validation failed; refusing generation.[/red]")
        print_validation(Path(args.raw_dir))
        return 1

    synthesis_config = load_yaml(Path(args.synthesis_config))
    task_config = load_yaml(Path(args.task_config))
    quality_config = load_yaml(Path(args.quality_config))
    apply_run_overrides(args, synthesis_config)

    api_key_env = str(
        synthesis_config.get("model", {}).get("api_key_env", "GEMINI_API_KEY")
    )
    if not os.environ.get(api_key_env):
        console.print(f"[red]Missing {api_key_env}; add it to {args.env_file}.[/red]")
        return 1

    docs, prompt_records = build_prompt_record_models(
        args,
        synthesis_config=synthesis_config,
        task_config=task_config,
    )
    docs_by_id = {doc.doc_id: doc for doc in docs}

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        output_dir / "prompts.jsonl",
        [record.model_dump(mode="json") for record in prompt_records],
    )

    already_completed = completed_prompt_ids(output_dir) if args.resume else set()
    prompt_records = [
        record for record in prompt_records if record.prompt_id not in already_completed
    ]

    model_name = str(synthesis_config["model"]["primary"])
    client = client_from_config(synthesis_config)
    valid_taxonomy_refs = valid_taxonomy_refs_from_quality_config(quality_config)
    max_retries = int(synthesis_config.get("generation", {}).get("max_retries", 2))
    generated_at = datetime.now(timezone.utc).isoformat()

    attempted_prompts = 0
    accepted_prompt_count = 0
    api_error_count = 0
    validation_rejected_count = 0
    accepted_pairs = 0
    rejected_prompts = 0
    raw_outputs = 0
    stopped_early = False
    stop_reason: str | None = None

    console.print(
        f"Generating {len(prompt_records)} prompt(s) with {model_name}; "
        f"resume skipped {len(already_completed)}."
    )

    for index, prompt_record in enumerate(prompt_records, 1):
        source_doc = docs_by_id[prompt_record.source_doc_id]
        attempted_prompts += 1
        response, attempts, error = generate_with_retries(
            client,
            prompt_record,
            max_retries,
        )

        if response is None:
            api_error_count += 1
            rejected_prompts += 1
            append_jsonl(
                output_dir / "rejected.jsonl",
                {
                    "prompt_id": prompt_record.prompt_id,
                    "source_doc_id": prompt_record.source_doc_id,
                    "source": prompt_record.source,
                    "status": "api_error",
                    "attempts": attempts,
                    "error": error,
                    "generated_at": generated_at,
                },
            )
            console.print(f"[red]{index}/{len(prompt_records)} rejected API error[/red]")
        else:
            raw_outputs += 1
            append_jsonl(
                output_dir / "raw_outputs.jsonl",
                {
                    "prompt_id": prompt_record.prompt_id,
                    "source_doc_id": prompt_record.source_doc_id,
                    "source": prompt_record.source,
                    "model": response.model,
                    "attempts": attempts,
                    "output_text": response.text,
                    "metadata": response.metadata,
                    "generated_at": generated_at,
                },
            )

            validation = validate_generated_pairs(
                response.text,
                source_doc,
                prompt_record,
                valid_taxonomy_refs,
            )
            if validation.ok:
                accepted_prompt_count += 1
                for pair_index, pair in enumerate(validation.pairs):
                    row = pair.model_dump(mode="json")
                    row.update(
                        {
                            "prompt_id": prompt_record.prompt_id,
                            "pair_index": pair_index,
                            "model": response.model,
                            "generated_at": generated_at,
                        }
                    )
                    append_jsonl(output_dir / "accepted.jsonl", row)
                    accepted_pairs += 1
                console.print(
                    f"[green]{index}/{len(prompt_records)} accepted "
                    f"{len(validation.pairs)} pair(s)[/green]"
                )
            else:
                validation_rejected_count += 1
                rejected_prompts += 1
                append_jsonl(
                    output_dir / "rejected.jsonl",
                    {
                        "prompt_id": prompt_record.prompt_id,
                        "source_doc_id": prompt_record.source_doc_id,
                        "source": prompt_record.source,
                        "model": response.model,
                        "status": "validation_failed",
                        "issues": [
                            issue.model_dump(mode="json")
                            for issue in validation.issues
                        ],
                        "raw_output": response.text,
                        "metadata": response.metadata,
                        "attempts": attempts,
                        "generated_at": generated_at,
                    },
                )
                console.print(
                    f"[yellow]{index}/{len(prompt_records)} rejected validation "
                    f"({len(validation.issues)} issue(s))[/yellow]"
                )

        stop_reason = rejection_circuit_breaker_reason(
            args,
            attempted_prompts,
            rejected_prompts,
        )
        if stop_reason:
            stopped_early = True
            console.print(f"[red]{stop_reason}[/red]")
            break

        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)

    manifest = GenerationManifest(
        run_id=f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        mode=args.mode,
        model=model_name,
        created_at=datetime.now(timezone.utc),
        source_doc_count=len(docs),
        prompt_count=len(docs),
        output_dir=str(output_dir),
        config_path=args.synthesis_config,
        notes=[
            "Gemini API generation run.",
            f"Attempted prompts this run: {attempted_prompts}",
            f"Accepted prompts this run: {accepted_prompt_count}",
            f"API error prompts this run: {api_error_count}",
            f"Validation-rejected prompts this run: {validation_rejected_count}",
            f"Raw outputs written: {raw_outputs}",
            f"Accepted pairs written: {accepted_pairs}",
            f"Rejected prompts written: {rejected_prompts}",
            f"Resume skipped prompts: {len(already_completed)}",
            (
                "Rejection circuit breaker disabled."
                if args.disable_rejection_circuit_breaker
                else (
                    "Rejection circuit breaker: "
                    f"threshold={args.max_rejection_rate:.1%}, "
                    f"min_check={args.min_rejection_check}"
                )
            ),
            f"Stopped early: {stopped_early}",
            f"Stop reason: {stop_reason or ''}",
        ],
    )
    (output_dir / "generation_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    console.print(f"Wrote accepted pairs to {output_dir / 'accepted.jsonl'}")
    console.print(f"Wrote rejected prompts to {output_dir / 'rejected.jsonl'}")
    console.print(f"Wrote raw outputs to {output_dir / 'raw_outputs.jsonl'}")
    return 2 if stopped_early else 0


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

    run = subparsers.add_parser(
        "run",
        help="Generate instruction pairs with the configured model provider",
    )
    run.add_argument("--raw-dir", default="data/raw")
    run.add_argument("--synthesis-config", default="configs/synthesis.yaml")
    run.add_argument("--task-config", default="configs/task_categories.yaml")
    run.add_argument("--quality-config", default="configs/quality.yaml")
    run.add_argument("--output-dir", default="data/synthesized/gemini_run")
    run.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    run.add_argument("--source")
    run.add_argument("--limit", type=int)
    run.add_argument("--max-prompts", type=int)
    run.add_argument("--env-file", default=".env")
    run.add_argument("--model")
    run.add_argument("--thinking-level", choices=["low", "medium", "high"])
    run.add_argument("--sleep-seconds", type=float, default=0.0)
    run.add_argument(
        "--max-rejection-rate",
        type=float,
        default=0.20,
        help=(
            "Stop generation when current-run rejected prompts reach this rate "
            "after --min-rejection-check attempts"
        ),
    )
    run.add_argument(
        "--min-rejection-check",
        type=int,
        default=20,
        help="Minimum current-run attempted prompts before checking rejection rate",
    )
    run.add_argument(
        "--disable-rejection-circuit-breaker",
        action="store_true",
        help="Disable early stop based on current-run rejection rate",
    )
    run.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Do not skip prompt IDs already present in output JSONL files",
    )
    run.set_defaults(resume=True)

    args = parser.parse_args()
    if args.command == "validate-raw":
        raise SystemExit(print_validation(Path(args.raw_dir)))
    if args.command == "render-prompts":
        raise SystemExit(write_prompt_render(args))
    if args.command == "run":
        raise SystemExit(run_generation(args))


if __name__ == "__main__":
    main()
