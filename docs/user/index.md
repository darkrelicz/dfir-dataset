<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">User Guide</h1>

This section details how to use this project, from collecting raw data sources to the final finetuned model. It consist of helpful links and commands to execute the dataset pipeline. 

To find out more on the implementation and maintenance details, please refer to [**Developer Guide**](../developer/index.md).

# Quick Start

| I want to... | Run or Read |
|---|---|
| Run the complete pipeline | [Running The Pipeline](running-the-pipeline.md) |
| Collect or refresh data from raw sources | `python -m scripts.collect_all` |
| Generate training data | `python -m scripts.synthesize` |
| Filter candidate pairs | `python -m scripts.quality_filter` |
| Build train/validation/test files | `python -m scripts.package_dataset` |
| Finetune the GLM model | `python -m scripts.finetune --config configs/<versioned_finetune_config>.yaml` |
| Evaluate a model | `python -m scripts.run_evaluation` |
| Compare a model | `python -m scripts.compare_evaluations` |
| View the current sources | [Source Overview](source-overview.md) |

# Normal Operating Path

```text
collect_all -> synthesize -> quality_filter -> package_dataset
                                              |
                                              +-> finetune
                                              +-> run_evaluation -> compare_evaluations
```

Do not feed `accepted.jsonl` from the `synthesize` stage directly to packaging or training. It is candidate data. The active package is built only from filtered rows in `quality_filter` stage; review and rejected rows remain excluded.


# Credentials And Compute

* Collection generally needs internet access
* Gemini synthesis additionally needs `GEMINI_API_KEY` in `.env` or the environment. Do not commit this.
* Training requires the DGX CUDA/Unsloth environment
* Evaluation requires separate local OpenAI-compatible target and judge endpoints
* Collection, prompt rendering, raw validation, quality filtering, and packaging do not need a model API.
