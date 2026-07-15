---
tags: [snippet, domain/fine-tuning, level/core]
aliases: [QLoRA config, bitsandbytes 4-bit SFT]
summary: "Runnable QLoRA setup (transformers + bitsandbytes + peft + TRL) with every load-bearing 4-bit and LoRA flag annotated."
---
# Snippet - QLoRA Fine-Tune Configuration

> **What it does:** fine-tunes an 8B base as a 4-bit QLoRA on a single ~16GB GPU. **Dependencies:** `transformers` 4.46, `peft` 0.13, `bitsandbytes` 0.44, `trl` 0.12, `accelerate` 1.0, `datasets` 3.0 (CUDA 12.1, Linux; see the Windows note below). **Expected output:** `trainable params: ~42M / 8.0B (~0.52%)` and a decreasing SFT loss (roughly `1.8 → 1.1` over one epoch on a small chat set).

This is the config that actually matters. Everything else — the dataset, the eval — is elsewhere ([[Playbook - Preparing a Fine-Tuning Dataset]]); the flags below are the ones that silently decide whether your run trains at all, and each maps to a specific piece of the [[Concept - QLoRA]] mechanism.

```python
# QLoRA supervised fine-tune: 4-bit NF4 frozen base + bf16 LoRA adapters on one ~16GB card.
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training
from trl import SFTConfig, SFTTrainer

model_id = "meta-llama/Meta-Llama-3.1-8B"

# 1) Quantize the FROZEN base to 4-bit NF4. Storage dtype (4-bit) != compute dtype (bf16).
bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",              # NormalFloat4: codepoints at normal-dist quantiles, not int4
    bnb_4bit_compute_dtype=torch.bfloat16,  # every matmul dequantizes NF4 -> bf16 on the fly
    bnb_4bit_use_double_quant=True,         # quantize the per-block scale constants too (~0.4 bit/param)
)

tok = AutoTokenizer.from_pretrained(model_id)
tok.pad_token = tok.eos_token               # Llama base ships no pad token
tok.padding_side = "right"                  # left-pad is for generation; training pads right

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# 2) Wire gradient checkpointing + input grads for a k-bit base.
#    WITHOUT this, gradients never reach the adapters and the loss sits flat forever.
model = prepare_model_for_kbit_training(model)

# 3) LoRA on ALL linear layers (coverage beats rank); alpha = 2r.
peft_cfg = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    target_modules="all-linear",            # q,k,v,o,gate,up,down — NOT just q,v
    task_type="CAUSAL_LM",
)

# NOTE: a *base* model has no chat template — you own it. Verify formatting before training
# (see the dataset playbook and the chat-template gotchas). Here we use a pre-formatted chat set.
ds = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft[:2000]")

args = SFTConfig(
    output_dir="qlora-llama3-8b",
    num_train_epochs=1,                     # 1-3; >3 overfits small sets fast
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,          # effective batch = 16
    learning_rate=2e-4,                     # ~10x a full-FT LR; only A,B are trained
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    bf16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",               # paged: spill optimizer state to CPU RAM on memory spikes
    max_seq_length=2048,
    logging_steps=10,
)

trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=ds,
    peft_config=peft_cfg,                    # SFTTrainer calls get_peft_model for you
    processing_class=tok,
)
trainer.train()

# 4) Saving writes ONLY the ~80MB adapter, not the 16GB base.
trainer.save_model("qlora-llama3-8b/adapter")
```

To deploy with zero inference overhead, merge — but **load the base in fp16 first**, never merge into the 4-bit weights:

```python
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16)  # NOT load_in_4bit
merged = PeftModel.from_pretrained(base, "qlora-llama3-8b/adapter").merge_and_unload()
merged.save_pretrained("qlora-llama3-8b/merged")
```

## Why it's written this way

- **`optim="paged_adamw_8bit"` — paged optimizer for OOM safety.** Gradient checkpointing recomputes activations in the backward pass, producing sharp transient memory spikes; a single unusually long sequence can OOM a run that was fine for thousands of steps. The paged optimizer pages [[Concept - QLoRA|Adam]] state to CPU RAM during the spike, turning a hard crash into a soft slowdown — the difference between a robust unattended run and a 3 a.m. failure on a rented spot GPU.
- **`target_modules="all-linear"` — coverage beats rank.** The original LoRA paper adapted only `q,v`; modern practice adapts every linear (attention *and* MLP `gate/up/down`). Broadening the target set recovers far more of the full-fine-tuning gap than raising `r` does, at nearly the same cost. Defaults in [[Reference - Fine-Tuning Hyperparameters]] assume this.
- **`bf16` compute despite 4-bit storage.** NF4 is a *storage* format; each matmul dequantizes the relevant block to bf16, multiplies, and discards the copy — the same [[Concept - Mixed Precision Training]] discipline used in pretraining, distinct from the int8/fp8 [[Concept - Post-Training Quantization Formats]] used for inference. This dequant-per-matmul is exactly the overhead [[Breakdown - Unsloth]] fuses away.
- **`use_double_quant=True` — nearly free memory.** Quantizing the block scale constants from fp32 to 8-bit saves ~0.4 bit/param (about 3GB on a 65B model) at negligible quality cost; leave it on.
- **`prepare_model_for_kbit_training(model)` is not optional.** It enables `gradient_checkpointing` and, critically, `enable_input_require_grads()` so gradients flow into a frozen k-bit base. Omitting it is the number-one "loss won't move" bug in [[Gotchas - LoRA Fine-Tuning]].

**Version caveat:** TRL's trainer API churns fast. In older versions pass `tokenizer=` instead of `processing_class=`, use `TrainingArguments` + `SFTTrainer(max_seq_length=..., dataset_text_field=...)` instead of `SFTConfig`, and expect `merge_and_unload` return signatures to shift. Pin every version. On **Windows**, `bitsandbytes` historically needed a community CUDA build (`bitsandbytes-windows`) or WSL2 — check current wheel support before assuming `pip install bitsandbytes` gives you a working 4-bit kernel.

This whole setup runs an [[Concept - Supervised Fine-Tuning (SFT)]] objective; QLoRA is orthogonal to the objective — swap `SFTTrainer` for a DPO/GRPO trainer and the `BitsAndBytesConfig`/`LoraConfig` block is identical.

## Connections
- [[Concept - QLoRA]] — the NF4 / double-quant / paged-optimizer mechanism each flag here switches on.
- [[Deep Dive - LoRA]] — the `r`/`alpha`/`target_modules` knobs in `LoraConfig` and what they do.
- [[Reference - Fine-Tuning Hyperparameters]] — the source of the `2e-4` LR, `warmup_ratio`, epoch, and rank defaults used above.
- [[Gotchas - LoRA Fine-Tuning]] — why `prepare_model_for_kbit_training` and fp16-before-merge are load-bearing.
- [[Playbook - Preparing a Fine-Tuning Dataset]] — the dataset and chat-template work this snippet deliberately assumes done.
- [[Breakdown - Unsloth]] — a near-drop-in wrapper that makes this exact config ~2x faster and 50-80% lighter.
- [[Concept - Mixed Precision Training]] — the bf16 compute path the 4-bit weights are dequantized into.
- [[Concept - Post-Training Quantization Formats]] — the inference-time int8/fp8 formats NF4 is deliberately *not* (it stays trainable-adjacent).
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training objective this config runs; QLoRA is orthogonal to it.

## Sources
- Dettmers et al. (2023) — *QLoRA: Efficient Finetuning of Quantized LLMs.* Origin of NF4, double quantization, and paged optimizers, all wired up in the config above.
