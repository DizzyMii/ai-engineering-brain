---
tags: [reference, domain/foundations, level/core]
aliases: [IEEE 754, float format comparison, fp32 fp16 bf16 fp8 comparison]
summary: "Lookup table of bit layout, dynamic range, precision, and memory cost for every floating-point format used in modern deep learning."
---

# Reference - Floating Point Formats

A lookup table for mid-task use. The mechanism, and why bf16 beat fp16 for training, lives in [[Concept - Floating Point for Deep Learning]]. Layouts are IEEE-754 style unless noted. The DL-specific formats (tf32, fp8, fp4) follow vendor/OCP conventions, not a formal IEEE standard.

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

¹ Machine epsilon = $2^{-\text{mantissa bits}}$, the gap between 1.0 and the next representable value. Don't confuse it with the smallest representable number, which comes from the exponent field and subnormals (see [[Concept - Subnormal Numbers and Gradual Underflow]]).
² tf32 keeps fp32's 8-bit exponent (so the range is identical) and truncates to 10 mantissa bits. Tensor cores compute it from fp32-stored operands; it never exists in memory as a separate 19-bit type.
³ fp4 e2m1 is the microscaling (MX) convention (OCP Microscaling spec); values always come with a shared block exponent (see below), since 1 mantissa bit on its own is nearly useless.

## Exact-integer range

Largest $N$ such that every integer $0 \ldots N$ is exactly representable. Past this the mantissa bits run out:

| Format | Exact integers up to |
|---|---|
| fp16 | 2,048 |
| bf16 | 256 |
| fp32 | $2^{24}$ = 16,777,216 |
| fp64 | $2^{53}$ ≈ 9.007e15 |

So token counts, position indices and large loop counters go in int or fp32. bf16 silently starts skipping integers past 256, and a counter that looks like it should "just work" gets corrupted.

## Rounding and scaling

- **Default:** round-to-nearest-even (the IEEE default; ties go to the even last bit), for storage and for tensor-core accumulation.
- **Stochastic rounding:** rounds up or down with probability proportional to the distance from each neighbor, so the *expected* rounding error is zero instead of biased low. Used for low-precision weight updates, where round-to-nearest would silently zero out a long run of small updates.
- **Loss scaling (fp16 only):** multiply the loss by a constant, typically $2^{10}$–$2^{16}$, before backprop so small gradients land inside fp16's representable band. Mechanism and history: [[Lore - Loss Scaling and the fp16 Underflow Crisis]].
- **Block scaling (fp8/fp4):** per-tensor scaling gives a whole tensor one scale factor. Microscaling (mxfp) gives each block of 32 elements a shared exponent. You pay a little memory for the extra scale bytes and get much better dynamic range coverage than per-tensor scaling at 4-bit precision.

## Memory cost per value

| Format | Bytes | Relative to fp32 |
|---|---|---|
| fp32 | 4 | 1x |
| fp16 / bf16 | 2 | 0.5x |
| fp8 | 1 | 0.25x |
| fp4 (packed) | 0.5 | 0.125x |

[[Reference - Memory Math for Transformers]] rolls these per-value costs up into parameter, optimizer-state and activation memory totals.

Status (as of 2026): bf16 is the default training dtype on GPU and TPU. fp8 (e4m3/e5m2) is mainstream for training and inference on Hopper-class hardware. fp4/mxfp formats are arriving on Blackwell-class hardware and are still mainly an inference/quantization format, not a training default.

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
