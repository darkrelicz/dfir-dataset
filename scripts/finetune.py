import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only

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
        "training": config.get("finetune", {}),
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

    dataset_config = config["dataset"]
    model_config = config["model"]
    lora_config = config["lora"]
    finetune_config = config["finetune"]
    export_config = config["export"]

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["base_model"],
        max_seq_length=int(model_config["max_seq_length"]),
        load_in_4bit=True,
        trust_remote_code=True,
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
    )

    dataset = load_dataset(
        "json",
        data_files={
            "train": dataset_config["train_path"],
            "validation": dataset_config["validation_path"],
        },
    )

    dataset = render_training_dataset(
        dataset,
        tokenizer,
        max_length=int(model_config["max_seq_length"]),
    )

    sft_args = build_sft_config(model_config, finetune_config, config)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        args=sft_args,
    )
    trainer = train_on_responses_only(
        trainer,
        num_proc=finetune_config["dataset_num_proc"],
    )

    stats = trainer.train()
    model.save_pretrained(export_config["adapter_dir"])
    tokenizer.save_pretrained(export_config["adapter_dir"])
    model.save_pretrained_gguf(
        export_config["gguf_dir"],
        tokenizer,
        quantization_method=export_config["gguf_quantization"],
    )

    return {
        "train_result": str(stats),
        "adapter_dir": export_config["adapter_dir"],
    }


def format_messages_for_training(
    messages_batch: list[list[dict[str, Any]]],
    tokenizer: Any,
    *,
    max_length: int,
) -> list[str]:
    """Render conversations, append EOS explicitly, and reject truncation."""

    eos_token = tokenizer.eos_token
    if not eos_token:
        raise ValueError("Tokenizer must define an EOS token before SFT formatting")

    texts: list[str] = []
    for messages in messages_batch:
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        if not rendered.endswith(eos_token):
            rendered += eos_token
        texts.append(rendered)

    encoded = tokenizer(
        texts,
        add_special_tokens=False,
        truncation=False,
    )["input_ids"]
    oversized = [
        (index, len(token_ids))
        for index, token_ids in enumerate(encoded)
        if len(token_ids) > max_length
    ]
    if oversized:
        preview = ", ".join(
            f"batch_index={index} tokens={length}"
            for index, length in oversized[:10]
        )
        raise ValueError(
            f"Rendered training examples exceed max_length={max_length}: {preview}"
        )
    return texts


def render_training_dataset(
    dataset: Any,
    tokenizer: Any,
    *,
    max_length: int,
) -> Any:
    """Replace source messages with the exact text that TRL must tokenize."""

    def format_messages(batch: dict[str, Any]) -> dict[str, list[str]]:
        return {
            "text": format_messages_for_training(
                batch["messages"],
                tokenizer,
                max_length=max_length,
            )
        }

    # Without removing `messages`, TRL identifies the row as conversational and
    # silently applies the chat template again instead of consuming `text`.
    return dataset.map(
        format_messages,
        batched=True,
        remove_columns=["messages"],
    )


def build_sft_config(
    model_config: dict[str, Any],
    finetune_config: dict[str, Any],
    config: dict[str, Any],
) -> Any:
    from trl.trainer.sft_config import SFTConfig

    sft_kwargs: dict[str, Any] = {
        "output_dir": finetune_config["output_dir"],
        "dataset_text_field": "text",
        "dataset_num_proc": finetune_config["dataset_num_proc"],
        "max_length": int(model_config["max_seq_length"]),
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
        "report_to": "none",
        "seed": int(config["run"]["seed"]),
        "warmup_ratio": float(finetune_config["warmup_ratio"]),
    }
    return SFTConfig(**sft_kwargs)


if __name__ == "__main__":
    main()
