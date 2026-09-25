---
tags: [concept, domain/foundations, level/unicorn]
aliases: [subnormals, denormals, denormal numbers, gradual underflow, flush-to-zero, FTZ, DAZ]
summary: "The IEEE-754 arcana that bites DL: subnormals, the flush-to-zero cliff, signed zero, and NaN semantics — and how they silently stall training."
---

# Concept - Subnormal Numbers and Gradual Underflow

> **One-paragraph hook:** Below the smallest "normal" float sits a band of subnormal numbers that IEEE-754 keeps to soften the fall to zero. The band is a deliberate accuracy-preserving design, and modern ML hardware routinely throws it away for speed. What you get is a class of bugs where a model *stops learning without any error* because its smallest gradients got flushed to zero, plus a family of NaN/signed-zero footguns that break sorting, dedup, and normalization. Almost nobody reads this part of [[Concept - Floating Point for Deep Learning|floating point]] until it costs them a training run.

## The mechanism

A normalized IEEE-754 value is $(-1)^s \times 1.m \times 2^{e-\text{bias}}$, with an *implicit leading 1*. That leading 1 gives normals their precision, but it also sets a floor: the smallest normal fp32 is $2^{-126} \approx 1.18\times10^{-38}$. Without a special case, everything between there and zero would round straight to $0$. A hard cliff.

IEEE-754 avoids the cliff with **subnormals** (a.k.a. denormals). When the exponent field is *all zeros*, the implicit leading bit becomes $0$ and the value is $(-1)^s \times 0.m \times 2^{-126}$. Representable magnitudes then extend downward in *absolute* steps of the smallest subnormal, down to:

| Format | Smallest normal | Smallest subnormal | Machine epsilon ($2^{-\text{mant}}$) |
|---|---|---|---|
| fp32 (1/8/23) | $2^{-126}\approx1.18\text{e-}38$ | $2^{-149}\approx1.4\text{e-}45$ | $2^{-23}\approx1.19\text{e-}7$ |
| fp16 (1/5/10) | $2^{-14}\approx6.10\text{e-}5$ | $2^{-24}\approx5.96\text{e-}8$ | $2^{-10}\approx9.77\text{e-}4$ |
| bf16 (1/8/7) | $2^{-126}\approx1.18\text{e-}38$ | $2^{-133}\approx9.18\text{e-}40$ | $2^{-7}\approx7.81\text{e-}3$ |

This is **gradual underflow**: precision degrades one bit at a time as you approach zero instead of falling off a cliff. William Kahan pushed it through the IEEE-754 (1985) committee as a deliberate and famously contested choice, against the flush-to-zero camp (DEC VAX and others). Gradual underflow guarantees something the alternatives lack: $x - y = 0$ *if and only if* $x = y$, so no two distinct floats subtract to a false zero, and error bounds near zero stay honest. The bit layout of all these formats is in [[Reference - Floating Point Formats]].

**Epsilon is not the smallest number.** Machine epsilon ($2^{-\text{mantissa}}$, the gap between $1.0$ and the next float) measures *relative* precision near 1.0. The smallest representable value is many orders of magnitude smaller, because the *exponent*, extended by subnormals, sets the range. Mix them up ("I'll use `1e-7` as my floor because that's fp32 epsilon") and your tolerances are off by 30+ orders of magnitude.

## In practice

