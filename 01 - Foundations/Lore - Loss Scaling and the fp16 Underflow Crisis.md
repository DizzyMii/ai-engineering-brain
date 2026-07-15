---
tags: [lore, domain/foundations, level/unicorn]
aliases: [loss scaling, dynamic loss scaling, GradScaler, fp16 underflow, gradient scaling]
summary: "How fp16's 5-bit exponent nearly killed low-precision training, the loss-scaling hack that saved it, and the bf16 ending."
---

# Lore - Loss Scaling and the fp16 Underflow Crisis

> Between roughly 2016 and 2020, half-precision training nearly died in the crib. fp16 promised 2-8x throughput and half the memory traffic, and in exchange it silently zeroed the gradients of any network deep enough to matter. The rescue was a one-line multiply — scale the loss before backprop — plus a self-tuning feedback loop around it that an entire generation of practitioners ran without understanding. Then bf16 arrived and made the whole apparatus obsolete overnight. This is the story, because the same crisis is currently replaying one octave lower in fp8.

## What happened

**The setup.** Volta-class hardware (V100, 2017) offered 125 TFLOPS of fp16 tensor-core throughput against 15.7 TFLOPS of fp32 — an ~8x carrot ([[Concept - Tensor Cores]]). Halving bytes per value also halves memory bandwidth per tensor, which matters even more than FLOPs for most real layers. Everyone wanted fp16 training. Almost nobody's first fp16 run worked.

**The crisis.** The problem is written directly into the bit layout described in [[Concept - Floating Point for Deep Learning]]: fp16 spends only 5 bits on the exponent. Its largest finite value is 65504; its smallest normal is $2^{-14} \approx 6.1\times10^{-5}$, with subnormals extending the floor to $2^{-24} \approx 6\times10^{-8}$ (exact constants in [[Reference - Floating Point Formats]]). Deep-net activation gradients routinely live at $10^{-5}$ to $10^{-8}$ and below — precisely the band fp16 can barely represent, and exactly the band that flush-to-zero hardware modes discard outright ([[Concept - Subnormal Numbers and Gradual Underflow]]). So gradients underflowed to exactly 0 and the model *silently stopped learning*: no exception, no NaN, just a loss curve that plateaus early while an fp32 control run keeps descending. Simultaneously, the *high* side bit too — attention logits and activations spiking past 65504 overflow to inf, which becomes NaN one op later. fp32's 8-bit exponent (range $\sim 10^{38}$) had been quietly absorbing both failure modes for years; fp16's 5 bits exposed them at once.

The diagnosis came from Micikevicius et al. 2017 ("Mixed Precision Training", NVIDIA + Baidu), whose gradient histogram is one of the most consequential plots in systems ML: for an SSD detection network, a large mass of activation-gradient magnitudes sat *below* fp16's representable floor — flushed to zero in a straight fp16 cast — while most of fp16's upper exponent range sat completely unused. The format's 12 orders of magnitude of dynamic range were pointed at the wrong decades.

**The hack.** If the gradients sit too low in the range, *shift the whole distribution up*. Multiply the loss by a scale factor $S$ before backprop. Backpropagation is linear in the upstream gradient, so by the chain rule every gradient in the network is multiplied by exactly $S$:

$$\nabla_\theta (S \cdot L) = S \cdot \nabla_\theta L$$

Choose $S$ a power of two and the multiply touches only exponent bits — no mantissa rounding, bit-exact direction. Unscale (divide by $S$, in fp32) before the optimizer step. Static scales of $2^{10}$ to $2^{16}$ were typical; for the SSD network in the paper, $S = 8$ — three exponent positions — was enough to recover fp32 accuracy. The constraint is a squeeze: $S$ large enough to lift the small-gradient tail above $2^{-24}$, small enough that the largest gradients don't overflow 65504.

