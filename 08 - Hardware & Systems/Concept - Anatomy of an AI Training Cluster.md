---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "The physical hierarchy of a modern GPU training cluster — GPU, node, rack, pod, datacenter — and the two-tier network that binds them."
---

# Concept - Anatomy of an AI Training Cluster

> **One-paragraph hook:** A "10,000-GPU training run" isn't 10,000 independent devices. It's a strict physical hierarchy of GPU → node → rack → pod → datacenter, held together by two very different networks with an order-of-magnitude bandwidth gap between them. Knowing that hierarchy, and where the bandwidth cliff sits, tells you where a distributed job's parallelism is allowed to go.

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

The **node** is the basic unit. An NVIDIA DGX/HGX H100 packs 8 GPUs fully connected through NVSwitch, so each GPU gets ~900 GB/s of [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)|NVLink4]] bandwidth to every other GPU in the box, all-to-all, at essentially uniform latency. That's what lets [[Concept - All-Reduce and Collective Operations|an all-reduce or all-gather]] run at full speed inside one node.

Above the node the regime changes. Nodes talk over InfiniBand NDR or RoCEv2 at roughly 400 Gb/s (~50 GB/s) per GPU. That's the **bandwidth cliff**: leaving the node gives a GPU roughly 10-18x less bandwidth than staying inside it. Distributed training frameworks insist on keeping [[Concept - Tensor and Pipeline Parallelism|tensor parallelism]] inside one NVLink domain for this reason, and push data- or pipeline-parallel communication, which needs less bandwidth per byte of useful work, out onto the slower inter-node fabric.

Racks group a handful of nodes behind a top-of-rack switch. Pods group many racks behind a spine/leaf fabric ([[Concept - Network Topology for AI Clusters]] covers how that fabric is designed). The datacenter ties pods together along with what makes a cluster usable instead of a pile of GPUs: a parallel filesystem or object store for checkpoints and datasets, head/login nodes for job submission, and a scheduler that places jobs onto the topology (SLURM in HPC-descended shops, [[Concept - GPU Orchestration on Kubernetes|Kubernetes]] in cloud-native ones).

## In practice

Scale as of 2026: NVIDIA's reference SuperPOD design tops out around 256 GPUs as one deployable unit, but frontier-training clusters in production are far larger. Reports put xAI's Colossus at roughly 100,000 H100-class GPUs, and Meta has described building two separate 24,000-GPU clusters for Llama training (2024). [[Reference - The AI Hardware Market]] has the wider buildout context. At that size the cluster behaves less like a bunch of computers and more like one distributed machine whose main design variable is interconnect topology, not GPU count.

The physical limit is power and cooling, not floor space. One H100 draws roughly 700W, and a fully loaded 8-GPU node draws 10 kW or more once NICs, CPUs and memory are counted. Air cooling is already strained at that density. NVIDIA's [[Concept - Rack-Scale Systems and NVLink Domains|GB200 rack-scale systems]] push rack power toward ~120 kW, which forces a wholesale move to liquid cooling. That's a facilities decision, not a chip decision, and it gates how fast a datacenter can stand up new capacity no matter how many GPUs are on order.

## Failure modes

**Parallelism placed across the bandwidth cliff.** The most common distributed-training misconfiguration is letting tensor-parallel communication, which is hungry for both latency and bandwidth, span node boundaries. Symptom: step time dominated by communication and GPU utilization far below expectation. Cause: topology-unaware rank placement. Fix: pin tensor-parallel groups inside one node's NVLink domain and keep data/pipeline parallelism on the InfiniBand tier.

**Hardware failures at scale.** At 10,000+ GPUs, component failure is a *when*, not an *if*; [[Gotchas - Hardware Failures at Scale]] has the taxonomy (ECC errors, fallen-off-the-bus GPUs, flaky NICs). So checkpoint frequency and elastic, fault-tolerant restart are cluster-anatomy decisions as much as training-loop details. The bigger the cluster, the shorter the expected time until some node has to be excluded and the job restarted.

**Power/thermal throttling under sustained load.** A rack or row that hits its power or cooling ceiling downclocks GPUs silently instead of crashing. Throughput drops slowly and is hard to diagnose. DCGM telemetry shows it; job logs don't.

## The non-obvious

Engineers new to distributed training consistently underestimate how big the cliff is. Compared against the aggregate on-node bisection bandwidth NVSwitch provides, leaving the node is close to two orders of magnitude slower per byte-second than staying on NVLink. That ratio is why 3D-parallelism configurations (tensor × pipeline × data) are designed top-down from the physical topology instead of bottom-up from the model architecture. The cluster's shape constrains the parallelism strategy at least as much as the model does.

The part that surprises people moving from single-node to multi-node work: at real frontier scale, the scheduler and the filesystem stop being ops details and matter as much as the GPUs. A checkpoint-and-restart cycle that reads or writes too slowly, or a scheduler that can't place a job topology-aware inside one failure domain, silently caps how much of the cluster you can use.

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
