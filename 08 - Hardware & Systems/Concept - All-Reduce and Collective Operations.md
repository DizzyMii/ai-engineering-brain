---
tags: [concept, domain/hardware-systems, level/core]
aliases: [all-reduce, AllReduce, collective communication, ring all-reduce, reduce-scatter, all-gather, all-to-all]
summary: "All-reduce, all-gather, reduce-scatter, and all-to-all: the collective ops and ring/tree algorithms distributed training runs on."
---

# Concept - All-Reduce and Collective Operations

> **One-paragraph hook:** Every distributed training step ends with GPUs agreeing on a number: summed gradients, sharded weights, routed tokens. The algorithm that gets them there has its own bandwidth and latency cost model, and you have to reason about it the way you reason about a kernel's arithmetic intensity. Pick the wrong collective and you can double step time without changing a line of model code.

## The mechanism

The core ops:
- **all-reduce**: every GPU ends up with the sum (or other reduction) of every GPU's input. Used to sync gradients.
- **all-gather** and **reduce-scatter**: together they make an all-reduce, and [[Concept - Data Parallelism and ZeRO]] uses them *separately* to shard optimizer state and weights.
- **broadcast**: one GPU's data to all.
- **all-to-all**: every GPU sends a distinct chunk to every other GPU. It's the expensive primitive behind expert dispatch in [[Concept - Mixture of Experts Architecture]].

**Ring all-reduce** is the standard bandwidth-optimal implementation. Put N GPUs in a logical ring; each only talks to its two neighbors. Over $2(N-1)$ steps, each GPU sends and receives $\frac{N-1}{N}$ of the data in a reduce-scatter phase, then another $\frac{N-1}{N}$ in an all-gather phase. That's $\frac{2(N-1)}{N} \times \text{data}$ bytes per GPU in total, which approaches $2\times\text{data}$ bytes as $N$ grows, and **the bandwidth term doesn't depend on N**. That's what "bandwidth-optimal" means: a ring all-reduce of a fixed tensor costs about the same bandwidth on 8 GPUs or 800. Latency does grow with N, because the ring takes $2(N-1)$ sequential steps and each pays a fixed per-hop latency even with zero bytes to send.

**Tree (recursive-doubling/halving) algorithms** exist because of that latency term. A tree finishes in $O(\log N)$ steps instead of $O(N)$, giving up some bandwidth efficiency for much lower latency. That's the right trade for small tensors or very large GPU counts, where ring's $2(N-1)$ step count starts to dominate. The general cost model:

$$
T \approx \alpha \cdot \text{steps} + \frac{\text{bytes}}{\text{bandwidth}}
$$

where $\alpha$ is per-step latency. Small tensors are **latency-bound** (the $\alpha \cdot \text{steps}$ term dominates) and large ones are **bandwidth-bound** (bytes/bandwidth dominates). Gradient bucketing/fusion exists for this reason: coalescing many small per-layer gradient tensors into a few large buffers before the all-reduce gets you out of the latency-bound regime.

**Hierarchical collectives** use the two-tier interconnect from [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]]. Reduce inside the fast NVLink domain first, run one cross-node collective between node representatives over the much slower InfiniBand/RoCE link, then broadcast the result back down. N-way collectives never run directly over the slow scale-out network, and that's how NCCL scales ring and tree algorithms to tens of thousands of GPUs (see [[Breakdown - NCCL]]).

## In practice

Inside a single [[Concept - Anatomy of an AI Training Cluster]] node, the data-parallel gradient all-reduce runs almost entirely in the NVSwitch domain at close to TB/s effective bandwidth. The per-layer all-reduce in [[Concept - Tensor and Pipeline Parallelism]] happens far more often than a data-parallel gradient sync, so it has to stay inside that fast domain and not cross nodes. Across nodes, collective bandwidth is capped by InfiniBand/RoCE (~50 GB/s per GPU) and by how well the [[Concept - Network Topology for AI Clusters]] avoids oversubscription.

[[Concept - Fully Sharded Data Parallel (FSDP)]] makes the reduce-scatter/all-gather split explicit and depends on it. Instead of one big all-reduce per step, it reduce-scatters gradients (each GPU owns and updates only its shard) and all-gathers weights on demand before each layer's forward/backward. Total bytes moved match an all-reduce, restructured so memory is sharded too.

The collective practitioners fear most is all-to-all for MoE expert routing. Its cost is sensitive to load imbalance across experts, which all-reduce's isn't, so a badly balanced router can make the communication step arbitrarily worse than the balanced-case bandwidth math predicts.

## Failure modes

- **Straggler stall.** A ring all-reduce moves at the speed of its slowest participant. One thermally throttled GPU or one degraded NIC stalls every other GPU in the ring, and a healthy-looking cluster goes slow with no obvious culprit. Catch it with per-rank step-time logging or NCCL flight-recorder traces (see [[Playbook - Debugging a Hung Distributed Training Job]]).
- **Mismatched collective calls across ranks → hang, not crash.** If ranks diverge (different op, shape, dtype, or call order; say one rank takes a conditional branch that skips a collective), the collective never completes on the ranks still waiting. There's no error, only a watchdog timeout after ~30 minutes by default. Audit for data-dependent control flow around collective calls.
- **Buffer size/dtype mismatch.** One rank passing a tensor of the wrong shape or dtype into the same collective as its peers causes an immediate hang, or worse, silently wrong results if the mismatch happens to be shape-compatible.

## The non-obvious

People often read the ring's bandwidth independence from N as "communication cost doesn't grow with cluster size." It does grow, through the latency term. At 8 GPUs, $2(N-1)=14$ steps of fixed latency is noise. At 512 GPUs it's 1022 steps, and if per-step latency is set by an under-provisioned scale-out fabric instead of NVLink, the latency term can swamp the bandwidth term. Production frameworks switch to hierarchical or tree-based collectives past a certain scale instead of running one flat ring across the whole cluster.

## Connections

- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — the physical bandwidth numbers the ring/tree cost model plugs into.
- [[Breakdown - NCCL]] — the library that actually implements ring, tree, and hierarchical collectives on NVIDIA hardware.
- [[Concept - Data Parallelism and ZeRO]] — the primary consumer of all-reduce/reduce-scatter/all-gather for gradient and state synchronization.
- [[Concept - Tensor and Pipeline Parallelism]] — tensor parallelism's per-layer all-reduce is why it must stay inside the fast NVLink domain.
- [[Concept - Mixture of Experts Architecture]] — the source of the imbalance-sensitive all-to-all collective.
- [[Playbook - Debugging a Hung Distributed Training Job]] — the operational procedure for diagnosing the straggler and mismatch failures above.
- [[Concept - Anatomy of an AI Training Cluster]] — the node/rack hierarchy that hierarchical collectives are built to exploit.
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — restructures the all-reduce into explicit reduce-scatter + all-gather to also shard memory.

## Sources

- Real-world implementation: NVIDIA NCCL — the de facto reference implementation of ring and tree all-reduce for GPU clusters (see [[Breakdown - NCCL]] for internals).
- Patarasuk & Yuan (2009) — "Bandwidth Optimal All-reduce Algorithms for Clusters of Workstations" — the ring all-reduce bandwidth-optimality result underlying the $2(N-1)/N$ formula.
