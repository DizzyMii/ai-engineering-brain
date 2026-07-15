---
tags: [concept, domain/training-at-scale, level/core]
aliases: [DDP, ZeRO, DeepSpeed ZeRO, ZeRO-1, ZeRO-2, ZeRO-3, ZeRO-Offload, ZeRO-Infinity]
summary: "Replicated-model data parallelism and the ZeRO stages that shard optimizer state, gradients, and parameters to cut redundant per-GPU memory."
---

# Concept - Data Parallelism and ZeRO

> **One-paragraph hook:** Plain data parallelism scales throughput by giving every GPU a full copy of the model and syncing gradients — but it does nothing for capacity, because every rank still pays the full memory bill. [[Concept - Why Models Don't Fit on One GPU]] showed that bill is ~16-20 bytes/param, and most of it — the Adam optimizer state — is pure redundancy across ranks. ZeRO's insight is embarrassingly simple: if every GPU is storing an identical copy of something, shard it instead of replicating it, and reconstruct the full copy only for the instant it's needed.

## The mechanism

**Plain DDP** (distributed data parallel): every rank holds a full model replica, runs forward/backward on its own data shard, and then synchronizes gradients with a ring [[Concept - All-Reduce and Collective Operations]] before every rank independently runs an identical optimizer step:

```python
# DDP training step (per rank), conceptually
loss = model(microbatch)
loss.backward()                     # local gradients
all_reduce(model.grad, op=AVG)      # ring all-reduce, every rank ends up with the same averaged grad
optimizer.step()                    # every rank redundantly recomputes the same update
```

Every rank's memory footprint stays at the full **params + gradients + optimizer state**, regardless of world size. DDP buys you more tokens/sec (more data processed in parallel) but zero additional capacity — a 70B model that doesn't fit on one GPU still doesn't fit under DDP, no matter how many GPUs you add.

**ZeRO** (Rajbhandari et al. 2019, DeepSpeed) removes the redundancy in three stages, each shredding one more pool across the $N$ data-parallel ranks. Using $\Psi$ for parameter count and the standard mixed-precision Adam byte budget (2 bytes bf16 param + 2 bytes grad + 12 bytes fp32 optimizer state = $16\Psi$ total, see [[Concept - Adam and AdamW]] for where the 12 comes from):

| Stage | What's sharded | Per-GPU memory | Extra comm vs DDP |
|---|---|---|---|
| DDP (baseline) | nothing | $16\Psi$ | baseline (1 all-reduce/step) |
| ZeRO-1 | optimizer states | $4\Psi + 12\Psi/N$ | ≈ baseline |
| ZeRO-2 | + gradients | $2\Psi + 14\Psi/N$ | ≈ baseline |
| ZeRO-3 | + parameters | $16\Psi/N$ | ≈1.5x baseline |

ZeRO-1 and ZeRO-2 keep the standard gradient all-reduce (or a reduce-scatter variant) and only change how the *optimizer step* is computed — each rank updates only the slice of parameters it owns and the sharded state is scattered back. Communication volume barely moves relative to DDP.

ZeRO-3 goes further and shards the parameters themselves. Each rank permanently holds only $1/N$ of every layer's weights. Just before a layer's forward (and again before its backward) needs the full weight, every rank **all-gathers** that layer's complete parameters, uses them, and immediately **frees** the gathered copy:

```python
# ZeRO-3 forward pass, per layer, per rank
for layer in model.layers:
    full_params = all_gather(layer.param_shard)   # reconstruct this layer's full weights, just-in-time
    activations = layer.forward(activations, full_params)
    free(full_params)                              # drop the transient full copy; keep only the shard
# backward mirrors this: all-gather params again to compute grads,
# then reduce-scatter the resulting gradients back to the owning rank
```

Because the gather happens twice per layer (forward and backward) instead of once, ZeRO-3's total communication volume comes out to roughly **1.5x** plain DDP's all-reduce volume — the memory-for-bandwidth trade at the heart of the whole design.

```mermaid
flowchart LR
    subgraph DDP["DDP: full replica, every rank"]
        A0["GPU0: P + G + O (full)"]
        A1["GPU1: P + G + O (full)"]
    end
    subgraph Z3["ZeRO-3: sharded at rest, gathered just-in-time"]
        B0["GPU0: P/N + G/N + O/N"] -->|all-gather| C["transient full layer params"]
        B1["GPU1: P/N + G/N + O/N"] -->|all-gather| C
        C -->|reduce-scatter grads| B0
        C -->|reduce-scatter grads| B1
    end
```

**ZeRO-Offload** (Ren et al. 2021) and **ZeRO-Infinity** (Rajbhandari et al. 2021) push the sharded optimizer states and even parameters off the GPU entirely, onto CPU DRAM or NVMe. This buys capacity at severe bandwidth cost — PCIe or NVMe is orders of magnitude slower than HBM — so it's a tool for *fitting* a model on a small GPU count, not for maximizing throughput on a well-provisioned cluster.

## In practice

Concretely: a 70B model's mixed-precision Adam footprint is $16 \times 70\text{e}9 \approx 1.12\text{TB}$. Sharded across 64 ranks under ZeRO-3, that's $1.12\text{TB}/64 \approx 18\text{GB/GPU}$ — a number that fits comfortably even alongside activations on an 80GB H100, where the unsharded version was flatly impossible on a single device.

DeepSpeed exposes the ZeRO stage as a single config flag (`zero_optimization.stage`), which makes it tempting to treat as a pure memory dial — but it isn't free, and the comm cost above is real wall-clock time that has to be *overlapped* with compute to avoid stalling the pipeline. PyTorch's own implementation of the same idea is [[Concept - Fully Sharded Data Parallel (FSDP)]] (functionally ZeRO-3), which composes more natively with [[Concept - Tensor and Pipeline Parallelism]] and other native PyTorch parallelism primitives — see [[Reference - Parallelism Strategies]] for how DP/ZeRO sits alongside TP/PP/SP/CP/EP as one axis of a larger [[Pattern - 3D Parallelism Composition]].

## Failure modes

- **Comm becomes the bottleneck on slow interconnect.** ZeRO-2/3's extra reduce-scatter and all-gather traffic rides the same fabric as everything else; on a cluster without fast intra-node links, the "free" memory win comes with a real throughput tax. Detect via a drop in [[Concept - GPU Memory Hierarchy|HBM]] bandwidth utilization or MFU alongside stable compute time per layer.
- **ZeRO-3 param-gather stalls the pipeline if not overlapped with compute.** If the all-gather for layer $k{+}1$ doesn't start until layer $k$ finishes, every layer pays the full gather latency serially. Fix: prefetch the next layer's gather during the current layer's compute.
- **Bucket sizing and prefetch depth need tuning.** Too-small communication buckets under-utilize the network (many small messages); too-large buckets delay the first send and blow past the memory budget you were trying to save. This is a real tunable, not a set-and-forget default.

## The non-obvious

Most engineers reach for ZeRO-3 as soon as they see an OOM, treating it as "the strong setting." In practice, ZeRO-3's extra gather traffic only pays for itself when you are genuinely parameter-memory-constrained — if ZeRO-1 (shard just the optimizer state, which is the largest of the three pools at 12 of the 16 bytes/param) already gets the model under budget, going to ZeRO-3 anyway can *reduce* throughput for zero additional benefit, because you've traded a communication-cheap configuration for a communication-heavy one you didn't need. Profile the actual per-rank memory breakdown before escalating stages — the OOM might be an activation problem, not a state-sharding problem.

## Connections
- [[Concept - Why Models Don't Fit on One GPU]] — the memory-budget problem ZeRO exists to solve; this note is the primary mechanism for sharding the redundant state it identifies.
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — PyTorch's native implementation of the same ZeRO-3 idea, with a different sharding unit and API.
- [[Concept - All-Reduce and Collective Operations]] — the ring collective DDP uses for gradient sync, and the all-gather/reduce-scatter primitives ZeRO-2/3 build on.
- [[Concept - Tensor and Pipeline Parallelism]] — the orthogonal axis: splitting the model itself rather than sharding its redundant per-replica state.
- [[Reference - Parallelism Strategies]] — places DP/ZeRO alongside every other sharding dimension with its comm pattern and interconnect sensitivity.
- [[Concept - Adam and AdamW]] — the source of the 12-bytes/param optimizer state that ZeRO-1 shards first because it's the largest pool.
- [[Pattern - 3D Parallelism Composition]] — how DP/ZeRO composes with TP and PP in a real large-scale run's device layout.
- [[Concept - GPU Memory Hierarchy]] — the HBM capacity and bandwidth that ZeRO is trading against communication volume.

## Sources
- Rajbhandari et al. (2019) — "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" — introduces the three ZeRO stages and their memory/communication accounting.
- Ren et al. (2021) — "ZeRO-Offload: Democratizing Billion-Scale Model Training" — offloads optimizer states and computation to CPU to fit larger models on fewer GPUs.
- Rajbhandari et al. (2021) — "ZeRO-Infinity: Breaking the GPU Memory Wall for Extreme Scale Deep Learning" — extends offload to NVMe for extreme-scale capacity.
