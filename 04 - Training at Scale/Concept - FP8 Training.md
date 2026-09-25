---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [FP8 pretraining, E4M3, E5M2, 8-bit floating point training]
summary: "Training LLMs in 8-bit floating point — the E4M3/E5M2 formats, why scaling is the real problem, and how DeepSeek-V3 made it production-viable."
---

# Concept - FP8 Training

> **One-paragraph hook:** Hopper and Blackwell tensor cores run fp8 matmuls at roughly 2x the throughput of [[Concept - Mixed Precision Training|bf16]] with half the memory footprint. For years, though, fp8 pretraining was folklore-unstable: teams that ported bf16 recipes naively into 8 bits got divergent or quietly worse runs. DeepSeek-V3 (2024) showed it works at frontier scale, with 671B parameters, mostly-fp8 GEMMs and near-bf16 quality at a fraction of the compute cost. What fixed it was scaling discipline. The format was never the issue.

## The mechanism

FP8 comes in two formats standardized by the Open Compute Project (Micikevicius et al. 2022). **E4M3** has 1 sign bit, 4 exponent bits and 3 mantissa bits, with a dynamic range of roughly ±448. **E5M2** has 1 sign, 5 exponent and 2 mantissa bits: more range, less precision, the same tradeoff as fp16 vs bf16 in [[Concept - Mixed Precision Training]]. Convention is E4M3 for forward-pass activations and weights, which layernorm/softmax have already normalized and which don't need much range. Gradients get E5M2, since their magnitude can vary by orders of magnitude across layers and they need the extra exponent bits more than the extra mantissa bit.

The hard part is fp8's tiny dynamic range: roughly 2^-9 to 448 for E4M3, against bf16's ~10^±38. Anything outside it underflows to zero or overflows to infinity, so *scaling* (picking the per-tensor multiplier that maps real values into fp8's representable range) is the whole game. Two strategies are in production use:

- **Delayed scaling** reuses a rolling history of past steps' amax (absolute max) values to set this step's scale factor. It's cheap, but slow to react to a sudden spike.
- **Current-tensor (just-in-time) scaling** computes the amax of the actual tensor before quantizing it. More accurate, at the cost of an extra reduction pass.

DeepSeek-V3 added **fine-grained scaling**. In place of one scale factor per tensor, it uses one per 1×128 tile for activations and one per 128×128 block for weights. A single outlier (common near attention or MoE router logits) then wrecks the scale for its own small tile only, and the rest of the tensor keeps its precision.

Some things stay in high precision on purpose: the fp32 master weights and optimizer moments (the accumulate/update step never runs in 8-bit, same as in [[Concept - Mixed Precision Training]]), layernorm statistics and softmax. Most important, **the fp8×fp8 matmul must accumulate its partial sums in fp32**, and that doesn't happen automatically. Hopper tensor cores' native fp8 GEMM path accumulates internally at reduced precision, so summing hundreds of fp8 products (the inner dimension of a large matmul) loses precision right where you'd expect a high-precision accumulator to protect you. DeepSeek-V3 periodically promotes partial sums out to an fp32 accumulation path on CUDA cores instead of trusting the tensor core's native accumulator end to end.

## In practice

DeepSeek-V3 (DeepSeek-AI, 2024) is, per the inventory, the first production-scale fp8-pretrained LLM. It has 671B total parameters (37B active, MoE) and trained for roughly 2.788M H800 GPU-hours. Most GEMMs ran in fp8. Sensitive components (embeddings, the output/unembedding head, MoE router logits, normalization layers) stayed in bf16/fp32, following [[Concept - Post-Training Quantization Formats|the same sensitive-layer logic used at inference time]]. Training loss and downstream quality came out close to a bf16 baseline, while the bulk of the compute got fp8's throughput and memory advantages. [[Breakdown - DeepSeek-V3 Training]] walks through how this fit with their MoE and pipeline design.

## Failure modes

- **Amax spike blowing the scale.** One outlier pushes a tensor's true max above what the current scale factor can represent (delayed scaling especially), so values saturate or clip before the scale catches up. These outliers typically sit near attention or MoE-router logits, the same place [[Concept - Training Stability and Loss Spikes|loss spikes]] start. Best case is silent accuracy loss; worst case is NaN propagation.
- **Reduced-precision accumulation error compounding over depth.** Without an explicit fp32 accumulation fix, small per-GEMM rounding errors from the tensor core's native fp8 accumulator add up across dozens of transformer layers. The result is a *slow* divergence from a bf16 reference loss curve, not a sharp spike, which a dashboard that only watches for spikes will miss.
- **Sensitive layers need to stay out of fp8.** Embeddings, the final output projection, and often the first and last transformer blocks have activation distributions that can't tolerate fp8's coarse 3-bit mantissa. Keeping them in bf16/fp32 is a correctness requirement, learned the hard way.
- **Calibration drift between forward and backward.** E4M3 activations and E5M2 gradients get their scale factors at different points in the step. If the backward-pass scale (from a stale or delayed amax) doesn't track the gradient distribution that actually emerges after the forward pass, gradients systematically underflow to zero, which kills learning silently, or overflow into the amax-spike failure above.

## The non-obvious

FP8 pretraining sat for years in "theoretically attractive, practically unstable" territory because early attempts treated it as a format swap: the bf16 recipe with fewer bits. A smaller dynamic range needs finer-grained scaling and explicit accumulation discipline. The lesson I'd take from DeepSeek-V3 is that precision problems in low-bit training are almost always solved by better *scaling granularity* (smaller tiles, more frequent recalibration). Pushing more of the network back into high precision is the easy fix, and it gives up most of the speed and memory win you wanted in the first place.

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
