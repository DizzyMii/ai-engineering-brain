---
tags: [concept, domain/training-at-scale, level/surface]
aliases: [gradient accumulation, grad accum, microbatching]
summary: "Splitting a target batch into microbatches whose gradients sum before one optimizer step, hitting a token budget under fixed GPU memory."
---

# Concept - Gradient Accumulation and Microbatching

> **One-paragraph hook:** A pretraining run wants a 4-million-token batch for stable, efficient gradient estimates; a single GPU can physically hold maybe a few hundred thousand tokens of activations at once. Gradient accumulation is the trick that reconciles the two — run several small forward/backward passes, sum their gradients, and take exactly one optimizer step — and it is so mechanically simple that a subtle bug in it (mis-weighting the summed gradient) went unnoticed in mainstream training frameworks for years.

## The mechanism

The core identity: **effective batch size = microbatch_size × grad_accum_steps × data_parallel_world_size**. This is the lever every large run pulls to hit a fixed token-per-step target (e.g., 4M tokens) regardless of how much HBM any single GPU has — see [[Concept - Why Models Don't Fit on One GPU]] for why that HBM ceiling exists in the first place.

The mechanism is a loop, not a single fused step:

```python
optimizer.zero_grad()
for i, microbatch in enumerate(microbatches):
    is_last = (i == len(microbatches) - 1)
    with model.no_sync() if (ddp and not is_last) else nullcontext():
        loss = model(microbatch)
        (loss / accum_steps).backward()   # accumulates into .grad
optimizer.step()
```

Each microbatch runs a full forward and backward pass, and PyTorch's autograd accumulates gradients additively into `.grad` by default — that's the entire trick, no special API needed for the summation itself. Under DDP, wrapping every microbatch *except the last* in `no_sync()` matters: without it, DDP all-reduces gradients after every microbatch's backward, which is correct but wastes communication — with it, the all-reduce fires once per accumulation window instead of once per microbatch, at zero cost to correctness (see [[Concept - Data Parallelism and ZeRO]] for the all-reduce mechanics being economized here).

**The 2024 loss-normalization bug**: dividing each microbatch's *mean* loss by `accum_steps` is only correct if every microbatch has the same number of contributing (non-padding) tokens. When microbatches have unequal token counts — from padding to different lengths, or from sequence packing — that per-microbatch mean silently over- or under-weights microbatches with fewer real tokens, mis-scaling the effective gradient. This was surfaced publicly by Unsloth in 2024 and confirmed as a bug present in Hugging Face's `Trainer` and other frameworks; the fix is to **sum per-token losses across all microbatches and divide once by the global token count**, not average per-microbatch means.

## In practice

LLM pretraining batches typically span 0.5M-16M tokens; grad-accum steps of 4-64 are common depending on cluster size and per-GPU memory. A useful framing: accumulation is *free* in FLOP terms — the same total compute runs regardless of how it's split into microbatches — but it changes the **communication-to-compute ratio**: more accumulation steps means fewer data-parallel all-reduce syncs per token processed, which is a real throughput win on bandwidth-constrained interconnects. It interacts directly with [[Concept - Tensor and Pipeline Parallelism]]: pipeline parallelism's microbatches are the same physical mechanism used to fill the pipeline, not a separate concept.

Precision interactions matter too, tying into [[Concept - Mixed Precision Training]]: when loss scaling is in play (fp16), unscale the accumulated gradient *before* clipping, not per-microbatch. Gradient clipping itself (see [[Concept - AdamW at Scale]]) must be computed on the **global norm of the fully accumulated gradient**, after all microbatches have contributed — clipping per-microbatch clips a partial, smaller-magnitude gradient and silently changes the effective step.

## Failure modes

- **Forgetting the `1/accum_steps` scaling** (or getting it wrong under unequal microbatch token counts, per the bug above): silently multiplies the effective learning rate by `accum_steps`, which at 16-64x accumulation is enough to destabilize or diverge a run that looks correctly configured everywhere else.
- **Clipping per-microbatch instead of on the accumulated gradient**: clips a gradient that hasn't finished accumulating, changing the effective clip threshold in a way that's invisible unless you specifically check where clipping is called relative to the accumulation loop.
- **Missing `no_sync()` under DDP**: not a correctness bug, but a throughput bug — every microbatch triggers a full all-reduce, wasting bandwidth proportional to `accum_steps`.
- **Packed sequences without correcting the denominator**: sequence packing (multiple documents per training sequence) changes the token count per microbatch in ways that make the naive per-microbatch-mean loss bug above especially likely to bite.

## The non-obvious

Gradient accumulation *feels* like a pure memory workaround, but it also functions as a communication-cost dial: for a fixed total token budget, more accumulation steps per optimizer step means proportionally fewer all-reduces, which is a real lever for tuning MFU on a bandwidth-limited cluster independent of the memory motivation. The loss-normalization bug is the sharper lesson, though — it's a case where code that is *locally* correct (each microbatch computes a standard mean-reduced loss, exactly as single-batch training would) becomes *globally* wrong the moment token counts vary across microbatches, and it survived in widely-used training code for years because the mis-weighting is subtle enough not to crash anything, just to quietly change what the model learns.

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
