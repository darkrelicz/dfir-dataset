import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from synthesizers.clients.base import ModelClient, ModelResponse
from synthesizers.planner import build_prompt_plan
from synthesizers.run_state import (
    build_run_id,
    completed_prompt_ids,
    prompt_hashes,
    prompt_record_row,
    prompt_run_fields,
)
from synthesizers.schemas import GenerationManifest, PromptRecord
from synthesizers.validators import (
    valid_taxonomy_refs_from_quality_config,
    validate_generated_pairs,
    validate_raw_corpus,
)
from utils.io import append_jsonl, load_yaml, write_json, write_jsonl
from utils.text import safe_filename


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


def print_validation(raw_dir: Path) -> int:
    console = Console()
    result = validate_raw_corpus(raw_dir)

    console.print("\nRaw Corpus Validation")
    console.print(f"Files: {result.file_count}")
    console.print(f"Documents: {result.document_count}")
    console.print(f"Unique doc IDs: {result.unique_doc_ids}")
    console.print(f"Issues: {len(result.issues)}")

    console.print("\nSource Counts")
    for source, count in result.source_counts.items():
        console.print(f"{source}: {count}")

    if result.issues:
        console.print("Validation Issues")
        for issue in result.issues[:25]:
            line = f":{issue.line}" if issue.line else ""
            console.print(f"{issue.path}{line}: {issue.message}")

    return 0 if result.ok else 1


def write_prompt_render(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    synthesis_config = load_yaml(Path(args.synthesis_config))
    task_config = load_yaml(Path(args.task_config))
    plan = build_prompt_plan(
        Path(args.raw_dir),
        synthesis_config,
        task_config,
        args.mode,
        limit=args.limit,
    )
    records = [prompt_record_row(record) for record in plan.prompt_records]
    created_at = datetime.now(timezone.utc)

    prompt_jsonl = output_dir / "prompts.jsonl"
    write_jsonl(prompt_jsonl, records)

    write_prompt_files = getattr(args, "write_prompt_files", False)
    if write_prompt_files:
        prompts_dir = output_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        for record in records:
            prompt_path = prompts_dir / f"{safe_filename(record['prompt_id'])}.md"
            prompt_path.write_text(record["prompt"], encoding="utf-8")

    manifest = GenerationManifest(
        run_id=build_run_id("dry-run", created_at),
        mode="dry_run",
        model="none",
        created_at=created_at,
        source_doc_count=len(records),
        prompt_count=len(records),
        output_dir=str(output_dir),
        config_path=args.synthesis_config,
        notes=["No model API calls were made."],
    )
    write_json(
        output_dir / "generation_manifest.json",
        manifest.model_dump(mode="json"),
    )

    console = Console()
    console.print(f"Wrote {len(records)} prompt records to {prompt_jsonl}")
    if write_prompt_files:
        console.print(f"Wrote individual prompt markdown files to {prompts_dir}")
    return 0


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


def rejection_circuit_breaker_reason(
    args: argparse.Namespace,
    attempted_prompts: int,
    rejected_prompts: int,
) -> str | None:
    if args.mode != "full":
        return None
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
    if args.mode != "full":
        return None
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

    api_key_env = str(
        synthesis_config.get("model", {}).get("api_key_env", "GEMINI_API_KEY")
    )
    if not os.environ.get(api_key_env):
        console.print(f"[red]Missing {api_key_env}; add it to {args.env_file}.[/red]")
        return 1

    plan = build_prompt_plan(
        Path(args.raw_dir),
        synthesis_config,
        task_config,
        args.mode,
        limit=args.limit,
    )
    docs_by_id = {doc.doc_id: doc for doc in plan.docs}
    expected_prompt_hashes = prompt_hashes(plan.prompt_records)
    model_name = str(synthesis_config["model"]["primary"])
    run_started_at = datetime.now(timezone.utc)
    run_id = build_run_id("run", run_started_at)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        output_dir / "prompts.jsonl",
        [prompt_record_row(record) for record in plan.prompt_records],
    )

    already_completed = (
        completed_prompt_ids(output_dir, expected_prompt_hashes, model_name)
        if args.skip_present
        else set()
    )
    prompt_records = [
        record
        for record in plan.prompt_records
        if record.prompt_id not in already_completed
    ]

    from synthesizers.clients.gemini import GeminiClient

    client = GeminiClient(
        synthesis_config["model"],
        synthesis_config.get("generation", {}),
    )
    valid_taxonomy_refs = valid_taxonomy_refs_from_quality_config(quality_config)
    max_retries = int(synthesis_config.get("generation", {}).get("max_retries", 2))
    generated_at = run_started_at.isoformat()

    attempted_prompts = 0
    accepted_pairs = 0
    rejected_prompts = 0
    stopped_early = False
    stop_reason: str | None = None

    console.print(
        f"Generating {len(prompt_records)} prompt(s) with {model_name}; "
        f"present prompts skipped {len(already_completed)}."
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
            rejected_prompts += 1
            append_jsonl(
                output_dir / "rejected.jsonl",
                {
                    **prompt_run_fields(prompt_record, run_id),
                    "model": model_name,
                    "status": "api_error",
                    "attempts": attempts,
                    "error": error,
                    "generated_at": generated_at,
                },
            )
            console.print(
                f"[red]{index}/{len(prompt_records)} rejected API error[/red]"
            )
        else:
            append_jsonl(
                output_dir / "raw_outputs.jsonl",
                {
                    **prompt_run_fields(prompt_record, run_id),
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
                for pair_index, pair in enumerate(validation.pairs):
                    row = pair.model_dump(mode="json")
                    row.update(
                        {
                            **prompt_run_fields(prompt_record, run_id),
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
                rejected_prompts += 1
                append_jsonl(
                    output_dir / "rejected.jsonl",
                    {
                        **prompt_run_fields(prompt_record, run_id),
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

    manifest_notes = [
        "Gemini API generation run.",
        f"Attempted prompts this run: {attempted_prompts}",
        f"Accepted pairs written: {accepted_pairs}",
        f"Rejected prompts written: {rejected_prompts}",
        f"Present prompts skipped: {len(already_completed)}",
        (
            "Rejection circuit breaker inactive in pilot mode."
            if args.mode != "full"
            else "Rejection circuit breaker disabled."
            if args.disable_rejection_circuit_breaker
            else (
                "Rejection circuit breaker: "
                f"threshold={args.max_rejection_rate:.1%}, "
                f"min_check={args.min_rejection_check}"
            )
        ),
    ]
    if stopped_early:
        manifest_notes.append(f"Stopped early: {stop_reason}")

    manifest = GenerationManifest(
        run_id=run_id,
        mode=args.mode,
        model=model_name,
        created_at=run_started_at,
        source_doc_count=len(plan.docs),
        prompt_count=len(plan.prompt_records),
        output_dir=str(output_dir),
        config_path=args.synthesis_config,
        notes=manifest_notes,
    )
    write_json(
        output_dir / "generation_manifest.json",
        manifest.model_dump(mode="json"),
    )

    console.print(f"Wrote accepted pairs to {output_dir / 'accepted.jsonl'}")
    console.print(f"Wrote rejected prompts to {output_dir / 'rejected.jsonl'}")
    console.print(f"Wrote raw outputs to {output_dir / 'raw_outputs.jsonl'}")
    return 2 if stopped_early else 0
