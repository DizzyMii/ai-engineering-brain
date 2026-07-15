---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [FP8 pretraining, E4M3, E5M2, 8-bit floating point training]
summary: "Training LLMs in 8-bit floating point — the E4M3/E5M2 formats, why scaling is the real problem, and how DeepSeek-V3 made it production-viable."
---

# Concept - FP8 Training

> **One-paragraph hook:** Hopper and Blackwell tensor cores execute fp8 matmuls at roughly 2x the throughput of [[Concept - Mixed Precision Training|bf16]] and at half the memory footprint, but fp8 pretraining was folklore-unstable for years — teams that tried a naive port of bf16 recipes into 8 bits got divergent or quietly-worse-quality runs. DeepSeek-V3 (2024) is the proof it can work at frontier scale: 671B parameters, mostly-fp8 GEMMs, near-bf16 quality, at a fraction of the compute cost — and the fix wasn't the format, it was scaling discipline.

## The mechanism

FP8 comes in two formats standardized by the Open Compute Project (Micikevicius et al. 2022): **E4M3** (1 sign bit, 4 exponent bits, 3 mantissa bits, dynamic range roughly ±448) and **E5M2** (1 sign, 5 exponent, 2 mantissa — more range, less precision, mirroring the fp16-vs-bf16 tradeoff from [[Concept - Mixed Precision Training]]). The convention is E4M3 for forward-pass activations and weights, where values have already been normalized by layernorm/softmax and don't need much dynamic range, and E5M2 for gradients, which can vary in magnitude by orders of magnitude across layers and need the extra exponent bits more than the extra mantissa bit.

The hard problem is not the format — it's that fp8's dynamic range is minuscule (roughly 2^-9 to 448 for E4M3, versus bf16's ~10^±38), so a value falling outside that range either underflows to zero or overflows to infinity, and *scaling* — choosing the per-tensor multiplier that maps real values into fp8's representable range — becomes the entire game. Two scaling strategies are in production use: **delayed scaling**, which reuses a rolling history of past steps' amax (absolute max) values to set the current step's scale factor (cheap, but reacts slowly to a sudden value spike), and **current-tensor (just-in-time) scaling**, which computes the amax of the actual tensor before quantizing it (more accurate, costs an extra reduction pass). DeepSeek-V3's contribution was **fine-grained scaling**: instead of one scale factor for an entire tensor, use a separate scale per 1×128 tile for activations and per 128×128 block for weights, so a single outlier value (common near attention or MoE router logits) blows the scale for its own small tile rather than degrading precision for the whole tensor.

What stays in high precision, deliberately: the fp32 master weights and optimizer moments (the accumulate/update step, exactly as in [[Concept - Mixed Precision Training]], never happens directly in 8-bit), layernorm statistics and softmax. Most critically, **the fp8×fp8 matmul must accumulate its partial sums in fp32** — and this is not automatic. Hopper tensor cores' native fp8 GEMM path accumulates internally at reduced precision, so summing hundreds of fp8 products (the inner dimension of a large matmul) loses precision exactly where you'd expect a high-precision accumulator to save you. DeepSeek-V3's fix was to periodically promote partial sums out to an fp32 accumulation path via CUDA cores rather than trusting the tensor core's native accumulator end to end.

## In practice

DeepSeek-V3 (DeepSeek-AI, 2024) is, per the inventory, the first production-scale fp8-pretrained LLM: 671B total parameters (37B active, MoE), trained for roughly 2.788M H800 GPU-hours, with the majority of GEMMs run in fp8 and sensitive components — embeddings, the output/unembedding head, MoE router logits, normalization layers — kept in bf16/fp32 per [[Concept - Post-Training Quantization Formats|the same sensitive-layer logic used at inference time]]. The result reached training loss and downstream quality close to a bf16 baseline, while capturing fp8's throughput and memory advantages across the bulk of the compute. See [[Breakdown - DeepSeek-V3 Training]] for the full system-level walkthrough of how this composed with their MoE and pipeline design.

## Failure modes

- **Amax spike blowing the scale**: a single outlier value — typically near an attention or MoE-router logit, which is exactly where [[Concept - Training Stability and Loss Spikes|loss spikes]] also originate — pushes a tensor's true max above what the current (especially delayed) scale factor can represent, saturating or clipping values before the scale catches up. This shows up as silent accuracy loss at best and NaN propagation at worst.
- **Reduced-precision accumulation error compounding over depth**: without an explicit fp32 accumulation fix, small per-GEMM rounding errors from the tensor core's native fp8 accumulator compound across dozens of transformer layers, producing a *slow* divergence from a bf16 reference loss curve rather than a single sharp spike — much harder to catch in a dashboard that only watches for spikes.
- **Sensitive layers need to stay out of fp8**: embeddings, the final output projection, and often the first/last transformer blocks have activation distributions that don't tolerate fp8's coarse 3-bit mantissa; keeping these in bf16/fp32 is not an optimization, it's a correctness requirement learned the hard way.
- **Calibration drift between forward and backward**: E4M3 activations and E5M2 gradients get their scale factors computed at different points in the step, and if the backward-pass scale (computed from a stale or delayed amax) doesn't track the true gradient distribution that emerges after the forward pass ran, gradients systematically underflow to zero (killing learning silently) or overflow (triggering the amax-spike failure above).

## The non-obvious

FP8 pretraining spent years as "theoretically attractive, practically unstable" folklore precisely because early attempts treated it as a format swap — the same recipe as bf16 but with fewer bits — rather than recognizing that a smaller dynamic range demands finer-grained scaling and explicit accumulation discipline. The generalizable lesson from DeepSeek-V3's success: precision problems in low-bit training are almost always solved by improving *scaling granularity* (smaller tiles, more frequent recalibration), not by retreating more of the network back into high precision — the latter is the easy fix that gives up most of the speed and memory win you were chasing in the first place.

## Connections
- [[Concept - Mixed Precision Training]] — fp8 training is the next rung down from bf16 on the same precision ladder, reusing its master-weight and selective-fp32 patterns.
- [[Concept - Floating Point for Deep Learning]] — the exponent/mantissa tradeoff that defines E4M3 vs E5M2 is the same tradeoff explained there for fp16/bf16.
- [[Concept - Tensor Cores]] — the ~2x fp8-vs-bf16 throughput advantage, and the reduced-precision native accumulator that fp8 training has to work around, are both properties of the tensor-core hardware itself.
- [[Breakdown - DeepSeek-V3 Training]] — the full system-level account of the run that proved fp8 pretraining viable at frontier scale.
- [[Concept - Post-Training Quantization Formats]] — the sensitive-layer-stays-high-precision logic used here mirrors the same practice applied to fp8/int8 inference quantization.
- [[Concept - Training Stability and Loss Spikes]] — the same attention/router-logit outliers that trigger loss spikes are exactly what blows fp8's per-tensor scale factors.
- [[Concept - FP8 and Low-Precision Hardware Formats]] — the hardware-level treatment of what Hopper/Blackwell tensor cores actually do with fp8 inputs and accumulators.
- [[Reference - Floating Point Formats]] — the lookup table of exponent/mantissa bit layouts across every format referenced here.

## Sources
- Micikevicius et al. (2022) — "FP8 Formats for Deep Learning" — defines the E4M3/E5M2 formats and the OCP FP8 specification.
- DeepSeek-AI (2024) — DeepSeek-V3 Technical Report — the first production-scale fp8-pretrained frontier LLM, introducing fine-grained per-tile/per-block scaling and the fp32 accumulation-path fix for Hopper's fp8 GEMM.
