---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [FP8 inference, MXFP4, NVFP4, E4M3, E5M2]
summary: "Hardware-native FP8 and FP4 inference formats: layouts, scaling recipes, and the GPU-generation gating tying precision to your fleet."
---
> **One-paragraph hook:** FP8 and FP4 are more than "smaller floats." They're tensor-core-native formats, and they're only a *speed* win because the hardware executes them directly. Their quality survives because of *how* they're scaled as much as how many bits they use. Get the scaling granularity wrong and a "lossless" format silently corrupts output; get it right and fp8 is close to a free 2x over bf16.

## The mechanism

Bf16, the training-era default, spends 8 exponent bits on range and 7 mantissa bits on precision. FP8 drops that budget. **E4M3** (4 exponent, 3 mantissa bits, plus sign) is the workhorse for weights and activations: it gives up dynamic range for the extra mantissa bit that keeps rounding error tolerable. **E5M2** (5 exponent, 2 mantissa) swings back toward range at precision's expense and shows up mostly on the gradient side of training, not in inference. Neither format has the dynamic range to hold a tensor's raw values; a large activation outlier would overflow E4M3. So every fp8 tensor carries a **scale factor** that moves values into the format's sweet spot before the cast.

The scale's *granularity* matters more for quality than the bit-width:
- **Per-tensor** scaling (one scale for the whole tensor) is cheapest and fragile. One outlier channel forces a scale that starves every other value's mantissa bits.
- **Per-channel** (weights, one scale per output channel) and **per-token** (activations, one scale per token) hold up far better against the outlier structure real transformer activations have.
- **Block/tile-wise** scaling goes finer. DeepSeek-V3 used tile-wise fp8 scaling (small blocks of weights and small groups of activation channels, each with its own scale) to both *train* and *serve* natively in fp8, with reported negligible quality loss relative to higher precision; see [[Breakdown - DeepSeek-V3 Architecture]]. It's the strongest existence proof that fp8 needn't be a lossy post-hoc [[Concept - Post-Training Quantization Formats|PTQ]] step bolted onto a bf16-trained model. It can be the native precision end to end if the scaling recipe is fine-grained enough.

FP4 is the next format generation, and 2025-26 is when it reaches production serving. **MXFP4** is the OCP Microscaling spec: E2M1 values with one shared 8-bit E8M0 scale per 32-element block. **NVFP4** is Blackwell's variant, with an fp8 E4M3 scale per 16-element block, finer than MXFP4's. The same problem returns with higher stakes. E2M1 has essentially no room for error, so a block small enough to track local outlier structure is what separates a usable fp4 deployment from a broken one.

On the hardware side it's a throughput multiplier as well as a memory saving. NVIDIA's H100 SXM datasheet lists roughly **2x the dense TFLOPS for fp8 tensor-core execution versus bf16** (~1979 vs ~989 dense TFLOPS), and Blackwell's fp4 [[Concept - Tensor Cores]] paths target another ~2x over fp8. Each precision step down roughly doubles compute throughput and memory bandwidth utilization, because half (or a quarter) as many bytes move per element.

## In practice

The 2026 default on Hopper-and-newer NVIDIA fleets is **fp8 weights + fp8 KV cache** (the cache side is in [[Concept - KV Cache Quantization]]). It's treated as near-lossless and turned on essentially by default. vLLM, SGLang and [[Breakdown - TensorRT-LLM]] all expose it as a flag, with no research decision involved.

FP4 is where high-throughput serving is heading on Blackwell, but it isn't a drop-in yet. Recovering quality at 4 bits typically needs one of three things: mixed precision (lm_head, embeddings and the most sensitive MoE experts stay at higher precision), quantization-aware calibration, or rotation/Hadamard-style transforms. The transforms spread outlier energy across channels before the cast, so the post-rotation distribution is closer to uniform and easier to represent in 4 bits. Serving frameworks still recommend per-model task-level validation before shipping fp4. That's [[Decision - Choosing a Quantization Method]]'s "measure the actual downstream task, not perplexity" rule at the sharpest precision point in the stack.

Precision is hard-coupled to your fleet. Fp8 tensor-core paths need Hopper or newer (H100/H200, Ada to a lesser extent); fp4 needs Blackwell (B200/GB200). Ask for either on Ampere-class hardware (A100) and you get an outright error or a silent slow emulation path that casts up and computes in higher precision. You take the quality risk of low precision with none of the speed benefit, and since the code "runs," it's easy to ship unnoticed.

## Failure modes

The dominant failure is **granularity mismatch, not bit-width**. A too-coarse (per-tensor) scale on a tensor with heavy-tailed activations overflows and underflows at once. The outliers clip to the format's max, corrupting whatever depended on their true magnitude. Everything else is tiny relative to the forced scale and loses its remaining mantissa bits to rounding. So two "fp8" deployments of the same model, on the same hardware, at the same nominal bit-width, can differ dramatically in quality from the scaling recipe alone. "fp8" by itself isn't enough of a spec to compare vendors or engines.

The second recurring failure is silent hardware fallback. Requesting fp8/fp4 kernels on unsupported silicon rarely fails loudly, so the first symptom is usually "why didn't throughput improve," not a crash.

And as with weight [[Concept - Post-Training Quantization Formats|PTQ]] generally, reasoning, coding and tool-calling degrade at fp4 before perplexity moves. A model that reads fine in a smoke test can still fail structured output in production; see [[Gotchas - Quantization Quality Loss]].

## The non-obvious

The community learned this the hard way: scaling granularity, more than the number of mantissa bits, is usually the dominant factor in fp8/fp4 quality. A well-scaled per-token/per-block fp8 tensor routinely beats a badly-scaled per-tensor fp8 tensor at the *identical* nominal bit-width. "Runs in fp8" tells you almost nothing about output quality until you know the scaling recipe underneath. DeepSeek-V3's tile-wise scaling is the clearest public evidence that the engineering effort belongs on this axis, and the exponent/mantissa split matters less.

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
