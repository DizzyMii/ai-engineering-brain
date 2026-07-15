---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [FP8 inference, MXFP4, NVFP4, E4M3, E5M2]
summary: "Hardware-native FP8 and FP4 inference formats: layouts, scaling recipes, and the GPU-generation gating tying precision to your fleet."
---
> **One-paragraph hook:** FP8 and FP4 aren't just "smaller floats" — they're tensor-core-native formats that only exist as a *speed* win because the hardware executes them directly, and their quality only survives because of *how* they're scaled, not just how many bits they use. Get the scaling granularity wrong and a "lossless" format silently corrupts output; get it right and fp8 is close to a free 2x over bf16.

## The mechanism

Bf16, the training-era default, spends 8 exponent bits and 7 mantissa bits on range and precision respectively. FP8 abandons that budget entirely: **E4M3** (4 exponent, 3 mantissa bits, plus sign) is the workhorse for weights and activations, trading dynamic range for the extra mantissa bit that keeps rounding error tolerable; **E5M2** (5 exponent, 2 mantissa) trades back toward range at precision's expense and shows up mostly on the gradient side of training rather than inference. Neither format has enough native dynamic range to hold a tensor's raw values directly — a large activation outlier would simply overflow E4M3's representable range — so every fp8 tensor carries a **scale factor** that rescales values into the format's sweet spot before the cast.

That scale's *granularity* is the actual quality lever, more than the bit-width itself:
- **Per-tensor** scaling (one scale for the whole tensor) is cheapest but fragile — a single outlier channel forces a scale that starves every other value's mantissa bits.
- **Per-channel** (weights, one scale per output channel) and **per-token** (activations, one scale per token) are far more robust to the outlier structure real transformer activations actually have.
- **Block/tile-wise** scaling goes finer still: DeepSeek-V3 used fine-grained tile-wise fp8 scaling (small blocks of weights, small groups of activation channels each carrying their own scale) to both *train* and *serve* natively in fp8 with reported negligible quality loss relative to higher precision — see [[Breakdown - DeepSeek-V3 Architecture]]. This is the strongest existence proof that fp8 doesn't have to be a lossy post-hoc [[Concept - Post-Training Quantization Formats|PTQ]] step bolted onto a bf16-trained model — it can be the native precision end to end, provided the scaling recipe is fine-grained enough.

FP4 pushes one format generation further, and 2025-26 is where it becomes a serving reality: **MXFP4** (the OCP Microscaling spec — E2M1 values, one shared 8-bit E8M0 scale per 32-element block) and **NVFP4** (Blackwell's variant — an fp8 E4M3 scale per 16-element block, a finer granularity than MXFP4's). The core problem repeats at higher stakes: E2M1 has essentially no room for error, so getting the block small enough to track local outlier structure is what separates a usable fp4 deployment from a broken one.

On the hardware side, this is a genuine throughput multiplier, not just a memory saving: NVIDIA's H100 SXM datasheet lists roughly **2x the dense TFLOPS for fp8 tensor-core execution versus bf16** (published as ~1979 vs ~989 dense TFLOPS), and Blackwell's fp4 [[Concept - Tensor Cores]] paths target another ~2x over fp8 on top of that — each precision step down roughly doubles both compute throughput and memory bandwidth utilization, since half (or a quarter) as many bytes move per element.

## In practice

The 2026 default on Hopper-and-newer NVIDIA fleets is **fp8 weights + fp8 KV cache** — see [[Concept - KV Cache Quantization]] for the cache side — treated as near-lossless and turned on essentially by default; vLLM, SGLang, and [[Breakdown - TensorRT-LLM]] all expose it as a straightforward flag rather than a research decision. FP4 is where high-throughput serving is heading on Blackwell but is not yet a drop-in: quality recovery at 4 bits typically needs mixed precision (keeping the lm_head, embeddings, and the most sensitive MoE experts at higher precision), quantization-aware calibration, or rotation/Hadamard-style transforms that spread outlier energy across channels before the cast, making the post-rotation distribution closer to uniform and therefore more representable in 4 bits. Serving frameworks still recommend per-model task-level validation before shipping fp4, which is exactly [[Decision - Choosing a Quantization Method]]'s "measure the actual downstream task, not perplexity" rule applied at the sharpest precision point in the stack.