**Dynamic loss scaling.** A static $S$ is a hyperparameter with a cliff on both sides, and the correct value drifts as gradient magnitudes shrink over training. The fix that made fp16 actually usable was a feedback loop: start $S$ high (e.g. $2^{16}$); if any gradient comes back inf/NaN, *skip the optimizer step entirely* and halve $S$; after $N$ consecutive clean steps, double it. The scale rides a sawtooth just under the overflow ceiling, self-tuning to the gradient distribution. This shipped as NVIDIA Apex "amp" (2018) and then as `torch.cuda.amp.GradScaler`, whose defaults are the folklore constants frozen into an API: `init_scale=65536` ($2^{16}$), `backoff_factor=0.5`, `growth_factor=2.0`, `growth_interval=2000`. The full modern recipe lives in [[Concept - Mixed Precision Training]].

**fp32 master weights.** Even a rescued gradient can die at the update. The step $w \mathrel{-}= \eta g$ is an addition, and an addition loses the small operand entirely when $|\eta g| < \tfrac{1}{2}\,\text{ulp}(w) \approx \varepsilon |w|/2$ — the swamping mechanism from [[Concept - Matrix Multiplication as the Atom of Deep Learning]]'s accumulation story. fp16's machine epsilon is $2^{-10} \approx 9.8\times10^{-4}$: with a weight at 0.1, any update below $\sim 5\times10^{-5}$ rounds to nothing, and late-training updates are almost all that small. So the second pillar of Micikevicius et al.: keep an fp32 master copy of the weights, apply updates there, cast down to fp16 for the forward pass. (The alternative lineage — stochastic rounding — went into TPU and Graphcore hardware instead.)

**The era of pain.** Megatron-LM (Shoeybi et al. 2019), BERT, and the GPT-2/GPT-3 generation all trained fp16 with this full apparatus, and it was fragile in practice. The war stories are consistent: runs that diverge to NaN at step 40k from a single overflow spike; loss scales that collapse to 1 and pin there, meaning nearly every step is being skipped while the job burns GPU-hours "training" on almost no updates. [[Lore - The OPT-175B Logbook]] is the best public record — OPT-175B was trained in fp16, and the logbook documents repeated loss-scale collapses and divergences, answered with restart-from-checkpoint, lowered learning rates, and tightened gradient clipping. GLM-130B (Zeng et al. 2022) shipped an *embedding-gradient shrink* (scale embedding-layer gradients by 0.1) specifically to survive fp16. Folklore, well-attested: for years practitioners cargo-culted $S = 2^{15}$ as a static scale because it worked once on someone's BERT.

**The bf16 rescue.** [[Breakdown - bfloat16]] is the format that ended the crisis: keep fp32's 8-bit exponent, pay with a 7-bit mantissa. Same $\sim 3.4\times10^{38}$ range as fp32 means gradients essentially never underflow the *format* (the update-swamping problem remains — bf16's coarse mantissa still wants fp32 master weights). TPUs had bf16 from ~2018; the A100 (2020) brought it to GPUs, and large-model training pivoted almost immediately. BigScience watched its early 104B fp16 experiments diverge, watched OPT's fp16 ordeal, and trained BLOOM-176B in bf16, citing stability. Loss scaling went from load-bearing to legacy in about two years.

