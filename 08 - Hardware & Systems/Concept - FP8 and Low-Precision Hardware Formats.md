---
tags: [concept, domain/hardware-systems, level/frontier]
aliases: [FP8, FP4, E4M3, E5M2, E2M1, MXFP8, MXFP4, microscaling, MX format]
summary: "The 8-bit and 4-bit floating-point formats modern tensor cores execute natively, and the block-scaling machinery that keeps them from overflowing or underflowing."
---
> Every halving of numeric precision roughly doubles a tensor core's throughput — [[Concept - Tensor Cores|H100's FP8 path runs at ~1979 TFLOP/s versus ~989 for BF16]], and Blackwell's FP4 doubles again. But 8 bits (and especially 4 bits) cannot represent a tensor's dynamic range the way FP32 or even FP16 can, so FP8/FP4 are not just "BF16 but smaller" — they are formats that only work paired with hardware-managed scaling, and getting that scaling wrong is a silent-accuracy-loss failure mode, not a crash.

## The mechanism

**FP8 has two variants that split the exponent/mantissa budget differently**, and the split is a deliberate range-vs-precision tradeoff, not an arbitrary choice:

| Format | Sign | Exponent | Mantissa | Range | Typical use |
|---|---|---|---|---|---|
| E4M3 | 1 | 4 | 3 | ~±448 | weights, activations (narrower range, more precision) |
| E5M2 | 1 | 5 | 2 | wider (like FP16's range) | gradients (need range, tolerate less precision) |

E4M3's extra mantissa bit gives it roughly 2x the precision of E5M2 at any given magnitude, at the cost of a much smaller representable range (no `inf`, limited exponent). E5M2 mirrors FP16's exponent width, giving it FP16-like dynamic range but only 2 mantissa bits — appropriate for gradients, which can span many orders of magnitude during training but don't need much precision per value to still convey useful direction. This is the same shape of tradeoff [[Reference - Floating Point Formats|BF16 makes against FP16]] one level up: more exponent bits buys range, more mantissa bits buys precision, and you cannot have both in a fixed budget.

**Why FP8 needs explicit scaling.** E4M3's ~±448 range is far narrower than the activation magnitudes a transformer actually produces — outlier activations, attention logits before softmax, and LayerNorm outputs routinely exceed this range or underflow well above zero relative to it. NVIDIA's Transformer Engine handles this with **delayed scaling**: it tracks a rolling history of each tensor's recent absolute maximum (amax) and derives a per-tensor scale factor from that history each step, rather than computing a fresh scale from the current tensor (which would require an extra full pass over the data before the matmul could even start). The tensor is multiplied by this scale before quantizing to FP8 and divided back out after the matmul accumulates in higher precision — mechanically the same idea as [[Concept - Mixed Precision Training|loss scaling in fp16 training]], just applied per-tensor, per-step, and automatically.

**Microscaling (MX) goes finer-grained.** Instead of one scale factor for an entire tensor, the OCP Microscaling (MX) standard shares one exponent per small block of elements — typically 32 — giving **MXFP8**, **MXFP6**, and **MXFP4** their name. A block-local scale factor tracks that block's own dynamic range instead of the whole tensor's, which matters enormously once you go to 4 bits: a single per-tensor scale for FP4 would force every value in the tensor to compete for the same narrow representable window, and outlier elements elsewhere in the tensor would either clip or force everything else to underflow. Block scaling contains the outlier problem to just the block it lives in. Blackwell is the first NVIDIA generation with native MX hardware support.

**FP4 on Blackwell.** The format is E2M1 — 2 exponent bits, 1 mantissa bit — paired with an MX block scale, giving roughly 2x FP8's throughput again. With only 1 mantissa bit, each FP4 value can represent essentially {0, ±0.5, ±1, ±1.5, ±2, ±3, ±4, ±6} times its block's scale — a genuinely coarse quantization grid, which is why FP4 sits closer to the edge of acceptable accuracy loss than FP8 does and needs real calibration, not just "turn it on."

$$
\text{throughput}_{\text{FP4}} \approx 2\times \text{throughput}_{\text{FP8}} \approx 4\times \text{throughput}_{\text{BF16}}
$$

This FLOP-doubling-per-bit-halving pattern is the direct hardware payoff: each generation of [[Concept - Tensor Cores|tensor core]] packs more MACs into the same die area when operands are half the width, since a MAC unit's transistor count scales roughly with operand bit-width squared for the multiply.

## In practice

FP8 shows up in two very different places with different risk profiles. In **training**, it's used for the forward/backward matmuls (QKV projections, MLP layers) while keeping the optimizer state, master weights, and often the attention/softmax computation in higher precision — the same selective-precision discipline [[Concept - Mixed Precision Training]] established for BF16, just pushed one format lower. **DeepSeek-V3's training run** (2024) is the clearest large-scale public proof point: it pretrained with FP8 for the bulk of its matmuls at hundreds-of-billions-of-parameters scale, demonstrating FP8 pretraining is viable outside a lab demo — see [[Breakdown - DeepSeek-V3 Training]] for the specifics of how they managed the scaling and which layers stayed higher-precision.

In **inference**, FP8/FP4 weights and KV cache directly cut memory footprint (1 byte/param for FP8 vs 2 for FP16, further for FP4) and raise achievable batch size and throughput, which is why [[Concept - Post-Training Quantization Formats|post-training quantization]] pipelines target these formats as a deployment endpoint rather than just a training-time optimization. Per [[Reference - Memory Math for Transformers]], moving a 70B model's weights from fp16 (2 bytes/param, ~140 GB) to fp8 (1 byte/param, ~70 GB) can be the difference between needing two GPUs and fitting on one.

## Failure modes

- **Outlier features breaking per-tensor scaling.** A small number of activation dimensions in transformers routinely reach magnitudes 10-100x the typical value (the same phenomenon documented in the LLM.int8 line of work) — see [[Concept - Massive Activations and Outlier Features]]. A single per-tensor scale factor forces a choice: scale for the outliers (and waste most of the representable range on values that never get near it) or scale for the typical values (and clip the outliers to the format's max). Symptom: a sudden, unexplained loss spike or NaN partway through an otherwise-stable FP8 training run. Detection: monitor per-tensor amax history for sudden jumps and watch for saturation (values pinned at the format's max magnitude) rather than a smooth distribution.
- **FP4 calibration failure is silent, not a crash.** Because FP4's quantization grid is so coarse, a badly calibrated block scale doesn't error out — it just produces measurably worse outputs (higher perplexity, degraded downstream task accuracy) with no signal in the loss curve or logs. Detection requires an actual eval suite run before and after quantization, not just "did training complete."
- **Accumulating in low precision instead of high.** Tensor cores accumulate FP8×FP8 products in FP32 internally by design specifically to prevent rounding error from compounding across the reduction dimension of a matmul; custom kernels or serving code that downcasts the accumulator early reproduce instability that looks like a training bug but is a numerics bug — see [[Concept - Tensor Cores]] for the accumulation-precision discipline this depends on.
- **Applying uniform precision across all layers.** The attention/softmax path and the final logit layer are disproportionately sensitive to precision loss (softmax amplifies small errors, and logits feed directly into the loss); production FP8 recipes keep these in BF16/FP32 while the bulk of the matmuls run FP8 — treating FP8 as an all-or-nothing switch rather than a per-layer decision is a common early mistake.

## The non-obvious

The real engineering content of "using FP8" is almost entirely in the scaling machinery, not the format itself — a raw 8-bit float type has existed as a concept for a long time, but it was useless for deep learning until delayed scaling and microscaling made it practical to keep values inside the format's narrow representable range without a full extra pass over every tensor every step. This means the honest comparison between FP8 hardware generations isn't "how many FLOPs" but "how good is the automatic scaling" — Blackwell's jump to block-level MX scaling is arguably a bigger accuracy win than its raw FLOP increase, because it directly attacks the outlier-clipping problem that made per-tensor FP8 scaling fragile on some architectures. Folklore, weakly sourced: several teams that adopted early Hopper FP8 training report needing to keep more layers in BF16 than the reference recipes suggested, because outlier severity varies by architecture (particularly around normalization placement) in ways that aren't well characterized publicly — treat any team's "we trained fully in FP8" claim as architecture-specific until proven otherwise on your own model.

## Connections
- [[Concept - Tensor Cores]] — the hardware units that execute FP8/FP4 matmuls natively and accumulate in higher precision to contain rounding error.
- [[Concept - Floating Point for Deep Learning]] — the general exponent/mantissa tradeoff framework FP8's E4M3-vs-E5M2 split is a specific instance of.
- [[Reference - Floating Point Formats]] — the lookup table for FP16/BF16/FP32 bit layouts that this note's E4M3/E5M2 comparison extends one precision tier lower.
- [[Concept - Mixed Precision Training]] — the broader training discipline (selective precision per operation, loss/amax scaling) that FP8 training extends one format lower.
- [[Concept - Post-Training Quantization Formats]] — the inference-side quantization pipelines that target FP8/FP4 as a deployment format for weights and KV cache.
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — the specific silicon (Transformer Engine, MX hardware) that implements the scaling machinery this note describes.
- [[Reference - Memory Math for Transformers]] — the concrete byte-per-parameter arithmetic showing what FP8/FP4 buys in memory footprint.
- [[Breakdown - DeepSeek-V3 Training]] — the largest public proof point of FP8 used for pretraining at scale, not just inference.
- [[Concept - Massive Activations and Outlier Features]] — the root cause of FP8/FP4's central failure mode: a small number of extreme-magnitude activations breaking coarse scaling.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the historical precedent: the field already solved a version of this problem for fp16 gradients, and FP8's amax-scaling machinery is a direct descendant of that lesson.

## Sources
- Micikevicius, P. et al. (NVIDIA, 2022) — "FP8 Formats for Deep Learning" — E4M3/E5M2 definitions and the delayed-scaling recipe.
- Open Compute Project (2023) — "OCP Microscaling Formats (MX) Specification" — the MXFP8/MXFP6/MXFP4 block-scaling standard.
- DeepSeek-AI (2024) — DeepSeek-V3 technical report — large-scale FP8 pretraining as a public proof point, including which components were kept in higher precision.
- Dettmers, T. et al. (2022) — "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale" — the outlier-feature phenomenon that motivates block/mixed-precision scaling.
