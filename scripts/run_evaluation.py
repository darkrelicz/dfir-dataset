import argparse
import logging
import sys

from evaluation.runner import run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 6 benchmark evaluation")
    parser.add_argument("--config", default="configs/evaluation.yaml")
    parser.add_argument("--cases")
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id")
    parser.add_argument(
        "--mode",
        choices=["openai_compatible", "prediction_file", "predictions", "replay"],
    )
    parser.add_argument("--predictions")
    parser.add_argument("--model")
    parser.add_argument("--model-label")
    parser.add_argument(
        "--evaluator",
        choices=["statistical", "llm_judge", "both"],
        help="Override scoring.evaluator; statistical remains the default.",
    )
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    try:
        raise SystemExit(run_evaluation(args))
    except (FileNotFoundError, KeyError, ValueError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
