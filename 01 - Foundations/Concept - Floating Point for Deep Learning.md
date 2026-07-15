---
tags: [concept, domain/foundations, level/core]
aliases: [IEEE 754, fp16, bf16, fp8, floating-point arithmetic]
summary: "How IEEE-754 formats trade exponent range against mantissa precision, and why bf16's fp32-range exponent won deep learning training."
---

# Concept - Floating Point for Deep Learning

> **One-paragraph hook:** Every tensor you train or serve is a bit pattern in some IEEE-754-style format, and the format choice is a first-order training-stability decision, not an implementation detail. The entire modern precision stack — bf16 training, fp32 accumulation, fp8 inference — falls out of one tradeoff: exponent bits buy dynamic range, mantissa bits buy relative precision, and deep learning (where gradients span ten orders of magnitude but tolerate noise) wants range. Most NaN losses, silent training stalls, and "why is my sum wrong" bugs are this note's content wearing a disguise.

## The mechanism

An IEEE-754 float encodes

$$x = (-1)^{s} \times 1.\underbrace{b_1 b_2 \ldots b_m}_{\text{mantissa}} \times 2^{\,e - \text{bias}}$$

with $s$ the sign bit, $e$ the exponent field, and an implicit leading 1 on the mantissa (dropped for subnormals — see [[Concept - Subnormal Numbers and Gradual Underflow]]). The split of the bit budget is the whole story:

- **Exponent bits set dynamic range.** 8 exponent bits (bias 127) span roughly $10^{-38}$ to $3.4 \times 10^{38}$; 5 bits (bias 15) span only $6.1\times10^{-5}$ to $65504$.
- **Mantissa bits set relative precision.** Machine epsilon — the gap between 1.0 and the next representable value — is $\varepsilon \approx 2^{-m}$. fp32 (1/8/23): $\varepsilon \approx 1.19\times10^{-7}$, ~7.2 decimal digits. fp16 (1/5/10): $\varepsilon \approx 9.8\times10^{-4}$, ~3.3 digits. bf16 (1/8/7): $\varepsilon \approx 7.8\times10^{-3}$, ~2–3 digits.

**Precision is relative, not absolute.** The spacing between representable numbers (the ulp) scales with magnitude: near 1.0 a bf16 step is ~0.0078, near 1024 it is 8. So adding a small number to a large one can lose the small one entirely — *swamping*: in bf16, $1024 + 1 = 1024$ exactly. This is why running sums, means, and variances need care ([[Gotchas - Numerical Stability]]) and why gradient clipping by global L2 norm is computed in fp32 ([[Concept - Vector Norms and Distances]]).

**The tradeoff that decided the format war.** Activations and gradients in a deep net span many orders of magnitude across layers and across training. Clipping the *range* is catastrophic — overflow gives inf, underflow gives an exact 0 and the gradient signal is gone. Losing *mantissa* bits merely adds rounding noise on top of SGD's own minibatch noise, which training tolerates remarkably well. bf16 therefore keeps fp32's full 8-bit exponent (same ~$10^{38}$ range; activations essentially never overflow) and pays with only 7 mantissa bits. fp16 chose the opposite corner — 10 mantissa bits but a max of 65504 and a normal floor of $6.1\times10^{-5}$ — and needed the whole loss-scaling apparatus to survive ([[Lore - Loss Scaling and the fp16 Underflow Crisis]]).

**The DL format zoo.** tf32 (1/8/10, 19 bits used) is a compute mode on Ampere-and-later [[Concept - Tensor Cores]]: fp32 range, fp16-class precision, applied transparently to fp32 matmuls. fp8 comes in two flavors: e4m3 (max 448, more mantissa — weights and activations) and e5m2 (max 57344, more range — gradients), both requiring per-tensor scale factors. The 2024–2026 push is toward fp4 and mxfp block-scaled formats on Blackwell-class hardware *(as of 2026)*. Exact constants for all of these live in [[Reference - Floating Point Formats]].

**Accumulation stays high precision.** A matmul sums $k$ products; rounding error in the sum grows roughly as $\sqrt{k}\,\varepsilon$ ([[Concept - Matrix Multiplication as the Atom of Deep Learning]]). At $k = 8192$ (a typical hidden dim), $\sqrt{k} \approx 90$: with bf16's $\varepsilon \approx 7.8\times10^{-3}$ the accumulated relative error would be order-one — useless — while in fp32 it stays ~$10^{-5}$. This is exactly why tensor cores take bf16/fp16 *inputs* but accumulate the dot product in fp32.

## In practice

