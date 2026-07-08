<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

# DFIR Dataset

DFIR Dataset is a re-runnable dataset factory that produces quality DFIR training data for finetuning local LLMs. It is designed with expansionability in mind. To add a new data source, only one collector script and one line in the collector orchestrating script is needed. The rest of the pipeline can ran without modification.

* If you are interested in using this project, head over to the [_Quick Start section of the_ **User Guide**](user/quickstart.md).
* If you are interested about developing this project, the [**Developer Guide**](developer/index.md) is a good place to start.

## Current Snapshot

As of 2026-07-07, the active handoff path is:

1. Raw source collection under `../data/raw/`.
2. Reduced-subset Gemini synthesis under `../data/synthesized/gemini_subset_1/`.
3. Phase 4 quality filtering under `../data/quality/gemini_subset_1/`.
4. Phase 5 local packaging under `../data/packaged/gemini_subset_1/`.
5. Phase 6 baseline evaluation and LoRA SFT are the next project tasks.

The current packaged training inputs are:

* `../data/packaged/gemini_subset_1/train.jsonl`
* `../data/packaged/gemini_subset_1/validation.jsonl`
* `../data/packaged/gemini_subset_1/test.jsonl`

Refer to [**Current State**](current-state/index.md) to find out more about the current project state.