**The sequel.** fp8 on Hopper (2022) reopened the exact same wound one octave lower: e4m3 tops out at 448, e5m2 at 57344, and neither window covers real tensor distributions unaided. Scaling came back — not as one global loss scale but as per-tensor scale factors maintained from amax history (Transformer Engine's delayed scaling) and per-block scales in the mxfp lineage; DeepSeek-V3 (2024) trained in fp8 with fine-grained per-tile scaling. The same idea priced into inference is [[Concept - Post-Training Quantization Formats]]. The crisis never ended; it moved into the scaling metadata.

## The lesson

Mechanically, four things generalize:

1. **A format is a window; your tensors are a distribution.** Training works only if the window covers the distribution — and gradients, activations, and weights are *different distributions*, offset by orders of magnitude. fp16 failed not because 16 bits is too few but because its window was centered on the wrong decades for gradients. Every low-precision scheme since (bf16, fp8 + per-tensor scales, block formats) is a different answer to "how do we aim the window."
2. **Scaling is renting range.** A power-of-two multiplicative shift is exact in floating point and moves the whole distribution into the window. Loss scaling, fp8 per-tensor scales, and quantization block scales are the same trick at three granularities.
3. **The loss scale was free telemetry, and bf16 took it away.** A dynamic loss scale is a live gradient-magnitude monitor: a sagging scale means overflow frequency is rising — divergence early-warning *before* the loss curve shows anything. bf16 training lost this canary; you must watch gradient norms explicitly instead. Corollary: GradScaler *skips* steps on overflow, so optimizer steps < data steps; a thrashing loss scale means your run is silently training on fewer updates than you think. Log the scale and the skip count.
4. **Unscale before you clip.** Gradient clipping against `max_norm=1.0` while gradients are still multiplied by $2^{16}$ clips everything to numerical dust — or no-ops, depending on ordering. `scaler.unscale_(optimizer)` before clipping is the canonical fix; the surrounding pathology catalog is [[Gotchas - Numerical Stability]].

## Evidence status

- **Verified:** the fp16/bf16/fp8 format constants; the Micikevicius et al. 2017 mechanism, gradient histogram, $S=8$ SSD result, and fp32-master-weights recipe (published paper); Apex/`torch.cuda.amp.GradScaler` defaults (public source); OPT-175B's fp16 training and loss-scale battles (public logbook); GLM-130B's embedding-gradient shrink (published paper); BLOOM's deliberate bf16 choice (BigScience training chronicles).
- **Well-sourced engineering folklore:** the cargo-culted $S=2^{15}$, and the composite "NaN at step X" / "loss scale pinned at 1" anecdotes — universally recognized by anyone who ran fp16 at scale, attributable to no single citable run.
- **Mild caveat on the clean ending:** "bf16 eliminated loss scaling" is true for the loss-scale mechanism itself, but bf16's 7-bit mantissa means fp32 master weights (or stochastic rounding) survived into the bf16 era — only half the apparatus retired.

## Connections
- [[Concept - Floating Point for Deep Learning]] — the range-vs-precision bit-budget tradeoff that made fp16's 5-bit exponent the villain of this story.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the sub-$2^{-14}$ band where dying gradients live, and why flush-to-zero hardware makes the underflow strictly worse.
- [[Reference - Floating Point Formats]] — the exact constants (65504, $6.1\times10^{-5}$, $6\times10^{-8}$, e4m3's 448) this narrative turns on.
- [[Breakdown - bfloat16]] — the format designed as the answer: spend the bits on exponent so the loss-scaling apparatus becomes unnecessary.
- [[Concept - Mixed Precision Training]] — the modern recipe that inherited all of this: what to keep in fp32, where the scaler sits in the step, when you still need it.
- [[Gotchas - Numerical Stability]] — the wider pathology catalog; the unscale-before-clip bug and inf/NaN detection live there.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — swamping in accumulation is the same mechanism that kills unscaled fp16 weight updates.
- [[Concept - Tensor Cores]] — the hardware carrot (8x fp16 throughput) that made everyone willing to fight this fight at all.
- [[Concept - Post-Training Quantization Formats]] — where the per-tensor/per-block scaling idea that succeeded loss scaling is now standard practice.
- [[Lore - The OPT-175B Logbook]] — the best public primary source of what fp16 training pain actually looked like day to day at 175B scale.

## Sources
- Micikevicius et al. (2017) — "Mixed Precision Training" (ICLR 2018). Loss scaling, fp32 master weights, fp32 accumulation; the SSD gradient histogram and the $S=8$ result.
- Shoeybi et al. (2019) — "Megatron-LM". Representative large-scale fp16 + dynamic loss scaling training of the era.
- Zhang et al. (2022) — "OPT: Open Pre-trained Transformer Language Models" + the public metaseq logbook. Primary record of fp16 loss-scale collapses and restarts at 175B.
- Zeng et al. (2022) — "GLM-130B". Documents fp16 instability and the embedding-gradient-shrink workaround.
- BigScience Workshop / Scao et al. (2022) — "BLOOM"; training chronicles record choosing bf16 for stability after fp16 failures at 104B scale.
- NVIDIA Apex and PyTorch AMP documentation/source — dynamic loss scaling implementation and the `GradScaler` default constants.
- DeepSeek-AI (2024) — "DeepSeek-V3 Technical Report". fp8 training with fine-grained per-tile scaling — the crisis's fp8 sequel in production.
