import argparse
import logging

from quality.runner import run_quality_filter


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 quality filtering")
    parser.add_argument(
        "--input",
        default="data/synthesized/gemini_subset_1/accepted.jsonl",
        help="Phase 3 accepted JSONL input",
    )
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--quality-config", default="configs/quality.yaml")
    parser.add_argument("--task-config", default="configs/task_categories.yaml")
    parser.add_argument("--output-dir", default="data/quality/gemini_subset_1")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing quality output files instead of replacing them",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Console logging level for quality-filter stages",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    raise SystemExit(run_quality_filter(args))


if __name__ == "__main__":
    main()
