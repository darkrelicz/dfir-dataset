<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">User Guide</h1>

Using this project mostly means running Python scripts from the repository root.
The scripts read YAML configuration from `configs/` and write versionable JSONL
and manifest artifacts under `data/`.

# Choose A Task

| I want to... | Run or Read |
|---|---|
| Install the project and see the commands | [Quick Start](quickstart.md) |
| Run the complete pipeline | [Running The Pipeline](running-the-pipeline.md) |
| Refresh one or all public sources | `python -m scripts.collect_all` |
| Validate or generate synthesis data | `python -m scripts.synthesize` |
| Filter candidate pairs | `python -m scripts.quality_filter` |
| Build train/validation/test files | `python -m scripts.package_dataset` |
| Train the GLM LoRA | `python -m scripts.finetune --config configs/<versioned_finetune_config>.yaml` |
| Evaluate or compare a model | `python -m scripts.run_evaluation` / `python -m scripts.compare_evaluations` |
| Understand source coverage | [Source Guide](source-guide.md) |
| Understand quality/package policy | [Quality And Packaging](quality-and-packaging.md) |
| Apply release gates | [Training And Release](training-and-release.md) |
| Hand the repository to a successor | [Handover Guide](handover.md) |

# Command Map

After `pip install -e .`, each module also has a console command.

| Phase | Module Command | Installed Command |
|---|---|---|
| 2. Collection | `python -m scripts.collect_all` | `dfir-collect` |
| 3. Synthesis | `python -m scripts.synthesize` | `dfir-synthesize` |
| 4. Quality | `python -m scripts.quality_filter` | `dfir-quality` |
| 5. Packaging | `python -m scripts.package_dataset` | `dfir-package` |
| 6. Training | `python -m scripts.finetune` | `dfir-train-lora` |
| 6. Evaluation | `python -m scripts.run_evaluation` | `dfir-evaluate` |
| 6. Comparison | `python -m scripts.compare_evaluations` | `dfir-compare-evals` |

Use `--help` before changing defaults. The documentation uses module commands
so it is always clear which source file runs.

Fine-tuning is the exception where the default is historical v1 state. Always
pass an explicit versioned config and use isolated output paths.

# Normal Operating Path

```text
collect_all -> synthesize -> quality_filter -> package_dataset
                                              |
                                              +-> finetune
                                              +-> run_evaluation -> compare_evaluations
```

Do not bypass a stage by feeding Phase 3 `accepted.jsonl` directly to packaging
or training. It is candidate data. The active package is built only from Phase
4 filtered rows; review and rejected rows remain excluded.

# Before You Run Anything

1. Work from the repository root with Python 3.11+.
2. Read the [Current Project State](../current-state/index.md); it identifies
   active paths and rejected artifacts.
3. Give every new run its own output directory unless intentionally resuming
   Phase 3 with `--skip-present`.
4. Inspect the generated manifest, including errors, warnings, and expected
   source coverage, before using output downstream. Collection process exit
   status alone is not currently a reliable success gate.
5. Never treat a completed training or evaluation process as a release by
   itself; Phase 6 has explicit termination, calibration, and regression gates.

# Credentials And Compute

Collection generally needs internet access. Gemini synthesis additionally
needs `GEMINI_API_KEY` in `.env` or the environment. Training requires the DGX
CUDA/Unsloth environment. Evaluation requires separate local OpenAI-compatible
target and judge endpoints. Collection, prompt rendering, raw validation,
quality filtering, and packaging do not need a model API.
