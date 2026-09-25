---
tags: [concept, domain/hardware-systems, level/frontier]
aliases: [FP8, FP4, E4M3, E5M2, E2M1, MXFP8, MXFP4, microscaling, MX format]
summary: "The 8-bit and 4-bit floating-point formats modern tensor cores execute natively, and the block-scaling machinery that keeps them from overflowing or underflowing."
---
> Every halving of numeric precision roughly doubles a tensor core's throughput — [[Concept - Tensor Cores|H100's FP8 path runs at ~1979 TFLOP/s versus ~989 for BF16]], and Blackwell's FP4 doubles it again. But 8 bits (4 bits even more so) can't hold a tensor's dynamic range the way FP32 or even FP16 can. FP8/FP4 only work paired with hardware-managed scaling, which makes them more than "BF16 but smaller." Get the scaling wrong and you lose accuracy silently; nothing crashes.

## The mechanism

**FP8 comes in two variants that split the exponent/mantissa budget differently.** The split is a deliberate range-vs-precision trade:

| Format | Sign | Exponent | Mantissa | Range | Typical use |
|---|---|---|---|---|---|
| E4M3 | 1 | 4 | 3 | ~±448 | weights, activations (narrower range, more precision) |
| E5M2 | 1 | 5 | 2 | wider (like FP16's range) | gradients (need range, tolerate less precision) |

E4M3's extra mantissa bit gives it roughly 2x the precision of E5M2 at any magnitude, paid for with a much smaller representable range (no `inf`, limited exponent). E5M2 copies FP16's exponent width, so it has FP16-like dynamic range but only 2 mantissa bits. That suits gradients, which can span many orders of magnitude during training but still point in a useful direction without much per-value precision. It's the same trade [[Reference - Floating Point Formats|BF16 makes against FP16]] one level up: exponent bits buy range, mantissa bits buy precision, and a fixed budget can't have both.

**Why FP8 needs explicit scaling.** E4M3's ~±448 range is far narrower than the activation magnitudes a transformer produces. Outlier activations, pre-softmax attention logits and LayerNorm outputs routinely exceed it or underflow well above zero relative to it. NVIDIA's Transformer Engine handles this with **delayed scaling**. It keeps a rolling history of each tensor's recent absolute maximum (amax) and derives a per-tensor scale factor from that history each step. Computing a fresh scale from the current tensor would need an extra full pass over the data before the matmul could start. The tensor is multiplied by the scale before quantizing to FP8 and divided back out after the matmul accumulates in higher precision. Mechanically it's [[Concept - Mixed Precision Training|loss scaling in fp16 training]], applied per tensor, per step, automatically.

**Microscaling (MX) goes finer.** The OCP Microscaling (MX) standard shares one exponent per small block of elements, typically 32, instead of one scale for a whole tensor. That's where **MXFP8**, **MXFP6**, and **MXFP4** get their names. A block-local scale tracks that block's dynamic range, not the tensor's, and at 4 bits that matters enormously. With a single per-tensor scale, every FP4 value in the tensor competes for the same narrow window, and outliers anywhere in the tensor either clip or push everything else into underflow. Block scaling confines the outlier problem to the block it lives in. Blackwell is the first NVIDIA generation with native MX hardware support.

**FP4 on Blackwell.** The format is E2M1 (2 exponent bits, 1 mantissa bit) with an MX block scale, for roughly 2x FP8's throughput again. With 1 mantissa bit, an FP4 value can represent essentially {0, ±0.5, ±1, ±1.5, ±2, ±3, ±4, ±6} times its block's scale. That grid is coarse, so FP4 sits closer to the edge of acceptable accuracy loss than FP8 and needs real calibration. You can't just turn it on.

$$
\text{throughput}_{\text{FP4}} \approx 2\times \text{throughput}_{\text{FP8}} \approx 4\times \text{throughput}_{\text{BF16}}
$$

The hardware payoff is FLOPs doubling each time bits halve. A [[Concept - Tensor Cores|tensor core]] fits more MACs into the same die area when operands are half as wide, because a MAC unit's transistor count for the multiply scales roughly with operand bit-width squared.

## In practice

FP8 shows up in two places with different risk profiles. In **training** it runs the forward/backward matmuls (QKV projections, MLP layers) while optimizer state, master weights and often the attention/softmax computation stay in higher precision. That's the selective-precision discipline [[Concept - Mixed Precision Training]] set up for BF16, pushed one format lower. **DeepSeek-V3's training run** (2024) is the clearest large-scale public proof: it pretrained with FP8 for most of its matmuls at hundreds of billions of parameters, showing FP8 pretraining works outside a lab demo. [[Breakdown - DeepSeek-V3 Training]] has how they managed scaling and which layers stayed at higher precision.

In **inference**, FP8/FP4 weights and KV cache cut memory footprint (1 byte/param for FP8 vs 2 for FP16, less for FP4) and raise achievable batch size and throughput. [[Concept - Post-Training Quantization Formats|Post-training quantization]] pipelines target these formats as a deployment endpoint for that reason, beyond any training-time use. Per [[Reference - Memory Math for Transformers]], moving a 70B model's weights from fp16 (2 bytes/param, ~140 GB) to fp8 (1 byte/param, ~70 GB) can be the difference between needing two GPUs and fitting on one.

## Failure modes

- **Outlier features break per-tensor scaling.** A few activation dimensions in transformers routinely reach 10-100x the typical magnitude (the phenomenon documented in the LLM.int8 line of work; see [[Concept - Massive Activations and Outlier Features]]). One per-tensor scale forces a choice. Scale for the outliers and most of the representable range is wasted on values that never get near it; scale for typical values and the outliers clip to the format's max. Symptom: a sudden, unexplained loss spike or NaN partway through an otherwise stable FP8 run. Detection: watch per-tensor amax history for sudden jumps, and look for saturation (values pinned at the format's max magnitude) where you'd expect a smooth distribution.
- **FP4 calibration failure is silent.** FP4's grid is so coarse that a badly calibrated block scale doesn't error. It produces measurably worse outputs (higher perplexity, lower downstream accuracy) with no sign in the loss curve or logs. You need a real eval suite run before and after quantization; "did training complete" tells you nothing.
- **Accumulating in low precision.** Tensor cores accumulate FP8×FP8 products in FP32 internally by design, so rounding error doesn't compound across a matmul's reduction dimension. Custom kernels or serving code that downcast the accumulator early bring back an instability that looks like a training bug and is a numerics bug. [[Concept - Tensor Cores]] covers the accumulation-precision discipline this relies on.
- **Uniform precision across all layers.** The attention/softmax path and the final logit layer are disproportionately sensitive (softmax amplifies small errors, and logits feed straight into the loss). Production FP8 recipes keep them in BF16/FP32 while most matmuls run in FP8. Treating FP8 as an all-or-nothing switch instead of a per-layer decision is a common early mistake.

## The non-obvious

Nearly all the engineering in "using FP8" is in the scaling machinery. A raw 8-bit float has existed as a concept for a long time and was useless for deep learning until delayed scaling and microscaling kept values inside the format's narrow range without an extra full pass over every tensor every step. So the fair comparison between FP8 hardware generations is how good the automatic scaling is, more than how many FLOPs they have. Blackwell's move to block-level MX scaling is arguably a bigger accuracy win than its raw FLOP increase, because it goes after the outlier-clipping problem that made per-tensor FP8 scaling fragile on some architectures.

Folklore, weakly sourced: several teams that adopted early Hopper FP8 training report keeping more layers in BF16 than the reference recipes suggested. Outlier severity varies by architecture (especially around normalization placement) in ways that aren't well characterized publicly. Treat any "we trained fully in FP8" claim as architecture-specific until it holds on your own model.

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
