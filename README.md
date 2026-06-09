# Shepherd DFIR Dataset

This repository contains the data collection, synthesis, and quality assurance pipeline for building a specialized fine-tuning dataset for the Shepherd DFIR AI assistant.

## Project Purpose

The goal is to build a **re-runnable dataset factory** that produces high-quality instruction-response pairs covering key digital forensics and incident response (DFIR) tasks. The resulting dataset will be used to fine-tune a model (e.g., GLM-4.7-Flash) for Shepherd's specialist agents.

We are currently in **Phase 2: Collection Pipeline**. The source collection pipeline is fully implemented. You can now ingest DFIR datasets.

See `docs/ARCHITECTURE.md` for design decisions.

## Quick Start

### Setup

```bash
# Set up a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package in development mode
pip install -e ".[dev]"
```


### Collection Instructions
```bash
# Run all collectors
python -m scripts.collect_all

# Run a single collector
python -m scripts.collect_all --source mitre_attack

# Validate collected data
python -m scripts.collect_all --dry-run
```

### Running Tests

```bash
pytest tests/
```

## Directory Structure

- `collectors/`: Phase 2 source collection scripts
- `synthesizers/`: Phase 3 instruction pair generation
- `quality/`: Phase 4 automated quality scoring
- `packaging/`: Phase 5 dataset export
- `evaluation/`: Phase 6 benchmarking
- `docs/`: Documentation including TAXONOMY.md
- `configs/`: Pipeline configuration including taxonomy IDs
- `data/`: Output directory for generated artifacts (ignored by git)