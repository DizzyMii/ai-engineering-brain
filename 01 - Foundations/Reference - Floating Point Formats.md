---
tags: [reference, domain/foundations, level/core]
aliases: [IEEE 754, float format comparison, fp32 fp16 bf16 fp8 comparison]
summary: "Lookup table of bit layout, dynamic range, precision, and memory cost for every floating-point format used in modern deep learning."
---

# Reference - Floating Point Formats

Mid-task lookup. For the mechanism and why bf16 beat fp16 for training, see [[Concept - Floating Point for Deep Learning]]. All values are IEEE-754 style layouts unless noted; DL-specific formats (tf32, fp8, fp4) follow vendor/OCP conventions rather than a formal IEEE standard.

## Bit layout and range/precision

| Format | Sign | Exp bits | Mantissa bits | Bias | Max finite | Min normal | Min subnormal | Machine epsilon¹ | ~Decimal digits | Bytes/value |
|---|---|---|---|---|---|---|---|---|---|---|
| fp64 | 1 | 11 | 52 | 1023 | ~1.80e308 | ~2.23e-308 | ~4.94e-324 | ~2.22e-16 | ~15.9 | 8 |
| fp32 | 1 | 8 | 23 | 127 | ~3.40e38 | ~1.18e-38 | ~1.40e-45 | ~1.19e-7 | ~7.2 | 4 |
| tf32² | 1 | 8 | 10 | 127 | ~3.40e38 | ~1.18e-38 | — | ~9.77e-4 | ~3 | 4 (stored) |
| fp16 | 1 | 5 | 10 | 15 | 65,504 | ~6.10e-5 | ~5.96e-8 | ~9.77e-4 | ~3.3 | 2 |
| bf16 | 1 | 8 | 7 | 127 | ~3.39e38 | ~1.18e-38 | ~9.18e-41 | ~7.81e-3 | ~2-3 | 2 |
| fp8 e4m3 | 1 | 4 | 3 | 7 | 448 | ~1.56e-2 | ~1.95e-3 | 0.125 | ~1 | 1 |
| fp8 e5m2 | 1 | 5 | 2 | 15 | 57,344 | ~6.10e-5 | ~1.53e-5 | 0.25 | ~0.7 | 1 |
| fp4 e2m1³ | 1 | 2 | 1 | 1 | 6 | 1 | 0.5 | 0.5 | <1 | 0.5 (packed) |

¹ Machine epsilon = $2^{-\text{mantissa bits}}$, the gap between 1.0 and the next representable value — not the same as the smallest representable number (which is set by the exponent field and subnormals; see [[Concept - Subnormal Numbers and Gradual Underflow]]).
² tf32 keeps fp32's 8-bit exponent (hence identical range) but truncates to 10 mantissa bits; it is computed on tensor cores from fp32-stored operands, not stored as a distinct 19-bit type in memory.
³ fp4 e2m1 is the microscaling (MX) convention (OCP Microscaling spec); values are always used with a shared block exponent (see below) since 1 mantissa bit alone is nearly useless.

## Exact-integer range

The largest $N$ such that every integer $0 \ldots N$ is exactly representable (mantissa bits exhausted beyond this):

| Format | Exact integers up to |
|---|---|
| fp16 | 2,048 |
| bf16 | 256 |
| fp32 | $2^{24}$ = 16,777,216 |
| fp64 | $2^{53}$ ≈ 9.007e15 |

This is why token counts, position indices, and large loop counters belong in int or fp32 — bf16 silently starts skipping integers past 256, corrupting counters that look like they should "just work."

## Rounding and scaling

- **Default:** round-to-nearest-even (IEEE default; ties round to the even last bit) for both storage and tensor-core accumulation.
- **Stochastic rounding:** rounds up or down with probability proportional to distance from each neighbor, so the *expected* rounding error is zero rather than systematically biased low; used for low-precision weight updates where round-to-nearest would silently zero out a long run of small updates.
- **Loss scaling (fp16 only):** multiply the loss by a constant, typically $2^{10}$–$2^{16}$, before backprop to shift small gradients up into fp16's representable band; see [[Lore - Loss Scaling and the fp16 Underflow Crisis]] for the full mechanism and history.
- **Block scaling (fp8/fp4):** per-tensor scaling assigns one scale factor to an entire tensor; microscaling (mxfp) assigns one shared exponent per block of 32 elements, trading a small amount of memory overhead (extra scale bytes) for much better dynamic range coverage than per-tensor scaling at 4-bit precision.

## Memory cost per value

| Format | Bytes | Relative to fp32 |
|---|---|---|
| fp32 | 4 | 1x |
| fp16 / bf16 | 2 | 0.5x |
| fp8 | 1 | 0.25x |
| fp4 (packed) | 0.5 | 0.125x |

Cross-reference [[Reference - Memory Math for Transformers]] for how these per-value costs roll up into parameter, optimizer-state, and activation memory totals.

**Date-stamped (as of 2026):** bf16 is the default training dtype on GPU and TPU; fp8 (e4m3/e5m2) is mainstream for training and inference on Hopper-class hardware; fp4/mxfp formats are arriving on Blackwell-class hardware and remain primarily an inference/quantization format rather than a training default.

## Connections

- [[Concept - Floating Point for Deep Learning]] — the mechanism and narrative this table is the lookup companion to: why the range-vs-precision tradeoff exists and why bf16 won for training.
- [[Concept - The Memory Wall]] — the hardware-bandwidth pressure that makes every byte in this table's memory-cost column a first-order design decision, not an afterthought.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the min-subnormal column's origin and why flush-to-zero silently discards that range on real hardware.
- [[Reference - Memory Math for Transformers]] — turns the per-value byte costs here into full model/optimizer/activation memory budgets.
- [[Concept - Post-Training Quantization Formats]] — the INT8/INT4 integer counterparts to fp8/fp4, and when integer beats float for a given tensor.
- [[Concept - Tensor Cores]] — the hardware units that consume bf16/fp16/fp8 inputs and accumulate in fp32, which is why the accumulation dtype isn't a row in this table.
- [[Concept - Mixed Precision Training]] — the practical recipe (which tensors get which dtype) that this format catalog feeds into.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the historical reason the loss-scaling row above exists: fp16's narrow range forced it, and bf16's wider exponent mostly retired it.

## Sources

- IEEE 754-2019 — *IEEE Standard for Floating-Point Arithmetic.* Defines fp16/fp32/fp64 bit layouts, rounding modes, and subnormal behavior.
- Kalamkar et al. (2019) — *A Study of BFLOAT16 for Deep Learning Training.* bf16 layout and the empirical case for range over precision.
- Micikevicius et al. (2022) — *FP8 Formats for Deep Learning.* Defines the e4m3/e5m2 split (precision vs. range) adopted by NVIDIA Hopper and the OCP FP8 spec.
- Open Compute Project (2023) — *OCP Microscaling Formats (MX) Specification.* Defines fp4 e2m1/e2m3 variants and the shared-block-exponent scaling scheme.
