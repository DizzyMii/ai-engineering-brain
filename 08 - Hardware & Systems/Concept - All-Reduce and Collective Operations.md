---
tags: [concept, domain/hardware-systems, level/core]
aliases: [all-reduce, AllReduce, collective communication, ring all-reduce, reduce-scatter, all-gather, all-to-all]
summary: "All-reduce, all-gather, reduce-scatter, and all-to-all: the collective ops and ring/tree algorithms distributed training runs on."
---

# Concept - All-Reduce and Collective Operations

> **One-paragraph hook:** Every distributed training step ends with GPUs agreeing on a number — summed gradients, sharded weights, routed tokens — and the algorithm that gets them to agree is not free: it has its own bandwidth and latency cost model that you have to reason about the same way you reason about a kernel's arithmetic intensity. Get the collective wrong and you can double your step time without touching a single line of model code.

## The mechanism

The core op set: **all-reduce** (every GPU ends with the sum — or other reduction — of every GPU's input, used to sync gradients), **all-gather** and **reduce-scatter** (which compose to form an all-reduce, and which [[Concept - Data Parallelism and ZeRO]] uses *separately* to shard optimizer state and weights), **broadcast** (one GPU's data to all), and **all-to-all** (every GPU sends a distinct chunk to every other GPU, the expensive primitive behind [[Concept - Mixture of Experts Architecture]] expert dispatch).

**Ring all-reduce** is the standard bandwidth-optimal implementation: arrange N GPUs in a logical ring, and each GPU only ever talks to its two ring neighbors. Over $2(N-1)$ steps, each GPU sends and receives $\frac{N-1}{N}$ of the data in a reduce-scatter phase, then another $\frac{N-1}{N}$ in an all-gather phase — a total of $\frac{2(N-1)}{N} \times \text{data}$ bytes transferred per GPU, which converges to $2\times\text{data}$ bytes as $N$ grows and, critically, **does not depend on N for the bandwidth term**. That's the "bandwidth-optimal" property: a ring all-reduce of a fixed tensor costs roughly the same bandwidth whether you have 8 GPUs or 800. What *does* grow with N is latency, since the ring takes $2(N-1)$ sequential steps — each one paying a fixed per-hop latency cost even if there were zero bytes to send.

That latency term is why **tree (recursive-doubling/halving) algorithms** exist as the alternative: a tree completes in $O(\log N)$ steps instead of $O(N)$, trading some bandwidth efficiency for much lower latency — the right tradeoff for small tensors or very large GPU counts, where ring's $2(N-1)$ step count starts to dominate. The general cost model is:

$$
T \approx \alpha \cdot \text{steps} + \frac{\text{bytes}}{\text{bandwidth}}
$$

where $\alpha$ is per-step latency. Small tensors are **latency-bound** (the $\alpha \cdot \text{steps}$ term dominates), large tensors are **bandwidth-bound** (the bytes/bandwidth term dominates) — this is exactly why gradient bucketing/fusion exists: coalescing many small per-layer gradient tensors into a few large buffers before all-reducing moves you off the latency-bound regime.

**Hierarchical collectives** exploit the two-tier interconnect described in [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]]: reduce within the fast NVLink domain first, then run one cross-node collective over the much slower InfiniBand/RoCE link between node representatives, then broadcast the result back down. This avoids running N-way collectives directly over the slow scale-out network and is how NCCL scales ring/tree algorithms to tens of thousands of GPUs (see [[Breakdown - NCCL]]).

## In practice

At the scale of a single [[Concept - Anatomy of an AI Training Cluster]] node, gradient all-reduce for data parallelism runs almost entirely inside the NVSwitch domain at close to TB/s effective bandwidth. [[Concept - Tensor and Pipeline Parallelism]]'s per-layer all-reduce is far more frequent than a data-parallel gradient sync, which is exactly why it has to stay inside that fast domain rather than crossing nodes. Across nodes, the achievable collective bandwidth is capped by InfiniBand/RoCE (~50 GB/s per GPU) and by how well the [[Concept - Network Topology for AI Clusters]] avoids oversubscription. [[Concept - Fully Sharded Data Parallel (FSDP)]] makes the reduce-scatter/all-gather split explicit and load-bearing: instead of one big all-reduce per step, it reduce-scatters gradients (each GPU ends up owning and updating only its shard) and all-gathers weights on demand before each layer's forward/backward — the same total bytes moved as an all-reduce, but restructured to also shard memory. All-to-all for MoE expert routing is the collective practitioners fear most in practice: unlike all-reduce, its cost is sensitive to load imbalance across experts, so a poorly balanced router can make the communication step arbitrarily worse than the balanced-case bandwidth math predicts.

## Failure modes

- **Straggler stall**: a ring all-reduce moves at the speed of its slowest participant — one thermally-throttled GPU or one degraded NIC stalls every other GPU in the ring, turning a healthy-looking cluster into a slow one with no single obvious culprit. Detect with per-rank step-time logging or NCCL flight-recorder traces (see [[Playbook - Debugging a Hung Distributed Training Job]]).
- **Mismatched collective calls across ranks → hang, not crash**: if ranks diverge (different op, shape, dtype, or call order — e.g., one rank takes a conditional branch that skips a collective), the collective simply never completes on the ranks still waiting; there's no error, just a watchdog timeout after ~30 minutes by default. Detect by auditing for data-dependent control flow around collective calls.
- **Buffer size/dtype mismatch**: one rank passing a tensor of the wrong shape or dtype into the same collective call as its peers causes an immediate hang or, worse, silently wrong results if the mismatch happens to be shape-compatible.

## The non-obvious

The ring all-reduce's bandwidth-independence-from-N property is frequently misunderstood as "communication cost doesn't grow with cluster size" — it does, just through the latency term, not the bandwidth term. At 8 GPUs, $2(N-1)=14$ steps of fixed latency is noise; at 512 GPUs it's 1022 steps, and if your per-step latency is dominated by an under-provisioned scale-out fabric rather than NVLink, that latency term can eclipse the bandwidth term entirely — which is exactly why production frameworks switch to hierarchical or tree-based collectives past a certain scale rather than running a flat ring across the whole cluster.

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
