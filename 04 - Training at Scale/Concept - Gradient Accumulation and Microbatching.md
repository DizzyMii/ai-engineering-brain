---
tags: [concept, domain/training-at-scale, level/surface]
aliases: [gradient accumulation, grad accum, microbatching]
summary: "Splitting a target batch into microbatches whose gradients sum before one optimizer step, hitting a token budget under fixed GPU memory."
---

# Concept - Gradient Accumulation and Microbatching

> **One-paragraph hook:** A pretraining run wants a 4-million-token batch for stable, efficient gradient estimates. A single GPU can hold maybe a few hundred thousand tokens of activations at once. Gradient accumulation reconciles the two: run several small forward/backward passes, sum their gradients, and take one optimizer step. It's mechanically simple, and still a subtle bug in it (mis-weighting the summed gradient) went unnoticed in mainstream training frameworks for years.

## The mechanism

The identity to remember: **effective batch size = microbatch_size × grad_accum_steps × data_parallel_world_size**. Every large run uses it to hit a fixed token-per-step target (e.g., 4M tokens) no matter how much HBM a single GPU has. [[Concept - Why Models Don't Fit on One GPU]] covers where that HBM ceiling comes from.

It's a loop, not one fused step:

```python
optimizer.zero_grad()
for i, microbatch in enumerate(microbatches):
    is_last = (i == len(microbatches) - 1)
    with model.no_sync() if (ddp and not is_last) else nullcontext():
        loss = model(microbatch)
        (loss / accum_steps).backward()   # accumulates into .grad
optimizer.step()
```

Each microbatch runs a full forward and backward pass. PyTorch's autograd adds gradients into `.grad` by default, so the summation needs no special API. Under DDP, wrap every microbatch *except the last* in `no_sync()`. Without it DDP all-reduces after every microbatch's backward. That's correct but wastes communication. With it, the all-reduce fires once per accumulation window, at zero cost to correctness ([[Concept - Data Parallelism and ZeRO]] has the all-reduce mechanics being saved here).

**The 2024 loss-normalization bug.** Dividing each microbatch's *mean* loss by `accum_steps` is only correct if every microbatch has the same number of contributing (non-padding) tokens. When token counts differ, from padding to different lengths or from sequence packing, the per-microbatch mean over- or under-weights microbatches with fewer real tokens and mis-scales the effective gradient without any error. Unsloth surfaced this publicly in 2024, and it was confirmed in Hugging Face's `Trainer` and other frameworks. The fix: **sum per-token losses across all microbatches and divide once by the global token count** instead of averaging per-microbatch means.

## In practice

LLM pretraining batches typically span 0.5M-16M tokens, and grad-accum steps of 4-64 are common depending on cluster size and per-GPU memory. Accumulation is *free* in FLOPs, since the same total compute runs however you split it. What it changes is the **communication-to-compute ratio**: more accumulation steps means fewer data-parallel all-reduce syncs per token, a real throughput win on bandwidth-constrained interconnects. It also ties directly to [[Concept - Tensor and Pipeline Parallelism]]. The microbatches used to fill a pipeline are the same physical mechanism, not a separate concept.

Precision matters too (see [[Concept - Mixed Precision Training]]). With fp16 loss scaling, unscale the accumulated gradient *before* clipping, not per-microbatch. Gradient clipping itself (see [[Concept - AdamW at Scale]]) has to use the **global norm of the fully accumulated gradient**, after every microbatch has contributed. Clipping per-microbatch clips a partial, smaller-magnitude gradient and silently changes the effective step.

## Failure modes

- **Forgetting the `1/accum_steps` scaling**, or getting it wrong under unequal microbatch token counts as above. This silently multiplies the effective learning rate by `accum_steps`. At 16-64x accumulation that's enough to destabilize or diverge a run that looks correctly configured everywhere else.
- **Clipping per-microbatch instead of on the accumulated gradient.** You clip a gradient that hasn't finished accumulating, which changes the effective clip threshold. You won't see it unless you check where clipping sits relative to the accumulation loop.
- **Missing `no_sync()` under DDP.** A throughput bug, not a correctness bug: every microbatch triggers a full all-reduce, wasting bandwidth in proportion to `accum_steps`.
- **Packed sequences without correcting the denominator.** Packing multiple documents per training sequence changes the token count per microbatch, which makes the naive per-microbatch-mean bug above especially likely to bite.

## The non-obvious

Accumulation *feels* like a pure memory workaround, but it's also a communication-cost dial. For a fixed token budget, more accumulation steps per optimizer step means proportionally fewer all-reduces, which you can use to tune MFU on a bandwidth-limited cluster regardless of memory. The loss-normalization bug is the sharper lesson. Each microbatch computes a standard mean-reduced loss, the same as single-batch training would, so the code is *locally* correct. It becomes *globally* wrong once token counts vary across microbatches. It survived in widely used training code for years because the mis-weighting crashes nothing; it just changes what the model learns.

## Connections
- [[Concept - Why Models Don't Fit on One GPU]] — the memory ceiling that makes microbatching necessary in the first place.
- [[Concept - Critical Batch Size]] — the theory of what effective batch size a run should actually target.
- [[Concept - Data Parallelism and ZeRO]] — the all-reduce mechanism `no_sync()` is economizing across accumulation steps.
- [[Concept - Mixed Precision Training]] — loss scaling must be unscaled before clipping the accumulated gradient.
- [[Concept - Tensor and Pipeline Parallelism]] — pipeline schedules reuse the same microbatch mechanism to fill the pipeline.
- [[Concept - AdamW at Scale]] — global-norm gradient clipping must run on the fully accumulated gradient, not per microbatch.
- [[Concept - Vanishing and Exploding Gradients]] — mis-scaled accumulated gradients manifest as the same instability symptoms as exploding gradients.
- [[Concept - Floating Point for Deep Learning]] — the loss-scaling/unscaling arithmetic that must be sequenced correctly around accumulation.

## Sources
- Unsloth (2024) — public writeup identifying the gradient-accumulation loss-normalization bug across mainstream training frameworks (including Hugging Face's `Trainer`); the fix (sum per-token loss, divide by global token count) landed in `transformers` shortly after.
