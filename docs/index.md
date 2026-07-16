<frontmatter>
  pageNav: default
  pageNavTitle: "On This Page"
</frontmatter>

<h1 class="no-index">DFIR Dataset</h1>

DFIR Dataset is a re-runnable dataset factory for producing grounded DFIR
instruction data and evaluating a locally fine-tuned model. It is designed to
be extended with additional source collectors while preserving shared
collection, synthesis, quality, packaging, training, and evaluation stages.

* To run the Python scripts, start with the [**User Guide**](user/index.md).
* To change a pipeline phase, start with the [**Phase Maintenance Guide**](developer/phase-maintenance.md).
* For the complete handover snapshot, read [**Current State**](current-state/index.md).

# Current Snapshot

As of 2026-07-16, the active handoff path is:

1. Raw source collection under `../data/raw/`.
2. Reduced-subset Gemini synthesis under `../data/synthesized/gemini_subset_1/`.
3. Phase 4 quality filtering under `../data/quality/gemini_subset_1/`.
4. A GLM-specific Phase 5 view under `../data/packaged/glm47_dfir_v2/`.
5. V2 LoRA retraining and a mandatory direct-adapter EOS smoke gate.
6. Local LLM-judge calibration, calibrated base/v2 tuned evaluation, and
   post-training comparison.

The current packaged training inputs are:

* `../data/packaged/glm47_dfir_v2/train.jsonl`
* `../data/packaged/glm47_dfir_v2/validation.jsonl`
* `../data/packaged/glm47_dfir_v2/test.jsonl`

The first training run, `train-20260714T025314Z`, exported a LoRA adapter and a
Q4_K_M GGUF but is rejected because it loops and does not emit EOS. V2 training
is prepared but not complete. The 68-case base-model evaluation under
`../data/evaluation/glm47-flash-base/` is complete with an exploratory score of
`0.7588`, but its judge calibration ID is `uncalibrated`. It is not valid final
baseline evidence.

Refer to [**Current State**](current-state/index.md) to find out more about the current project state.
