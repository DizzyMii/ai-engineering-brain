---
tags: [concept, domain/training-at-scale, level/surface]
aliases: []
summary: "Why a modern LLM's parameters, gradients, optimizer states, and activations exceed one GPU's HBM, forcing sharding and parallelism."
---

# Concept - Why Models Don't Fit on One GPU

> **One-paragraph hook:** A 7B-parameter model is 14GB of bf16 weights, which looks like it fits on an 80GB H100 with room to spare. It doesn't. Training draws on four separate memory pools, and once you add gradients, optimizer state and activations, the same 7B model needs well over 100GB before a single training step runs. That gap between "the weights fit" and "the training run fits" is the whole reason distributed training exists.

## The mechanism

Training memory has four consumers. Lumping them together is the single most common sizing mistake.

1. **Parameters**: the weights, 2 bytes each in bf16.
2. **Gradients**: one per parameter, typically 2-4 bytes (bf16 or fp32 accumulation).
3. **Optimizer states**: for Adam/AdamW, an fp32 master-weight copy plus the first and second moment estimates (`m` and `v`), each fp32, so 4 + 4 + 4 = 12 bytes/param. That comes on top of parameters and gradients (see [[Concept - Adam and AdamW]]).
4. **Activations**: intermediate tensors saved in the forward pass for backprop. This pool scales with `batch_size × sequence_length × num_layers × hidden_dim`, not parameter count, so at long context it can dwarf the other three even for a small model.

Add up the first three under standard mixed-precision training (see [[Concept - Mixed Precision Training]]) and you get roughly **16-20 bytes per parameter** with no activations stored yet: 2 (bf16 weight) + 2 (bf16 grad, sometimes fp32) + 12 (Adam states) + a few bytes of slack for fp32 master-weight/grad copies, depending on the recipe.

So a 7B model needs `7e9 × ~16-20 bytes ≈ 112-140 GB` for weights, gradients and optimizer state alone. That's already past an 80GB H100's HBM (see [[Concept - GPU Memory Hierarchy]]) with zero activations. A 70B model needs over 1TB. No single-GPU configuration or clever kernel makes 70B+ dense pretraining fit on one device; the arithmetic rules it out.

Activations add a second axis of pain. Left alone, they grow linearly in layers and roughly with `batch × seq²` for naive attention. **Activation (gradient) checkpointing** trades that away: store a sparse subset of activations (say, one per transformer block) and recompute the rest in the backward pass. Peak activation memory drops from O(layers) to roughly O(√layers) for ~30% extra FLOPs, one of the best compute-for-memory trades in the field (Chen et al. 2016).

## In practice

On a single 80GB GPU with no sharding, the ceiling is a dense model of roughly **3-6B parameters** at reasonable batch/sequence sizes, once activations and framework overhead are counted. Beyond that you have to split something across devices. Either shard the redundant per-GPU state (ZeRO/[[Concept - Fully Sharded Data Parallel (FSDP)]]: same model, less state per rank) or shard the model itself ([[Concept - Tensor and Pipeline Parallelism]]: different layers or tensor slices on different ranks). Every large training run composes these two orthogonal axes.

It is almost always **HBM capacity and bandwidth, not raw FLOPs**, that sets a training run's configuration. A GPU with 10x the compute and the same memory won't train a bigger model. It just finishes the same one faster. That's the memory wall, and it's why [[Concept - The Roofline Model]] (arithmetic intensity vs. peak bandwidth) is the right lens for deciding whether a training step is compute-bound or memory-bound. Per-tensor formulas are in [[Reference - Memory Math for Transformers]].

## Failure modes

- **OOM at step 0**: the static footprint (params + grads + optimizer state, allocated eagerly) already exceeds HBM. Shard state (a ZeRO stage) or lower the model/GPU ratio. It's a sizing bug, not a runtime bug.
- **OOM after N steps**: the static allocation fit, but the activation *peak* (at the longest sequence in a batch, or in one particular layer) or lazy optimizer-state allocation (Adam allocates `m`/`v` on the first `.step()`, not at init) pushes past the limit later. Enable or tune activation checkpointing, shrink the microbatch, or check the allocator for fragmentation. This needs a different diagnostic from the step-0 case.
- **Silent slowdown without OOM**: memory technically suffices but is so tight that the allocator fragments and falls back to smaller, slower allocations. You see an unexplained throughput regression instead of a crash.

## The non-obvious

Sizing a training run by "weights in bf16" is the most common under-provisioning mistake junior engineers make, and it's off by ~8-10x once gradients, Adam state and activations are counted. The more useful corollary: optimizer state (12 bytes/param) is the largest of the three non-activation pools, and when replicated across data-parallel ranks it is *pure redundancy*. Sharding it (ZeRO stage 1) is almost always the best memory win per unit of engineering effort, and it comes before tensor or pipeline parallelism.

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
