---
tags: [concept, domain/training-at-scale, level/core]
aliases: [AMP, automatic mixed precision, bf16 training, fp16 training, loss scaling]
summary: "Training in bf16/fp16 with fp32 master weights and loss scaling to get 2-8x tensor-core throughput without losing numerical stability."
---

# Concept - Mixed Precision Training

> **One-paragraph hook:** Every FLOP a GPU's tensor cores run in bf16 instead of fp32 is roughly free: same silicon, several times the throughput, half the memory. The catch is that 16-bit floats can't represent everything fp32 can, and a handful of operations (loss, softmax, normalization statistics, gradient reduction) will silently corrupt a run if left in low precision. Mixed precision training means knowing which operations get the speedup and which must stay in fp32 no matter what.

## The mechanism

Two 16-bit formats compete for this role, and they fail in opposite ways:

| Format | Exponent bits | Mantissa bits | Range | Needs loss scaling? |
|---|---|---|---|---|
| fp32 | 8 | 23 | ~1e-38 to 3e38 | n/a |
| fp16 | 5 | 10 | ~6e-5 to 65504 | **yes** |
| bf16 | 8 | 7 | ~1e-38 to 3e38 (fp32's range) | no |

**fp16** has only 5 exponent bits, so its range tops out around 65504 and bottoms out around 6e-5. Smaller gradients flush to zero (underflow) before they're ever used. The fix is **loss scaling** (Micikevicius et al. 2018). Multiply the loss by a scale factor $S$ before `.backward()`. Every gradient gets scaled by the same $S$, which pushes small values back into fp16's representable range. Then **unscale** (divide by $S$) before the optimizer step. A *dynamic* scaler starts $S$ high, halves it whenever the gradients contain an inf/nan (skipping that step entirely), and grows it back periodically (e.g., every 2000 clean steps) to stay as close to the overflow boundary as it can without crossing it:

```
loss × S  →  backward()  →  grads × S (now representable in fp16)
          →  unscale (grads ÷ S)
          →  finite? ── no ──▶ skip step, halve S
                    │
                   yes
                    ▼
          clip grad norm → optimizer.step() (fp32 master update)
                    → cast fp32 master weights → fp16/bf16 working copy
                    → grow S every K clean steps
```

**bf16** keeps fp32's 8 exponent bits, so it has the same dynamic range, but only 7 mantissa bits. It's *coarser*, not narrower. Since it covers the same magnitudes as fp32 (less precisely), it never needs loss scaling. That's why bf16 is now the near-universal default for LLM pretraining and fp16 has largely disappeared from it. You lose a moving part (no scaler to tune, no overflow-skipped steps) and have to be more careful elsewhere.

**Master weights.** Whichever 16-bit format you compute in, the optimizer keeps an **fp32 copy** of every parameter, applies updates to *that* copy, and casts down to bf16/fp16 only for the next forward pass. The reason is *swamping*. bf16's 7 mantissa bits give roughly 2 decimal digits of precision, so a relative update smaller than about $2^{-7} \approx 0.8\%$ of the weight's magnitude rounds to exactly zero when applied directly in bf16. Late in training, with a decayed learning rate, per-step updates routinely fall below that threshold. Train directly in bf16 without an fp32 master copy and the model silently stops learning while the loss curve looks fine for a while. Accumulating updates in fp32 and only *rounding* to bf16 for compute avoids this.

**What always stays fp32:** the loss, softmax, layernorm/[[Concept - RMSNorm and LayerNorm|RMSNorm]] statistics (mean/variance accumulation), the online-softmax accumulation inside attention, and the **gradient all-reduce** across [[Concept - Data Parallelism and ZeRO|data-parallel ranks]]. Reducing gradients in bf16 compounds rounding error across every rank being summed, so the reduction needs fp32 accumulation even when the inputs started as bf16. Matmuls are the one thing that runs in low precision on [[Concept - Tensor Cores]]. **TF32** (10 mantissa bits, fp32's 8 exponent bits, Ampere+) is a middle-ground format used transparently for nominally-fp32 matmuls. It trades a little precision for tensor-core throughput with no explicit dtype change in model code.

## In practice

Real numbers: bf16 gives roughly **2x activation memory** savings over fp32 and **2-8x tensor-core throughput** on A100/H100, depending on the operation and shape. That's enough that fp32 training is essentially never used for LLM pretraining above toy scale. The only question is bf16 vs. the fp8 formats now used at the frontier ([[Concept - FP8 Training]] pushes the same master-weight/scaling discipline one format further down). Framework "automatic mixed precision" (PyTorch AMP, NVIDIA Apex) automates the cast/scale/unscale bookkeeping above. You still need to know which ops it excludes by default: a normalization layer or loss function implemented outside the framework's autocast rules can silently run in the wrong precision.

## Failure modes

- **fp16 loss-scale collapse.** Repeated gradient overflow drives the dynamic scaler's $S$ toward zero over many halvings. Once $S$ is small enough, legitimate gradients underflow again *even after* unscaling, and the run stalls without technically crashing. Watch the scaler's current $S$ and the skipped-step count. A monotonically shrinking $S$ with no recovery is the tell; the loss curve itself isn't.
- **bf16 precision causing slow, silent divergence** in very deep or very long runs. Nothing overflows to trip an alarm the way fp16 does. bf16 fails through rounding error compounding across depth or steps, which shows up as gradual loss/grad-norm drift instead of a sharp spike. [[Concept - Training Stability and Loss Spikes]] names bf16 rounding as one root cause of instability at scale.
- **Running layernorm in bf16 instead of fp32** causes instability. Variance is a sum of squares, a numerically sensitive reduction, and bf16's 7 mantissa bits aren't enough to compute it reliably, especially early in training when activations can have high variance. Keeping layernorm/RMSNorm statistics in fp32 is a deliberate convention for this reason.

## The non-obvious

bf16 never overflows the way fp16 does, so teams get complacent and treat it as numerically safe everywhere. bf16's failure mode is worse to debug *because* nothing crashes. fp16 collapse announces itself: skipped steps, a shrinking scale factor, a flat loss curve you can point to. bf16 divergence looks like a run that's fine for 40,000 steps and then starts producing a slightly-too-high loss with no single event to root-cause. It often gets traced back, hundreds of steps later, to an op someone left unguarded outside the fp32-mandatory list. My rule of thumb: the fp32-required op list ([[Concept - AdamW at Scale|optimizer update]], loss, softmax, norm statistics, gradient reduction) isn't something to revisit per model. Treat it as fixed, and audit any new custom op against it before trusting a run past a few thousand steps.

## Connections
- [[Concept - Why Models Don't Fit on One GPU]] — mixed precision's bytes-per-parameter choices (2 for bf16 vs 4 for fp32) directly set the memory budget this note's format table quantifies.
- [[Concept - FP8 Training]] — the next rung down in precision, inheriting the same master-weight and scaling discipline with a much smaller dynamic range to manage.
- [[Concept - Floating Point for Deep Learning]] — the bit-layout fundamentals (exponent/mantissa tradeoffs) that explain why fp16 and bf16 fail in opposite ways.
- [[Concept - Training Stability and Loss Spikes]] — bf16 rounding accumulation over depth is a named root cause of the instabilities that note catalogs.
- [[Concept - Tensor Cores]] — the hardware unit whose throughput gain is the entire reason to do any of this.
- [[Concept - RMSNorm and LayerNorm]] — the normalization statistics that must stay in fp32 to avoid the variance-computation instability described above.
- [[Concept - Data Parallelism and ZeRO]] — the gradient all-reduce whose reduction dtype (fp32, not bf16) matters at scale for exactly the same swamping reason as the master-weight update.
- [[Concept - AdamW at Scale]] — the optimizer whose fp32 master-weight update is the mechanism that makes bf16-compute-with-fp32-accumulate work at all.

## Sources
- Micikevicius et al. (2018) — "Mixed Precision Training" (ICLR) — introduces fp32 master weights and dynamic loss scaling for fp16 training.
- Kalamkar et al. (2019) — "A Study of BFLOAT16 for Deep Learning Training" — establishes bf16's exponent-preserving design and why it avoids the loss-scaling requirement fp16 needs.