Precision choice is coupled to your fleet, hard: fp8 tensor-core paths require Hopper or newer (H100/H200, Ada to a lesser extent); fp4 requires Blackwell (B200/GB200). Request either format on Ampere-class hardware (A100) and you either get an outright error or a silent slow emulation path that casts up and computes in higher precision — you absorb the quality risk of low precision with none of the speed benefit, and because the code "runs," this is easy to ship unnoticed.

## Failure modes

The dominant failure is **granularity mismatch, not bit-width**: a too-coarse (per-tensor) scale on a tensor with heavy-tailed activations simultaneously overflows the outlier values (clipped to the format's max, corrupting whatever depended on their true magnitude) and underflows everything else (most values, tiny relative to the forced scale, lose their remaining mantissa bits to rounding) — a single bad scaling choice produces both failure modes in the same tensor at once. This is why two "fp8" deployments of the same model, on the same hardware, at the same nominal bit-width, can differ dramatically in quality purely from their scaling recipe — "fp8" alone is not a sufficient spec to compare vendors or engines against each other. The second recurring failure is silent hardware fallback: requesting fp8/fp4 kernels on unsupported silicon rarely fails loudly, so the first symptom is usually "why didn't throughput improve," not a crash. And as with weight [[Concept - Post-Training Quantization Formats|PTQ]] generally, reasoning, coding, and tool-calling degrade before perplexity moves at fp4, so a model that reads fine in a smoke test can still fail structured output in production — see [[Gotchas - Quantization Quality Loss]].

## The non-obvious

The community learned this the hard way: scaling granularity, not the number of mantissa bits, is usually the dominant factor in fp8/fp4 quality. A well-scaled per-token/per-block fp8 tensor routinely beats a badly-scaled per-tensor fp8 tensor at the *identical* nominal bit-width — meaning the marketing claim "runs in fp8" tells you almost nothing about output quality until you know the scaling recipe underneath it. DeepSeek-V3's fine-grained tile-wise scaling is the clearest public evidence that this axis, not the exponent/mantissa split, is where the real engineering effort belongs.

## Connections
- [[Concept - Post-Training Quantization Formats]] — the integer-PTQ sibling (GPTQ/AWQ/GGUF); fp8/fp4 are the hardware-native floating-point alternative to those calibration-based integer schemes.
- [[Concept - Floating Point for Deep Learning]] — cross-domain (01) grounding: the exponent/mantissa fundamentals that E4M3/E5M2/E2M1 are specific points on.
- [[Concept - Tensor Cores]] — cross-domain (08) grounding: the hardware unit that makes fp8/fp4 a throughput win, not just a memory one.
- [[Concept - Mixed Precision Training]] — cross-domain (04) grounding: the training-side lineage of scaled low-precision formats that inference fp8/fp4 descends from.
- [[Breakdown - DeepSeek-V3 Architecture]] — the clearest public case of fine-grained fp8 scaling used natively for both training and serving.
- [[Concept - KV Cache Quantization]] — applying these same formats to the KV cache specifically, the other half of a full fp8 deployment.
- [[Decision - Choosing a Quantization Method]] — the practical decision this note's format details feed into.
- [[Concept - GPU Memory Hierarchy]] — cross-domain (08) grounding: the bandwidth savings that make lower precision a latency lever, not just a capacity one.
- [[Gotchas - Quantization Quality Loss]] — the general failure-mode catalog that this note's granularity-mismatch failure is a sharper instance of.

## Sources
- DeepSeek-AI (2024) — DeepSeek-V3 technical report. Fine-grained tile-wise fp8 scaling used natively for both training and serving, with reported negligible quality loss.
- Rouhani, B. D. et al. (2023) — *"Microscaling Data Formats for Deep Learning"* (Open Compute Project). The MX (MXFP4/MXFP8) specification underlying the shared-block-scale fp4 format.
- NVIDIA (2024) — Blackwell architecture whitepaper. NVFP4 format and native Blackwell fp4 tensor-core execution.
