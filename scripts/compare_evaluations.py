import argparse
import logging

from evaluation.comparison import compare_evaluations


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two Phase 6 evaluation runs")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--tuned-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--minimum-overall-delta", type=float, default=0.0)
    parser.add_argument("--max-task-regression", type=float, default=0.05)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    raise SystemExit(compare_evaluations(args))


if __name__ == "__main__":
    main()
