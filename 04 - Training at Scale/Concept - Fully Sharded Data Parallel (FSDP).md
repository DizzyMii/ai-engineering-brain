---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [FSDP, FSDP2, PyTorch FSDP]
summary: "PyTorch's native sharded-data-parallel implementation of ZeRO-3: just-in-time all-gather of params, reduce-scatter of grads, made fast by prefetch overlap."
---

# Concept - Fully Sharded Data Parallel (FSDP)

> **One-paragraph hook:** FSDP is how you train a model too big to replicate across data-parallel ranks without reaching for DeepSpeed — it's PyTorch's own realization of the [[Concept - Data Parallelism and ZeRO]] idea, built into `torch.distributed` and the default sharding backend for TorchTitan and most native-PyTorch large-model training in 2026. The sharding math is the easy half; the reason FSDP is fast rather than merely memory-efficient is a communication-overlap engineering problem, and that's where most of the actual complexity — and most of the bugs — live.

## The mechanism

FSDP shards parameters, gradients, and optimizer state across the data-parallel group, functionally equivalent to ZeRO-3: no rank ever holds a full copy of the model's trainable state at rest. The unit of sharding is not the whole model but a **wrapping unit** — typically one transformer block — set by the wrapping policy. For each unit, in forward order:

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

Every rank permanently holds only $1/N$ of each unit's parameters, gradients, and optimizer state; the full tensor exists transiently, only for the duration of that unit's compute, and only in the compute stream — never simultaneously across all units.

**FSDP1** implements this with a `FlatParameter`: all of a wrapping unit's parameters are concatenated into one flat 1-D tensor before sharding, which is simple to communicate efficiently but complicates per-parameter learning rates, optimizer parameter groups, and reading/writing state dicts, since the flat tensor has to be un-flattened to recover per-parameter structure. **FSDP2** replaces this with per-parameter `DTensor` sharding — each parameter is its own sharded tensor with a `DeviceMesh` describing how it's split — which composes cleanly with [[Concept - Tensor and Pipeline Parallelism]] on a 2D+ mesh and is the migration path TorchTitan and most 2024-2025-era native-PyTorch training stacks moved to.

## In practice

The whole design is only fast because the all-gathers overlap with compute rather than stalling for it: FSDP prefetches the *next* unit's all-gather while the *current* unit is still computing, controlled by `backward_prefetch` and related knobs. Get this overlap right and FSDP's communication is nearly hidden behind compute; get it wrong and every unit boundary becomes a synchronous stall.

Key configuration surface:
- **`MixedPrecisionPolicy`** sets separate dtypes for parameters, gradient reduction, and buffers — the reduce dtype matters more than it looks: reducing gradients in bf16 at scale loses precision that compounds across thousands of steps, so production configs keep the reduce dtype at fp32 even when compute runs in bf16 (see [[Concept - Mixed Precision Training]]).
- **`sharding_strategy`**: `FULL_SHARD` is the ZeRO-3 equivalent described above; `SHARD_GRAD_OP` shards only gradients and optimizer state (roughly ZeRO-2, cheaper communication, higher memory); `HYBRID_SHARD` shards within a node and replicates the shard across nodes, trading some memory savings for a large cut in inter-node communication — useful when intra-node NVLink bandwidth dwarfs inter-node InfiniBand/RoCE bandwidth.
- **`CPUOffload`** and composition with activation checkpointing extend the memory budget further, at a throughput cost, the same tradeoff [[Concept - Why Models Don't Fit on One GPU]] describes for recomputation generally.

A common anti-pattern: wrapping the entire model as a single FSDP unit. This defeats overlap entirely (there's nothing to prefetch behind, since only one unit exists) and peaks at full-model parameter memory during the one all-gather — exactly the memory profile FSDP exists to avoid. Wrapping granularity is a real tuning axis, not a default to leave alone: too coarse loses overlap and risks OOM at the all-gather peak, too fine adds per-unit communication overhead that can dominate for small blocks.

## Failure modes

- **Wrong wrapping granularity**: too coarse OOMs or serializes communication (see above); too fine multiplies the number of small collectives, adding fixed per-call overhead that a coarser grouping would have amortized.
- **bf16 reduce dtype silently losing gradient precision**: no crash, no obvious signal — just a slower, noisier convergence that's easy to misattribute to the optimizer or LR schedule instead of the reduction dtype.
- **Sharded state-dict pitfalls**: saving/loading a sharded checkpoint requires the same DTensor/DCP machinery on both ends (see [[Concept - Distributed Checkpointing]]); loading a sharded checkpoint into a differently-sharded mesh, or mixing FSDP1 `FlatParameter` state dicts with FSDP2 DTensor state dicts, produces shape or key-mismatch errors that are often mistakenly debugged as model-architecture bugs.
- **Combining with tensor parallelism requires an explicit 2D `DeviceMesh`**: FSDP's DP dimension and TP's intra-node dimension have to be composed deliberately (see [[Pattern - 3D Parallelism Composition]]); getting the mesh ordering wrong silently produces an incorrect or badly imbalanced sharding rather than a crash.

## The non-obvious

The sharding arithmetic in FSDP is not the hard part — DeepSpeed ZeRO-3 shards identically, and the memory-reduction formula is a one-liner. The actual engineering surface is scheduling: a naive stop-the-world all-gather before every unit's forward would make FSDP *slower* than plain [[Concept - Data Parallelism and ZeRO|DDP]] despite using far less memory, because it serializes communication and compute instead of overlapping them. In practice, most FSDP performance debugging sessions are about prefetch depth and wrapping granularity, not about whether the sharding math is correct — the sharding is essentially always correct; the overlap schedule is where the actual throughput, and the actual bugs, live.

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
