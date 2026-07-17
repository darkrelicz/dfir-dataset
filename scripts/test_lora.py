import time

import torch
from unsloth import FastLanguageModel

ADAPTER_PATH = "data/finetune/glm47_flash_v2/lora_adapter"
MAX_SEQ_LENGTH = 4096
MAX_NEW_TOKENS = 256

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is unavailable. Verify that nvidia-smi works and run this test "
        "from a GPU-enabled environment."
    )

print(f"Loading base model and LoRA adapter from {ADAPTER_PATH}...", flush=True)
load_started = time.perf_counter()
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTER_PATH,
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=True,
    trust_remote_code=True,
)
print(f"Model loaded in {time.perf_counter() - load_started:.1f}s.", flush=True)

FastLanguageModel.for_inference(model)

messages = [
    {"role": "user", "content": "hello"},
]

inputs = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    enable_thinking=False,
    return_tensors="pt",
).to(model.device)

print(f"Starting generation (maximum {MAX_NEW_TOKENS} new tokens)...", flush=True)
generation_started = time.perf_counter()
with torch.inference_mode():
    output = model.generate(
        inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
        use_cache=True,
    )
generation_seconds = time.perf_counter() - generation_started

generated_tokens = output[0, inputs.shape[-1]:]
generated_token_ids = generated_tokens.tolist()

print(tokenizer.decode(generated_tokens, skip_special_tokens=False))
print()
print("Generated tokens:", len(generated_tokens))
print("EOS generated:", tokenizer.eos_token_id in generated_token_ids)
print(f"Generation time: {generation_seconds:.1f}s")
if generation_seconds > 0:
    print(f"Generation speed: {len(generated_tokens) / generation_seconds:.2f} tokens/s")
