import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unsloth import FastLanguageModel

from utils.io import load_json, load_yaml, log_stage_complete, write_json

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unsloth LoRA SFT runner")
    parser.add_argument("--config", default="configs/finetune_glm47flash.yaml")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    raise SystemExit(run_training(args))


def run_training(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    config_path = Path(args.config)
    config = load_yaml(config_path)
    created_at = datetime.now(timezone.utc)
    run_id = f"train-{created_at.strftime('%Y%m%dT%H%M%SZ')}"

    output_dir = Path(config["finetune"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    stage_started = time.perf_counter()
    dataset_summary = validate_dataset_inputs(config)
    log_stage_complete(logger, "validated training dataset inputs", stage_started)

    manifest = {
        "run_id": run_id,
        "created_at": created_at.isoformat(),
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "dataset": dataset_summary,
        "model": config.get("model", {}),
        "lora": config.get("lora", {}),
        "training": config.get("training", {}),
        "export": config.get("export", {}),
    }

    stage_started = time.perf_counter()
    trainer_stats = train_with_unsloth(config)
    log_stage_complete(logger, "completed Unsloth LoRA training", stage_started)
    manifest["trainer_stats"] = trainer_stats
    write_json(output_dir / "training_manifest.json", manifest)

    log_stage_complete(logger, "completed Phase 6 training runner", started)
    print(f"Training complete: manifest={output_dir / 'training_manifest.json'}")
    return 0


def validate_dataset_inputs(config: dict[str, Any]) -> dict[str, Any]:
    dataset_config = config["dataset"]
    paths = {
        "train": Path(dataset_config["train_path"]),
        "validation": Path(dataset_config["validation_path"]),
        "test": Path(dataset_config["test_path"]),
        "packaging_manifest": Path(dataset_config["packaging_manifest_path"]),
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {name} input: {path}")

    packaging_manifest = load_json(paths["packaging_manifest"], logger)
    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "packaging_manifest_run_id": packaging_manifest.get("run_id"),
        "packaged_pairs": packaging_manifest.get("packaged_pairs"),
        "splits": packaging_manifest.get("splits", {}),
        "response_style": packaging_manifest.get("response_style", {}),
    }


def train_with_unsloth(config: dict[str, Any]) -> dict[str, Any]:
    from datasets import load_dataset
    from trl.trainer.sft_trainer import SFTTrainer
    from unsloth.chat_templates import train_on_responses_only

    dataset_config = config["dataset"]
    model_config = config["model"]
    lora_config = config["lora"]
    finetune_config = config["finetune"]
    export_config = config.get("export", {})

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["base_model"],
        max_seq_length=int(model_config["max_seq_length"]),
        load_in_4bit=bool(model_config.get("load_in_4bit")),
        load_in_8bit=bool(model_config.get("load_in_8bit")),
        load_in_16bit=bool(model_config.get("load_in_16bit")),
        full_finetuning=bool(model_config.get("full_finetuning")),
        trust_remote_code=bool(model_config.get("trust_remote_code")),
        unsloth_force_compile=bool(model_config.get("unsloth_force_compile")),
    )   

    model = FastLanguageModel.get_peft_model(
        model,
        r=int(lora_config["rank"]),
        target_modules=list(lora_config["target_modules"]),
        lora_alpha=int(lora_config["alpha"]),
        lora_dropout=int(lora_config["dropout"]),
        bias=str(lora_config["bias"]),
        use_gradient_checkpointing=lora_config.get("use_gradient_checkpointing"),
        random_state=int(lora_config["random_state"]),
        use_rslora=bool(lora_config.get("use_rslora", False)),
        loftq_config=lora_config.get("loftq_config"),
    )

    dataset = load_dataset(
        "json",
        data_files={
            "train": dataset_config["train_path"],
            "validation": dataset_config["validation_path"],
        },
    )

    def format_messages(batch: dict[str, Any]) -> dict[str, list[str]]:
        texts = [
            tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            for messages in batch["messages"]
        ]
        return {dataset_config.get("text_field", "text"): texts}

    dataset = dataset.map(format_messages, batched=True)

    sft_args = build_sft_config(dataset_config, model_config, finetune_config, config)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        args=sft_args,
    )
    if bool(finetune_config.get("train_on_responses_only", True)):
        response_masking_config = finetune_config.get("response_masking", {}) or {}
        instruction_part = response_masking_config.get("instruction_part")
        response_part = response_masking_config.get("response_part")
        masking_kwargs = {}
        if (instruction_part is None) != (response_part is None):
            raise ValueError(
                "response_masking.instruction_part and response_masking.response_part "
                "must both be set, or both be null for Unsloth auto-detection."
            )
        if instruction_part is not None or response_part is not None:
            masking_kwargs["instruction_part"] = str(instruction_part)
            masking_kwargs["response_part"] = str(response_part)
        trainer = train_on_responses_only(
            trainer,
            num_proc=finetune_config.get("dataset_num_proc"),
            **masking_kwargs,
        )

    stats = trainer.train()
    if bool(export_config.get("save_lora_adapter", True)):
        model.save_pretrained(export_config["adapter_dir"])
        tokenizer.save_pretrained(export_config["adapter_dir"])
    if bool(export_config.get("save_merged_16bit", False)):
        model.save_pretrained_merged(
            export_config["merged_16bit_dir"],
            tokenizer,
            save_method="merged_16bit",
        )
    return {
        "train_result": str(stats),
        "adapter_dir": export_config.get("adapter_dir"),
        "merged_16bit_dir": export_config.get("merged_16bit_dir")
        if bool(export_config.get("save_merged_16bit", False))
        else None,
    }


def build_sft_config(
    dataset_config: dict[str, Any],
    model_config: dict[str, Any],
    finetune_config: dict[str, Any],
    config: dict[str, Any],
) -> Any:
    from trl.trainer.sft_config import SFTConfig

    sft_kwargs: dict[str, Any] = {
        "output_dir": finetune_config["output_dir"],
        "dataset_text_field": dataset_config.get("text_field", "text"),
        "dataset_num_proc": finetune_config.get("dataset_num_proc"),
        "max_length": int(finetune_config.get("max_length", model_config["max_seq_length"])),
        "per_device_train_batch_size": int(finetune_config["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(finetune_config["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(finetune_config["gradient_accumulation_steps"]),
        "learning_rate": float(finetune_config["learning_rate"]),
        "num_train_epochs": float(finetune_config["num_train_epochs"]),
        "lr_scheduler_type": str(finetune_config["lr_scheduler_type"]),
        "optim": str(finetune_config["optim"]),
        "weight_decay": float(finetune_config["weight_decay"]),
        "logging_steps": int(finetune_config["logging_steps"]),
        "eval_strategy": str(finetune_config["eval_strategy"]),
        "eval_steps": int(finetune_config["eval_steps"]),
        "save_strategy": str(finetune_config["save_strategy"]),
        "save_steps": int(finetune_config["save_steps"]),
        "save_total_limit": int(finetune_config["save_total_limit"]),
        "bf16": bool(finetune_config["bf16"]),
        "fp16": bool(finetune_config["fp16"]),
        "report_to": str(finetune_config["report_to"]),
        "seed": int(config["run"]["seed"]),
    }
    if "warmup_steps" in finetune_config:
        sft_kwargs["warmup_steps"] = int(finetune_config["warmup_steps"])
    else:
        sft_kwargs["warmup_ratio"] = float(finetune_config["warmup_ratio"])
    if "max_steps" in finetune_config:
        sft_kwargs["max_steps"] = int(finetune_config["max_steps"])
    return SFTConfig(**sft_kwargs)


if __name__ == "__main__":
    main()
