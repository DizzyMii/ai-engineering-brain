---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [Quantized LoRA, NF4 fine-tuning]
summary: "4-bit NF4 base quantization plus bf16 LoRA adapters and paged optimizers, letting a 65B model fine-tune on one GPU."
---
# Concept - QLoRA

> **One-paragraph hook:** QLoRA is what let people fine-tune a 65B-parameter model on a single 48GB GPU in a day. It takes [[Deep Dive - LoRA]] and pushes the frozen base into 4-bit storage, so the multi-ten-GB base-weight cost disappears from the memory budget entirely — while keeping the trainable LoRA adapters, and all compute, in full bf16 precision. The frozen base never updates, so its quantization error is a fixed, known quantity that the adapter can learn to compensate for during training.

## The mechanism

Dettmers et al. (2023) combine three separate engineering ideas:

1. **NF4 (NormalFloat4) quantization of the frozen base.** Pretrained transformer weights are, empirically, close to zero-mean normally distributed within each block. NF4 is an information-theoretically optimal 4-bit datatype for exactly that distribution: its 16 representable code points are placed at the quantiles of a standard normal, per-block normalized so each of the 16 bins captures equal probability mass. This beats a uniform 4-bit int or fp4 format specifically because it spends its limited codepoints where the weight mass actually is, rather than spacing them linearly across the range — a refinement on top of the general theory covered in [[Concept - Floating Point for Deep Learning]].
2. **Double quantization.** Block-wise quantization needs a scale constant (absmax) per block; naively these are stored in fp32. QLoRA quantizes the scale constants themselves from 32-bit down to 8-bit, saving roughly 0.37 bits per parameter — about 3GB on a 65B model, which matters when you're trying to fit the whole thing under 48GB.
3. **Paged optimizers.** Gradient checkpointing produces sharp, transient memory spikes (recomputing activations during backward). QLoRA uses NVIDIA's unified memory to automatically page [[Concept - Adam and AdamW]]'s optimizer state out to CPU RAM during these spikes — a deliberate exploitation of the [[Concept - GPU Memory Hierarchy]] — converting what would be an OOM crash into a (rare) slowdown.

The result, on the Guanaco models trained as a demonstration: a 65B model fine-tuned on one 48GB GPU in under 24 hours, reaching roughly 99% of ChatGPT's quality on the Vicuna benchmark (as of 2023 — a specific, now-dated comparison point, but the memory-engineering result stands).

Critically, the base weights are frozen throughout — 4-bit is a storage format, not a compute format. Every matmul dequantizes the relevant NF4 block to bf16 on the fly, per the same [[Concept - Mixed Precision Training]] discipline used elsewhere in training, does the multiply, and discards the dequantized copy. Storage dtype and compute dtype differ throughout QLoRA: this is why it is fundamentally slower than 16-bit LoRA per step (dequant is extra work on the hot path), and why kernel-level engineering — fusing the dequant into the matmul, as [[Breakdown - Unsloth]] does — buys back much of that speed.

## In practice

Memory arithmetic makes the appeal concrete: a 7B model's weights in bf16 are ~14GB; the same weights in NF4 are ~3.5-4GB. Add a LoRA adapter (megabytes) and paged 8-bit optimizer state, and the whole fine-tune fits comfortably under 16GB — a single consumer GPU (full breakdown against full fine-tuning's ~84GB in [[Reference - Memory Math for Transformers]]). A concrete, load-bearing configuration — `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)` plus a standard `LoraConfig` — is worked through flag-by-flag in [[Snippet - QLoRA Fine-Tune Configuration]].

Because the base is frozen and quantized once, the training dynamics are otherwise identical to ordinary LoRA: same $A$,$B$ factorization, same $\alpha/r$ scaling, same gradient path. QLoRA is a memory optimization layered under LoRA, not a different training algorithm — NF4 sits alongside, but is distinct from, the [[Concept - Post-Training Quantization Formats]] used purely for inference (int8, fp8), since NF4's whole point is remaining trainable-adjacent rather than serving-optimal.

## Failure modes

- **Merging into the quantized base loses accuracy.** $W_{\text{merged}} = \text{dequantize}(W_{\text{nf4}}) + (\alpha/r)BA$ requires dequantizing first; adding the adapter directly to the quantized representation silently degrades quality below the adapter-on-4bit baseline. Fix: always dequantize to fp16/bf16, merge, then decide separately whether to re-quantize for serving.
- **Slower wall-clock training than 16-bit LoRA.** The dequant-per-matmul step is real overhead; QLoRA trades speed for memory headroom, not the reverse. If you have the VRAM for 16-bit LoRA, it will typically train faster.
- **NF4 degrades on outlier-heavy layers.** The datatype's optimality assumption is a near-normal weight distribution; layers with heavy-tailed or multimodal weight distributions (some embedding or output layers) quantize worse — part of why QLoRA keeps the LoRA adapters themselves in full precision rather than trying to push the adaptation into 4-bit too.

## The non-obvious

The paged-optimizer detail is easy to skip past, but it's the difference between QLoRA being merely memory-efficient and being *robust*: without it, a single unusually long sequence in a batch can spike activation memory during gradient-checkpointing recomputation and crash a run that had been fine for thousands of steps. Paging that spike out to CPU RAM converts a hard crash into a soft slowdown, which matters enormously for unattended multi-hour runs on rented spot GPUs — it's the kind of detail that reads as a footnote in the paper but is load-bearing for anyone actually running the training job.

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