- **The standard recipe** *(as of 2026)* is [[Concept - Mixed Precision Training]]: bf16 storage and matmuls, fp32 accumulation inside the matmul, fp32 master weights and optimizer states. Weights cost 2 bytes/param in bf16 — a 70B model is 140 GB of weights versus 280 GB in fp32.
- **Keep in fp32:** softmax (or compute it stably via [[Snippet - The Log-Sum-Exp Trick]]), LayerNorm/RMSNorm statistics, the loss, and any long reduction (means, norms, all-reduce buffers where affordable).
- **fp16 + dynamic loss scaling** is the fallback on pre-Ampere hardware (V100 era); typical scale factors run $2^{10}$–$2^{16}$.
- **Serving goes lower:** once training is done, [[Concept - Post-Training Quantization Formats]] (int8/int4/fp8) halve or quarter memory again, because inference only needs the forward pass's error tolerance.
- **Numbers worth memorizing:** fp16 max = 65504 (a pre-softmax attention logit or un-normalized activation near 256, squared, is already past it); bf16 represents consecutive integers only up to 256, fp16 up to 2048, fp32 up to $2^{24}$ — never store counts or indices in low-precision floats.

## Failure modes

- **Overflow → inf → NaN.** One activation exceeds the format max, the inf propagates through the next matmul as NaN, and the loss is NaN a step or two later. Classic in fp16 attention logits. Detection: finite-value asserts on loss and logits; in fp16, watch the grad-scaler's inf/NaN skip counter.
- **Underflow → 0, silently.** Gradients below the format's floor flush to zero and that parameter simply stops learning — no crash, just a mysteriously flat loss. fp16's subnormal band bottoms out near $6\times10^{-8}$ and hardware often flushes subnormals to zero outright ([[Concept - Subnormal Numbers and Gradual Underflow]]). Detection: per-layer gradient-norm histograms computed in fp32; a layer whose grad norm collapses to exact 0 is underflowing, not converged.
- **Precision loss in reductions.** Softmax, LayerNorm, means, and the loss computed natively in bf16 lose the tail of the sum; symptoms are subtle accuracy drift rather than explosions, which makes this the nastiest of the three. Remedy: fp32 reductions, always.
- **NaN poisoning.** A single NaN infects every downstream value and every gradient upstream through backprop. Detection: `torch.autograd.set_detect_anomaly(True)` (slow; use to localize), finite-check hooks on module outputs, then bisect the forward pass.

## The non-obvious

bf16 is literally fp32's top 16 bits — same sign, same 8-bit exponent, mantissa truncated. Conversion is a 16-bit shift, mixed fp32/bf16 storage is trivial hardware, and you can eyeball what bf16 will do to a tensor by histogramming its fp32 values: the overflow/underflow behavior is *identical* by construction, only rounding noise differs ([[Breakdown - bfloat16]]).

The second hard-won lesson: **underflow doesn't announce itself.** Overflow gives you a NaN you can't miss; underflow gives you a model that trains slightly worse forever. If a low-precision run's loss curve sits just above the fp32 baseline's, suspect flushed gradients before suspecting hyperparameters.

## Connections

- [[Reference - Floating Point Formats]] — the exact bit layouts, ranges, epsilons, and scaling metadata this note reasons about.
- [[Breakdown - bfloat16]] — the design history of the format that won training, including the truncation-conversion trick.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the arcana below the normal floor: gradual underflow, FTZ/DAZ flags, and their silent cost.
- [[Gotchas - Numerical Stability]] — the aggregated catalog of ways swamping, cancellation, and log(0) corrupt real computations.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the war story of fp16's narrow range nearly killing low-precision training.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — where the $\sqrt{k}\,\varepsilon$ accumulation-error argument comes from and why matmul dominates the precision budget.
- [[Concept - Mixed Precision Training]] — the operational recipe (bf16 compute, fp32 master weights) built on this note's mechanism.
- [[Concept - Tensor Cores]] — the hardware that enforces "low-precision multiply, fp32 accumulate" and defines which formats are fast.
- [[Concept - Post-Training Quantization Formats]] — what happens below 16 bits at serving time, where the error tolerance is looser.
- [[Concept - Vector Norms and Distances]] — norm and distance computations are the everyday reductions where relative precision bites first.
- [[Snippet - The Log-Sum-Exp Trick]] — the standard fix for exp/softmax overflow that this note's range limits make necessary.

## Sources

- Goldberg (1991) — *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* The canonical treatment of relative precision, rounding, and swamping.
- IEEE 754-2019 — the standard defining the sign/exponent/mantissa layout, round-to-nearest-even, and subnormals.
- Micikevicius et al. (2017) — *Mixed Precision Training.* fp16 training with loss scaling and fp32 master weights.
- Kalamkar et al. (2019) — *A Study of BFLOAT16 for Deep Learning Training.* The empirical case that range matters more than mantissa for training.
- Micikevicius et al. (2022) — *FP8 Formats for Deep Learning.* Defines e4m3/e5m2 and the per-tensor scaling regime.
