import argparse
import logging

from dataset_packaging.runner import run_packaging


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 dataset packaging")
    parser.add_argument("--config", default="configs/packaging.yaml")
    parser.add_argument("--quality-dir", default="data/quality/gemini_subset_1")
    parser.add_argument("--output-dir", default="data/packaged/gemini_subset_1")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    raise SystemExit(run_packaging(args))


if __name__ == "__main__":
    main()
