import argparse
import logging

from dataset_packaging.runner import run_packaging


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 dataset packaging")
    parser.add_argument("--config", default="configs/packaging.yaml")
    parser.add_argument(
        "--quality-dir",
        default=None,
        help="Override Phase 4 quality output directory from packaging config",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override packaged dataset output directory from packaging config",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    raise SystemExit(run_packaging(args))


if __name__ == "__main__":
    main()
