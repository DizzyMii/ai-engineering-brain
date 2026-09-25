---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [FSDP, FSDP2, PyTorch FSDP]
summary: "PyTorch's native sharded-data-parallel implementation of ZeRO-3: just-in-time all-gather of params, reduce-scatter of grads, made fast by prefetch overlap."
---

# Concept - Fully Sharded Data Parallel (FSDP)

> **One-paragraph hook:** FSDP is how you train a model too big to replicate across data-parallel ranks without reaching for DeepSpeed. It's PyTorch's own implementation of the [[Concept - Data Parallelism and ZeRO]] idea, built into `torch.distributed`, and the default sharding backend for TorchTitan and most native-PyTorch large-model training in 2026. The sharding math is the easy half. What makes FSDP fast, and not merely memory-efficient, is communication overlap, and that's where most of the complexity and most of the bugs are.

## The mechanism

FSDP shards parameters, gradients and optimizer state across the data-parallel group. Functionally that's ZeRO-3: at rest, no rank holds a full copy of the model's trainable state. Sharding happens per **wrapping unit**, typically one transformer block, as set by the wrapping policy. For each unit, in forward order:

```
all-gather the unit's full parameters from every rank   <- overlapped with the PREVIOUS unit's compute
compute forward(unit) using the now-complete parameters
free the full parameters, keep only this rank's local shard
```

and in backward order, symmetrically:

```
all-gather the unit's full parameters again
compute backward(unit) -> contributes to a local gradient shard
reduce-scatter gradients across ranks -> each rank ends up owning only its shard of the gradient
free the full parameters
```

Each rank permanently holds $1/N$ of each unit's parameters, gradients and optimizer state. The full tensor exists only transiently, for the duration of that unit's compute and only in the compute stream, never for all units at once.

**FSDP1** does this with a `FlatParameter`: all of a wrapping unit's parameters are concatenated into one flat 1-D tensor before sharding. That's easy to communicate efficiently, but it complicates per-parameter learning rates, optimizer parameter groups and state-dict reads/writes, since the flat tensor has to be un-flattened to get per-parameter structure back. **FSDP2** switches to per-parameter `DTensor` sharding, where each parameter is its own sharded tensor with a `DeviceMesh` describing the split. It composes cleanly with [[Concept - Tensor and Pipeline Parallelism]] on a 2D+ mesh, and it's what TorchTitan and most 2024-2025-era native-PyTorch training stacks migrated to.

## In practice

FSDP is fast only because the all-gathers overlap with compute. It prefetches the *next* unit's all-gather while the *current* unit is still computing, controlled by `backward_prefetch` and related knobs. With the overlap right, FSDP's communication is nearly hidden behind compute. With it wrong, every unit boundary is a synchronous stall.

