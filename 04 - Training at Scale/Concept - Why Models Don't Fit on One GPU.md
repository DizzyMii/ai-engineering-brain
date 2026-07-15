---
tags: [concept, domain/training-at-scale, level/surface]
aliases: []
summary: "Why a modern LLM's parameters, gradients, optimizer states, and activations exceed one GPU's HBM, forcing sharding and parallelism."
---

# Concept - Why Models Don't Fit on One GPU

> **One-paragraph hook:** A 7B-parameter model sounds like it should fit in 14GB of bf16 weights on an 80GB H100 with room to spare. It doesn't — training needs four separate memory pools, not one, and by the time you add gradients, optimizer state, and activations, that same 7B model needs well over 100GB before a single training step runs. This gap between "the weights fit" and "the training run fits" is the entire reason distributed training exists.

## The mechanism

Training memory has four distinct consumers, and conflating them is the single most common sizing mistake:

1. **Parameters** — the weights themselves, 2 bytes each in bf16.
2. **Gradients** — one gradient per parameter, typically 2-4 bytes (bf16 or fp32 accumulation).
3. **Optimizer states** — for Adam/AdamW, an fp32 master-weight copy plus the first and second moment estimates (`m` and `v`), each fp32: 4 + 4 + 4 = 12 bytes/param. This is on top of the parameters and gradients, not instead of them — see [[Concept - Adam and AdamW]].
4. **Activations** — the intermediate tensors saved during the forward pass for use in backprop. This pool doesn't scale with parameter count; it scales with `batch_size × sequence_length × num_layers × hidden_dim`, which means it can dwarf the other three at long context even for a small model.

Sum the first three under standard mixed-precision training (see [[Concept - Mixed Precision Training]]) and you land at roughly **16-20 bytes per parameter** before a single activation is stored: 2 (bf16 weight) + 2 (bf16 grad, sometimes fp32) + 12 (Adam states) + a few bytes of slack for master-weight/grad fp32 copies depending on exact recipe.

Concretely: a 7B model needs `7e9 × ~16-20 bytes ≈ 112-140 GB` for weights + gradients + optimizer state alone — already past an 80GB H100's HBM (see [[Concept - GPU Memory Hierarchy]]) with zero activations stored. A 70B model needs over 1TB. There is no single-GPU configuration, no clever kernel, that makes 70B+ dense pretraining fit on one device; the memory arithmetic makes it flatly impossible.

Activation memory adds a second axis of pain. Unless you intervene, it grows linearly in layers and roughly with `batch × seq²` for naive attention. **Activation (gradient) checkpointing** trades this away: instead of storing every layer's activations, you store a sparse subset (e.g., one per transformer block) and recompute the rest during the backward pass. This drops peak activation memory from O(layers) to roughly O(√layers) at the cost of ~30% extra FLOPs — one of the best compute-for-memory trades in the field (Chen et al. 2016).

## In practice

The practical ceiling: on a single 80GB GPU, without any sharding, you can train a dense model up to roughly **3-6B parameters** at reasonable batch/sequence sizes once you account for activations and framework overhead. Past that, you must split something across devices — either shard the redundant per-GPU state (ZeRO/[[Concept - Fully Sharded Data Parallel (FSDP)]] — same model, less state per rank) or shard the model itself ([[Concept - Tensor and Pipeline Parallelism]] — different layers/tensor slices on different ranks). These are the two orthogonal axes every large training run composes.

A useful framing: it is almost always **HBM capacity and bandwidth, not raw FLOPs**, that binds a training run's configuration. A GPU with 10x the compute but the same memory doesn't let you train a bigger model — it just finishes the same model faster. This is the memory wall, and it's the reason [[Concept - The Roofline Model]] (arithmetic intensity vs. peak bandwidth) is the right lens for reasoning about whether a training step is compute-bound or memory-bound. See [[Reference - Memory Math for Transformers]] for the exact per-tensor formulas.

## Failure modes

- **OOM at step 0**: the static footprint (params + grads + optimizer state, allocated eagerly) already exceeds HBM. Fix: shard state (ZeRO stage) or reduce model/GPU ratio — this is a sizing bug, not a runtime bug.
- **OOM after N steps**: the static allocation fit, but activation *peak* (at the longest sequence in a batch, or during a specific layer) or lazy optimizer-state allocation (Adam allocates `m`/`v` on first `.step()`, not at init) pushes past the limit later. Fix: enable/tune activation checkpointing, reduce microbatch size, or check the allocator for fragmentation — a different bug requiring a different diagnostic than the step-0 case.
- **Silent slowdown without OOM**: memory is technically sufficient but so tight that the allocator fragments and falls back to smaller, slower allocations — visible as unexplained throughput regression, not a crash.

## The non-obvious

The instinct to size a training run by "weights in bf16" is the single most common under-provisioning mistake junior engineers make — it's off by a factor of ~8-10x once gradients, Adam state, and activations are counted. The corollary is more useful: because optimizer state (12 bytes/param) is the largest of the three non-activation pools, and it is *pure redundancy* when replicated across data-parallel ranks, sharding it (ZeRO stage 1) is almost always the highest memory-per-engineering-effort win available before reaching for tensor or pipeline parallelism at all.

## Connections
- [[Reference - Memory Math for Transformers]] — the exact per-tensor byte formulas this note's numbers are drawn from.
- [[Concept - GPU Memory Hierarchy]] — HBM capacity and bandwidth are the physical resource being budgeted here.
- [[Concept - Data Parallelism and ZeRO]] — the primary mechanism for sharding the redundant optimizer/gradient/parameter state across ranks.
- [[Concept - Tensor and Pipeline Parallelism]] — the alternative axis: splitting the model itself rather than its redundant state.
- [[Concept - Mixed Precision Training]] — sets the bytes-per-parameter constants (2 for bf16, 4 for fp32 master) used in the memory budget.
- [[Concept - Adam and AdamW]] — the source of the 12-bytes/param optimizer-state cost.
- [[Concept - The Roofline Model]] — the general framework for reasoning about memory-bound vs. compute-bound regimes.
- [[Concept - Critical Batch Size]] — activation memory and batch size trade off directly against the throughput gains of a larger batch.

## Sources
- Chen et al. (2016) — "Training Deep Nets with Sublinear Memory Cost" — introduced activation checkpointing, trading ~30% recompute for O(√layers) activation memory.
- Rajbhandari et al. (2019) — "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" — the memory accounting (12 bytes/param Adam state) that motivates sharding.
