import argparse
from pathlib import Path

from synthesizers.runner import print_validation, run_generation, write_prompt_render


def main():
    parser = argparse.ArgumentParser(description="Data synthesis")
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
    render.add_argument(
        "--write-prompt-files",
        action="store_true",
        help="Also write one Markdown file per rendered prompt for inspection",
    )

    run = subparsers.add_parser(
        "run",
        help="Generate instruction pairs with the configured Gemini model",
    )
    run.add_argument("--raw-dir", default="data/raw")
    run.add_argument("--synthesis-config", default="configs/synthesis.yaml")
    run.add_argument("--task-config", default="configs/task_categories.yaml")
    run.add_argument("--quality-config", default="configs/quality.yaml")
    run.add_argument("--output-dir", default="data/synthesized/gemini_run")
    run.add_argument("--mode", choices=["pilot", "full"], default="pilot")
    run.add_argument("--source")
    run.add_argument("--limit", type=int)
    run.add_argument("--env-file", default=".env")
    run.add_argument(
        "--max-rejection-rate",
        type=float,
        default=0.20,
        help=(
            "In full mode, stop generation when current-run rejected prompts "
            "reach this rate after --min-rejection-check attempts"
        ),
    )
    run.add_argument(
        "--min-rejection-check",
        type=int,
        default=20,
        help="In full mode, minimum attempted prompts before checking rejection rate",
    )
    run.add_argument(
        "--disable-rejection-circuit-breaker",
        action="store_true",
        help="Disable full-mode early stop based on current-run rejection rate",
    )
    run.add_argument(
        "--skip-present",
        action="store_true",
        help=(
            "Skip prompt IDs already present in accepted/rejected output "
            "with matching prompt hash and model"
        ),
    )

    args = parser.parse_args()
    if args.command == "validate-raw":
        raise SystemExit(print_validation(Path(args.raw_dir)))
    if args.command == "render-prompts":
        raise SystemExit(write_prompt_render(args))
    if args.command == "run":
        raise SystemExit(run_generation(args))


if __name__ == "__main__":
    main()
