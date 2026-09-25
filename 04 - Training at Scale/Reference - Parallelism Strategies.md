---
tags: [reference, domain/training-at-scale, level/core]
aliases: [parallelism cheat sheet, DP TP PP SP CP EP comparison, N-D parallelism table]
summary: "Lookup table of DP, ZeRO/FSDP, TP, PP, SP, CP, and EP: what each shards, its collective, comm cost, and failure mode."
---

# Reference - Parallelism Strategies

*Reflects 2026 practice across Megatron-Core, DeepSpeed, PyTorch FSDP2 (see [[Concept - Fully Sharded Data Parallel (FSDP)]]), and TorchTitan. Comm-volume figures are per-step and order-of-magnitude, not byte counts. Profile your own topology before trusting them.*

## The seven dimensions

| Strategy | What it shards | Collective(s) | Comm volume / step | Interconnect need | Memory effect | Typical degree | Primary failure mode |
|---|---|---|---|---|---|---|---|
| **DP** ([[Concept - Data Parallelism and ZeRO]]) | nothing (full replica per rank) | all-reduce (grads), ring algorithm | ≈2× model size in grad bytes¹ | Bandwidth-tolerant, overlaps with backward | none: full model+grad+opt per GPU | 8 – thousands | wasted compute above the [[Concept - Critical Batch Size]] |
| **ZeRO-1/2/3 / FSDP** ([[Concept - Fully Sharded Data Parallel (FSDP)]]) | optimizer state (stage 1), +grads (2), +params (3) | all-gather (params) + reduce-scatter (grads) | ZeRO-1/2 ≈ DDP volume; ZeRO-3 ≈1.5× DDP² | Tolerant if prefetch overlaps compute | (model+grad+opt)/N per GPU | = DP world size | all-gather stall if not overlapped with compute |
| **TP** ([[Concept - Tensor and Pipeline Parallelism]]) | weight matrices within a layer | all-reduce (activations), 2× fwd + 2× bwd per block | one activation tensor, every layer | NVLink required, intra-node only | params / TP degree | ≤ 8 | MFU collapse if TP spans a node boundary |
| **PP** ([[Concept - Tensor and Pipeline Parallelism]]) | layers, into pipeline stages | point-to-point (activations) | one activation tensor per microbatch boundary | Latency-tolerant, inter-node OK | params / #stages (roughly) | 4 – 16+ | fill/drain bubble + stage imbalance |
| **SP** ([[Concept - Sequence and Context Parallelism]]) | norm/dropout/residual region, along sequence | all-gather + reduce-scatter (companion to TP) | ~0 added over TP's own all-reduce | Same requirement as TP (NVLink) | activations / TP degree | = TP degree | inherits TP's node-boundary limit |
| **CP** ([[Concept - Sequence and Context Parallelism]]) | the sequence dimension, for attention | ring send/recv or all-gather of KV blocks | KV-block-sized × ring steps | Latency-sensitive if not overlapped | attention activations O(seq²) → O(seq²/CP) | 2 – 8+, scales with target context | causal load imbalance, online-softmax rescale bugs |
| **EP** ([[Concept - Expert Parallelism]]) | experts, across devices | two all-to-all (dispatch + combine) | tokens × hidden × top-k × 2 | Cross-node all-to-all dominates step time | expert params / EP degree | 8 – 256 | straggler stalls, capacity-drop quality loss |

¹ Ring all-reduce moves ≈2×(N−1)/N of the gradient tensor per rank, treated here as ≈2× model size for N ≥ 8.
² ZeRO-3 replaces DDP's single gradient all-reduce with an all-gather of params (every forward *and* backward) plus a reduce-scatter of grads. That extra all-gather is the ~0.5× tax over plain DDP.

## Composition

$$\text{world size} = DP \times TP \times PP \times CP \times EP$$

Per-GPU memory ≈ $\dfrac{\text{sharded params+grad+opt}}{DP_{\text{shard}}} + \dfrac{\text{activations}}{TP \times CP \times PP}$. The full device-mesh derivation is in [[Pattern - 3D Parallelism Composition]].

| Dimension | Physical placement | Why |
|---|---|---|
| TP | intra-node ([[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]], NVLink ~900 GB/s) | synchronous all-reduce every layer; a slow link stalls every block |
| SP | rides with TP | free activation-memory win, no independent placement decision |
| PP | inter-node (InfiniBand/RoCE) OK | point-to-point, latency-tolerant with enough microbatches |
| DP / ZeRO shard | outermost, spans the whole cluster | bandwidth-tolerant with prefetch/overlap |
| CP | added only as sequence length demands | not needed until context length forces O(seq²) activation memory down |
| EP | orthogonal, on the expert axis, combined as EP × DP | independent of the DP/TP/PP mesh; MoE-specific |

## Connections
- [[Concept - Data Parallelism and ZeRO]] — the mechanism behind the DP and ZeRO-1/2/3 rows.
- [[Concept - Tensor and Pipeline Parallelism]] — the mechanism behind the TP and PP rows, including the pipeline-bubble formula.
- [[Concept - Sequence and Context Parallelism]] — the mechanism behind the SP and CP rows.
- [[Concept - Expert Parallelism]] — the mechanism behind the EP row's dispatch/combine all-to-all cost.
- [[Concept - All-Reduce and Collective Operations]] — the collective-op internals (ring all-reduce, all-gather, reduce-scatter) this table's comm-volume column assumes.
- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — the hardware bandwidth numbers behind the "interconnect need" column.
- [[Pattern - 3D Parallelism Composition]] — how to actually combine these dimensions into a working device mesh.
- [[Decision - Choosing a Parallelism Strategy]] — the decision flow that turns this table into a concrete config for a given cluster.
- [[Concept - Why Models Don't Fit on One GPU]] — the memory pressure that makes every row in this table necessary in the first place.
- [[Concept - Mixture of Experts Architecture]] — what EP is actually sharding: routed experts inside an MoE layer.
- [[Concept - Critical Batch Size]] — the theory of how large a batch DP can profitably scale to before the DP row's "wasted compute" failure mode kicks in.
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — the concrete PyTorch-native implementation of the ZeRO-3 row.