The main configuration knobs:
- **`MixedPrecisionPolicy`** sets separate dtypes for parameters, gradient reduction and buffers. The reduce dtype matters more than it looks. Reducing gradients in bf16 at scale loses precision that compounds over thousands of steps, so production configs keep it at fp32 even when compute runs in bf16 (see [[Concept - Mixed Precision Training]]).
- **`sharding_strategy`**: `FULL_SHARD` is the ZeRO-3 equivalent above. `SHARD_GRAD_OP` shards only gradients and optimizer state (roughly ZeRO-2: cheaper communication, more memory). `HYBRID_SHARD` shards within a node and replicates the shard across nodes, giving up some memory savings for a large cut in inter-node traffic. Use it when intra-node NVLink bandwidth dwarfs inter-node InfiniBand/RoCE bandwidth.
- **`CPUOffload`** and composition with activation checkpointing stretch the memory budget further at a throughput cost, the same tradeoff [[Concept - Why Models Don't Fit on One GPU]] describes for recomputation in general.

A common anti-pattern is wrapping the whole model as one FSDP unit. With a single unit there's nothing to prefetch behind, so overlap disappears, and memory peaks at the full model's parameters during the one all-gather: the profile FSDP exists to avoid. Treat wrapping granularity as a tuning axis. Too coarse loses overlap and risks OOM at the all-gather peak; too fine adds per-unit communication overhead that can dominate for small blocks.

## Failure modes

- **Wrong wrapping granularity.** Too coarse OOMs or serializes communication (see above). Too fine multiplies the number of small collectives, each paying a fixed per-call overhead that coarser grouping would have amortized.
- **bf16 reduce dtype silently losing gradient precision.** No crash, no obvious signal. Convergence just gets slower and noisier, and it's easy to blame the optimizer or LR schedule instead of the reduction dtype.
- **Sharded state-dict pitfalls.** Saving and loading a sharded checkpoint needs the same DTensor/DCP machinery on both ends (see [[Concept - Distributed Checkpointing]]). Loading into a differently sharded mesh, or mixing FSDP1 `FlatParameter` state dicts with FSDP2 DTensor ones, throws shape or key-mismatch errors that people often debug as model-architecture bugs.
- **Tensor parallelism needs an explicit 2D `DeviceMesh`.** FSDP's DP dimension and TP's intra-node dimension have to be composed deliberately (see [[Pattern - 3D Parallelism Composition]]). Get the mesh ordering wrong and you get an incorrect or badly imbalanced sharding, with no crash.

## The non-obvious

The sharding arithmetic is the easy part: DeepSpeed ZeRO-3 shards identically, and the memory-reduction formula is a one-liner. The engineering is in scheduling. A naive stop-the-world all-gather before every unit's forward would make FSDP *slower* than plain [[Concept - Data Parallelism and ZeRO|DDP]] despite using far less memory, because communication and compute run serially. Most FSDP performance debugging ends up being about prefetch depth and wrapping granularity. The sharding is essentially always correct; the throughput and the bugs are in the overlap schedule.

## Connections
- [[Concept - Data Parallelism and ZeRO]] — the ZeRO algorithm FSDP is PyTorch's native implementation of.
- [[Concept - Distributed Checkpointing]] — sharded checkpoint save/load, and the reshard-on-load problem this note's state-dict failure mode points to.
- [[Concept - All-Reduce and Collective Operations]] — the all-gather and reduce-scatter primitives FSDP's per-unit cycle is built from.
- [[Snippet - FSDP Minimal Setup]] — a runnable configuration of the wrapping policy, mixed-precision policy, and sharding strategy described here.
- [[Pattern - 3D Parallelism Composition]] — how FSDP's DP-dimension sharding composes with TP and PP on a shared device mesh.
- [[Concept - Mixed Precision Training]] — governs the parameter, compute, and reduce dtypes FSDP's `MixedPrecisionPolicy` configures.
- [[Concept - GPU Memory Hierarchy]] — the HBM budget FSDP's per-unit all-gather/free cycle is managing against.
- [[Decision - Full Fine-Tuning vs PEFT]] — FSDP is the same mechanism used for full-parameter fine-tuning at multi-GPU scale, not only pretraining.
- [[Breakdown - DeepSeek-V3 Training]] — a frontier-scale run that pushes sharding and precision further than FSDP's default recipe, useful as a comparison point for where the "just use FSDP" default stops being sufficient.
- [[Concept - Tensor and Pipeline Parallelism]] — the dimension FSDP2's per-parameter DTensor sharding composes with on a shared device mesh.
- [[Concept - Why Models Don't Fit on One GPU]] — the same recompute-for-memory tradeoff that CPUOffload and activation-checkpointing composition extend further.

## Sources
- Rajbhandari et al. (2020) — "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" — the sharding algorithm FSDP realizes.
- Zhao et al. (2023) — "PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel" — the PyTorch-native implementation, its `FlatParameter` design, and the prefetch/overlap engineering this note's non-obvious section centers on.
