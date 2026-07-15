---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "The physical hierarchy of a modern GPU training cluster — GPU, node, rack, pod, datacenter — and the two-tier network that binds them."
---

# Concept - Anatomy of an AI Training Cluster

> **One-paragraph hook:** A "10,000-GPU training run" is not 10,000 independent devices — it is a strict physical hierarchy of GPU → node → rack → pod → datacenter, glued together by two fundamentally different networks with an order-of-magnitude bandwidth gap between them. Understanding that hierarchy, and specifically where the bandwidth cliff sits, is what tells you where a distributed training job's parallelism strategy is even allowed to go.

## The mechanism

```
   GPU ── NVLink4, ~900 GB/s ──►  [ 8-GPU node, NVSwitch: all-to-all ]
                                            │
                              InfiniBand NDR / RoCEv2
                              ~400 Gb/s (≈50 GB/s) per GPU
                                            │
                        [ Rack: several nodes + top-of-rack switch ]
                                            │
                          [ Pod: many racks, spine/leaf fabric ]
                                            │
              [ Datacenter: multiple pods, parallel filesystem,
                head/login nodes, scheduler (SLURM or Kubernetes) ]
```

The **node** is the atomic building block: an NVIDIA DGX/HGX H100 packs 8 GPUs fully connected through NVSwitch, giving each GPU ~900 GB/s of [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)|NVLink4]] bandwidth to every other GPU in the box, all-to-all, at essentially uniform latency — the physical substrate that lets [[Concept - All-Reduce and Collective Operations|an all-reduce or all-gather]] run at full speed inside one node. Everything above the node is a different regime: nodes talk to each other over InfiniBand NDR or RoCEv2, delivering roughly 400 Gb/s (~50 GB/s) per GPU. That is the **bandwidth cliff**: leaving the node costs a GPU roughly 10-18x less bandwidth than staying inside it. This single fact is why distributed training frameworks are so insistent about keeping [[Concept - Tensor and Pipeline Parallelism|tensor parallelism]] confined to a single NVLink domain and pushing data- or pipeline-parallel communication — which needs less bandwidth per byte of useful work — out across the slower inter-node fabric.

Above the node, racks group a handful of nodes behind a top-of-rack switch; pods group many racks behind a spine/leaf fabric (see [[Concept - Network Topology for AI Clusters]] for how that fabric is actually designed); and the datacenter ties multiple pods together along with the supporting cast that makes a cluster usable rather than just a pile of GPUs: a parallel filesystem or object store for checkpoints and datasets, head/login nodes for job submission, and a scheduler — SLURM in HPC-descended shops, or [[Concept - GPU Orchestration on Kubernetes|Kubernetes]] in cloud-native ones — that places jobs onto the topology.

## In practice

Scale realities as of 2026: NVIDIA's reference SuperPOD design tops out around 256 GPUs as a single deployable unit, but production frontier-training clusters run far larger — reports put xAI's Colossus cluster at roughly 100,000 H100-class GPUs, and Meta has described building two separate 24,000-GPU clusters for Llama training (2024); see [[Reference - The AI Hardware Market]] for the broader buildout context behind these numbers. At that scale the cluster is no longer "a bunch of computers" — it is closer to a single distributed machine whose interconnect topology, not its GPU count, is the primary design variable.

Power and cooling are the binding physical constraint, not floor space. A single H100 draws roughly 700W; a fully loaded 8-GPU node draws 10 kW or more once NICs, CPUs, and memory are included. At that density, air cooling is already strained; NVIDIA's [[Concept - Rack-Scale Systems and NVLink Domains|GB200 rack-scale systems]] push rack power toward ~120 kW, which forces a wholesale move to liquid cooling — a facilities decision, not a chip decision, that gates how fast a datacenter can actually stand up new capacity regardless of how many GPUs are on order.

## Failure modes

**Parallelism placed across the bandwidth cliff:** the most common distributed-training misconfiguration is letting tensor-parallel communication — which is latency- and bandwidth-hungry — span node boundaries. Symptom: step time dominated by communication with GPU utilization far below expectation; cause is topology-unaware rank placement; fix is pinning tensor-parallel groups inside a single node's NVLink domain and confining data/pipeline parallelism to the InfiniBand tier.

**Hardware failures at scale:** at 10,000+ GPUs, component failure is a *when*, not an *if* — see [[Gotchas - Hardware Failures at Scale]] for the taxonomy (ECC errors, fallen-off-the-bus GPUs, flaky NICs). The practical consequence is that checkpoint frequency and elastic/fault-tolerant job restart are cluster-anatomy decisions, not just a training-loop nicety, because the larger the cluster the shorter the expected mean time between some node needing to be excluded and the job restarted.

**Power/thermal throttling under sustained load:** a rack or row hitting its power or cooling ceiling silently downclocks GPUs rather than crashing, producing a slow, hard-to-diagnose drop in throughput rather than a clean failure — detectable via DCGM telemetry, not via job logs.

## The non-obvious

New distributed-training engineers consistently underestimate the bandwidth cliff's magnitude: it isn't "somewhat slower" to leave the node, it is close to two orders of magnitude slower per byte-second than staying inside NVLink once you compare against the aggregate on-node bisection bandwidth NVSwitch provides. That single ratio is why 3D-parallelism configurations (tensor × pipeline × data) are designed top-down from the physical topology rather than bottom-up from the model architecture — the cluster's shape constrains the parallelism strategy at least as much as the model does. The corollary that surprises people moving from single-node to multi-node work: at genuine frontier scale, the scheduler and the filesystem stop being "ops details" and become as load-bearing as the GPUs themselves, because a checkpoint-and-restart cycle that takes too long to read/write, or a scheduler that can't topology-aware-place a job inside one failure domain, silently caps the effective size of cluster you can actually use.

## Connections
- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — the exact bandwidth numbers and mechanisms (NVSwitch, GPUDirect RDMA) behind the two-tier network this note describes.
- [[Concept - Network Topology for AI Clusters]] — how the fat-tree/rail-optimized fabric above the node is actually designed at 10k-100k GPU scale.
- [[Concept - All-Reduce and Collective Operations]] — the communication primitives whose cost model is shaped directly by this physical hierarchy.
- [[Concept - Tensor and Pipeline Parallelism]] — the parallelism strategy whose placement is dictated by the NVLink-vs-InfiniBand bandwidth cliff.
- [[Concept - Rack-Scale Systems and NVLink Domains]] — the frontier extension of "the node" where NVLink domains now span an entire rack (GB200 NVL72).
- [[Gotchas - Hardware Failures at Scale]] — the failure taxonomy that turns cluster size from a scaling win into an operational tax.
- [[Concept - GPU Orchestration on Kubernetes]] — one of the two dominant schedulers (alongside SLURM) that place jobs onto this physical hierarchy.
- [[Reference - The AI Hardware Market]] — the market context for why clusters of this scale exist and who is building them, as of 2026.

## Sources
- NVIDIA (2022) — "NVIDIA DGX H100 System Architecture" whitepaper — the node-level NVSwitch/NVLink topology and per-GPU bandwidth figures cited here.
- Meta AI (2024) — "Building Meta's GenAI Infrastructure" — describes the two 24,000-GPU H100 clusters built for Llama training, a real-world production-scale data point.
