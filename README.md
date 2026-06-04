# Shepherd DFIR Dataset

This repository contains the data collection, synthesis, and quality assurance pipeline for building a specialized fine-tuning dataset for the Shepherd DFIR AI assistant.

## Project Purpose

The goal is to build a **re-runnable dataset factory** that produces high-quality instruction-response pairs covering key digital forensics and incident response (DFIR) tasks. The resulting dataset will be used to fine-tune a model (e.g., GLM-4.7-Flash) for Shepherd's specialist agents.

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

### Validating the Taxonomy

The taxonomy is defined in `taxonomy/dfir_taxonomy.yaml`. To ensure it meets the schema requirements and distribution targets:

```bash
python taxonomy/validate_taxonomy.py
```

To see the MITRE ATT&CK tactic coverage of the example tasks:

```bash
python taxonomy/gap_analysis.py
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
- `taxonomy/`: Phase 1 task definitions (Source of Truth)
- `data/`: Output directory for generated artifacts (ignored by git)