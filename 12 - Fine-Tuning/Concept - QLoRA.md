---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [Quantized LoRA, NF4 fine-tuning]
summary: "4-bit NF4 base quantization plus bf16 LoRA adapters and paged optimizers, letting a 65B model fine-tune on one GPU."
---
# Concept - QLoRA

> **One-paragraph hook:** QLoRA is what let people fine-tune a 65B-parameter model on a single 48GB GPU in a day. It takes [[Deep Dive - LoRA]] and stores the frozen base in 4-bit, so the multi-ten-GB base-weight cost drops out of the memory budget, while the trainable LoRA adapters and all compute stay in full bf16 precision. The frozen base never updates, so its quantization error is a fixed, known quantity the adapter can learn to compensate for during training.

## The mechanism

Dettmers et al. (2023) combine three separate engineering ideas:

1. **NF4 (NormalFloat4) quantization of the frozen base.** Empirically, pretrained transformer weights are close to zero-mean normal within each block. NF4 is an information-theoretically optimal 4-bit datatype for that distribution: its 16 representable code points sit at the quantiles of a standard normal, per-block normalized so each of the 16 bins holds equal probability mass. It beats a uniform 4-bit int or fp4 format because it spends its few codepoints where the weight mass is, instead of spacing them linearly across the range. It's a refinement on the general theory in [[Concept - Floating Point for Deep Learning]].
2. **Double quantization.** Block-wise quantization needs a scale constant (absmax) per block, naively stored in fp32. QLoRA quantizes the scale constants themselves from 32-bit to 8-bit, saving roughly 0.37 bits per parameter. That's about 3GB on a 65B model, which matters when you're squeezing the whole thing under 48GB.
3. **Paged optimizers.** Gradient checkpointing causes sharp, transient memory spikes (recomputing activations during backward). QLoRA uses NVIDIA's unified memory to page [[Concept - Adam and AdamW]]'s optimizer state out to CPU RAM automatically during those spikes, a deliberate use of the [[Concept - GPU Memory Hierarchy]]. What would have been an OOM crash becomes a (rare) slowdown.

The demonstration was the Guanaco models: a 65B model fine-tuned on one 48GB GPU in under 24 hours, reaching roughly 99% of ChatGPT's quality on the Vicuna benchmark (as of 2023; that comparison point is now dated, but the memory-engineering result stands).

The base weights stay frozen throughout, and 4-bit is a storage format, not a compute format. Every matmul dequantizes the relevant NF4 block to bf16 on the fly, following the same [[Concept - Mixed Precision Training]] discipline used elsewhere in training, does the multiply, and discards the dequantized copy. Storage dtype and compute dtype differ everywhere in QLoRA. That's why it's inherently slower per step than 16-bit LoRA (dequant is extra work on the hot path), and why kernel work that fuses the dequant into the matmul, as [[Breakdown - Unsloth]] does, buys back much of the speed.

## In practice

The memory arithmetic is the appeal. A 7B model's weights are ~14GB in bf16 and ~3.5-4GB in NF4. Add a LoRA adapter (megabytes) and paged 8-bit optimizer state and the whole fine-tune fits comfortably under 16GB, on a single consumer GPU (full breakdown against full fine-tuning's ~84GB in [[Reference - Memory Math for Transformers]]). The standard configuration, `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)` plus a standard `LoraConfig`, is walked through flag by flag in [[Snippet - QLoRA Fine-Tune Configuration]].

Since the base is frozen and quantized once, training dynamics are otherwise the same as ordinary LoRA: same $A$,$B$ factorization, same $\alpha/r$ scaling, same gradient path. QLoRA is a memory optimization layered under LoRA, not a different training algorithm. NF4 sits alongside the [[Concept - Post-Training Quantization Formats]] used purely for inference (int8, fp8) but is distinct from them: NF4's point is staying close to trainable, not being optimal for serving.

## Failure modes

- **Merging into the quantized base loses accuracy.** $W_{\text{merged}} = \text{dequantize}(W_{\text{nf4}}) + (\alpha/r)BA$ requires dequantizing first. Adding the adapter directly to the quantized representation silently drops quality below the adapter-on-4bit baseline. Fix: always dequantize to fp16/bf16, merge, then decide separately whether to re-quantize for serving.
- **Slower wall-clock training than 16-bit LoRA.** Dequant-per-matmul is real overhead. QLoRA buys memory headroom with speed. If you have the VRAM for 16-bit LoRA, it will typically train faster.
- **NF4 degrades on outlier-heavy layers.** Its optimality assumes a near-normal weight distribution. Layers with heavy-tailed or multimodal weights (some embedding or output layers) quantize worse, which is part of why QLoRA keeps the LoRA adapters in full precision instead of pushing the adaptation into 4-bit too.

## The non-obvious

The paged-optimizer detail is easy to skip, but it's what makes QLoRA *robust* and not only memory-efficient. Without it, one unusually long sequence in a batch can spike activation memory during gradient-checkpointing recomputation and crash a run that had been fine for thousands of steps. Paging the spike out to CPU RAM turns a hard crash into a soft slowdown. For unattended multi-hour runs on rented spot GPUs that matters enormously. It reads like a footnote in the paper, and it's the part anyone actually running the job depends on.

## Connections

- [[Deep Dive - LoRA]] — QLoRA is the same BA factorization with the base additionally quantized; the LoRA math itself is unchanged.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — LoftQ specifically targets the quantization error QLoRA's zero-init leaves uncompensated at step 0.
- [[Concept - Floating Point for Deep Learning]] — NF4's design (quantile placement for a normal distribution) only makes sense against the general theory of floating-point and quantized number formats.
- [[Concept - Post-Training Quantization Formats]] — NF4 is a training-compatible analog to the int8/fp8 formats used for inference-time quantization.
- [[Concept - Mixed Precision Training]] — the bf16 compute path QLoRA dequantizes into is the same mixed-precision discipline used elsewhere in training.
- [[Concept - Adam and AdamW]] — the optimizer whose state the paged-optimizer trick offloads to CPU RAM.
- [[Concept - GPU Memory Hierarchy]] — paged optimizers are a direct application of unified memory across this hierarchy.
- [[Reference - Memory Math for Transformers]] — the source of the concrete GB figures for 4-bit vs bf16 base storage.
- [[Snippet - QLoRA Fine-Tune Configuration]] — the exact runnable config implementing every flag discussed here.
- [[Breakdown - Unsloth]] — the kernel engineering that claws back the dequant-overhead speed QLoRA gives up.

## Sources
- Dettmers et al. (2023) — "QLoRA: Efficient Finetuning of Quantized LLMs." Introduces NF4, double quantization, and paged optimizers; trains Guanaco.