Subnormals are cheap to *represent* and, on many machines, ruinously expensive to *compute with*. Most CPUs (and some accelerators) handle the all-zeros-exponent case in slow microcode off the fast path, so arithmetic that produces subnormals can slow down **10–100×**. Audio DSP has known this for decades (a reverb tail decaying smoothly into the subnormal range would spike a plugin's CPU by two orders of magnitude), and physics simulations hit it too.

The hardware/OS fix is to turn subnormals off:

- **FTZ (flush-to-zero)** rounds any subnormal *result* to zero.
- **DAZ (denormals-are-zero)** treats any subnormal *input* as zero.

On x86-SSE these are per-thread bits in the `MXCSR` register. Compiling with `-ffast-math` sets them process-wide, so fast-math can change results as well as speed (see [[Lore - The Nondeterminism of Floating-Point Reductions]]). On NVIDIA GPUs, denormal handling is fixed at *compile time* by the `-ftz` flag, with no runtime per-thread mode, and `--use_fast_math` implies `-ftz=true`. It's baked into the kernel you're running, so it's easy to inherit FTZ from a library without knowing.

## Failure modes

- **Dying gradients from FTZ.** With flush-to-zero on, any gradient or activation that drifts into the subnormal band becomes $0$ and stops contributing to the update, with no warning. In **fp16** this is acute. fp16's subnormal band ($6\times10^{-8}$ to $6\times10^{-5}$) is where deep-net tail gradients live, so FTZ turns "small but useful" into "gone." It's a hidden reason low-precision training stalls, and the mechanistic root of the crisis [[Lore - Loss Scaling and the fp16 Underflow Crisis|loss scaling]] was invented to fix: shift the whole gradient distribution up out of the subnormal/flushed region before it can be zeroed. It's easily confused with ordinary [[Concept - Vanishing and Exploding Gradients|vanishing gradients]]. Same symptom (learning stops), different cause (representation floor vs. signal decay).
  *Detection:* histogram gradient magnitudes per layer. A spike of exact-zero gradients with no dead ReLUs to explain it is FTZ, not the model.
- **Signed zero surprises.** $+0$ and $-0$ compare `==` equal, but $1/{+0} = +\infty$ while $1/{-0} = -\infty$. A sign that survives underflow to zero can flip the sign of everything downstream.
- **NaN semantics break collections.** `NaN != NaN`. That one fact breaks naive sorting, `argmax`/`argmin`, deduplication, and `set` membership without complaint: a NaN slips past every equality check and poisons order statistics. NaN also carries a payload and propagates. One NaN contaminates every value it touches, and $\infty - \infty = \text{NaN}$.
  *Detection:* gate layer boundaries with `torch.isfinite(x).all()`, and use anomaly mode to find the op that *produced* the NaN, since the first place it surfaces is often downstream (see [[Concept - Backpropagation|the backward pass]], where a NaN in one gradient poisons all upstream ones).
- **Precision loss when reductions are demoted.** Even in a bf16 model, sums/means/softmax/loss must accumulate in fp32. A reduction done in the low-precision type loses its tail right where subnormals would have carried it. [[Concept - Mixed Precision Training]] makes this a standing rule, and [[Concept - Tensor Cores|tensor cores accumulating in fp32]] enforce it in hardware.

## The non-obvious

**Gradual underflow is a correctness feature that FLOPS-hungry ML hardware deliberately discards, and you usually can't see the trade until a model stops learning.** Kahan spent political capital getting subnormals into the standard for numerical robustness. Three decades later, the highest-throughput accelerators flush them by default, because the extra silicon and cycles aren't worth it for workloads that already tolerate noise. That's a defensible engineering call until your fp16/fp8 gradients land in the flushed band and the loss curve flatlines with no NaN, no error, no warning. The tell is a *silent* stall. No crash, no spike, just a model whose smallest signals are now zero. After you've seen it once, "is FTZ on, and do my gradients live where it bites?" goes on the debugging checklist for good.

## Connections

- [[Concept - Floating Point for Deep Learning]] — the parent mechanism; subnormals are the edge case of the sign/exponent/mantissa layout described there.
- [[Reference - Floating Point Formats]] — the exact constants (smallest normal/subnormal, epsilon) for every format, front-loaded for mid-task lookup.
- [[Gotchas - Numerical Stability]] — the broader catalog where FTZ-flushed gradients, log(0), and NaN propagation sit alongside their fixes.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the historical fix aimed squarely at the fp16 subnormal band this note describes; the "why" behind static/dynamic loss scaling.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — the *other* thing fast-math does (reassociate sums) beyond flushing subnormals; both are silent result-changers.
- [[Concept - Mixed Precision Training]] — the practice that keeps reductions in fp32 precisely so the subnormal-range tail isn't lost.
- [[Concept - Tensor Cores]] — the hardware that multiplies in low precision but accumulates in fp32, dodging the subnormal-loss problem in matmul.
- [[Concept - Backpropagation]] — where a single flushed-to-zero or NaN gradient propagates and kills learning across the graph.
- [[Concept - Vanishing and Exploding Gradients]] — the classic failure this is easily mistaken for; same symptom, different (representational) cause.

## Sources

- IEEE 754 (1985, rev. 2008/2019) — defines subnormals and gradual underflow; Kahan's design rationale is the canonical account of why the band exists.
- Goldberg (1991) — "What Every Computer Scientist Should Know About Floating-Point Arithmetic." The standard reference for subnormals, signed zero, and NaN semantics.
- Micikevicius et al. (2017) — "Mixed Precision Training." Documents fp16 gradient underflow and the loss-scaling remedy that dodges the subnormal/flush region.
- Intel/NVIDIA architecture manuals — `MXCSR` FTZ/DAZ bits and the CUDA `-ftz` compile flag; the practical knobs and their costs.
