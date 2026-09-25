---
tags: [concept, domain/hardware-systems, level/core]
aliases: [NVLink, NVSwitch, InfiniBand, RoCE, RoCEv2, GPUDirect RDMA, scale-up networking, scale-out networking]
summary: "GPU-to-GPU links come in two tiers with a 10-18x bandwidth cliff between them, and that cliff dictates where parallelism strategies live."
---

# Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)

> **One-paragraph hook:** A GPU talks to other GPUs two very different ways: a point-to-point fabric to its seven neighbors in the same box, and a network to everything outside it. The bandwidth gap between the two decides where a distributed training job puts tensor parallelism and where it puts data parallelism. Get it wrong and a multi-million-dollar cluster spends its time shipping tensors over the slow path.

## The mechanism

**NVLink** is a point-to-point, high-bandwidth serial link between GPUs, separate from PCIe. On Hopper, NVLink4 gives each GPU ~900 GB/s aggregate, built from 18 links at 50 GB/s each. By itself NVLink only connects GPU pairs wired directly together. For full any-to-any connectivity among all 8 GPUs in a node, NVIDIA adds **NVSwitch**, a crossbar ASIC that every GPU's NVLinks plug into, so any GPU reaches any other at full NVLink bandwidth with no extra hop cost. For communication purposes that makes an 8-GPU DGX/HGX node behave like one big GPU (see [[Concept - Anatomy of an AI Training Cluster]]).

**PCIe is the slow path traffic falls onto when NVLink isn't used or isn't there.** PCIe Gen5 x16 tops out around 64 GB/s, about 14x slower than NVLink4. Older or cost-reduced systems that connect GPUs only through PCIe switches (no NVSwitch) push all inter-GPU traffic through this narrower, higher-latency path. Even on NVLink nodes, host-staged transfers (GPU → host memory → GPU) drop to PCIe speed.

**Node-to-node traffic uses a real network**, either **InfiniBand** or **RoCE (RDMA over Converged Ethernet)**. InfiniBand NDR delivers 400 Gb/s (~50 GB/s) per GPU-attached NIC, as defined by the InfiniBand Trade Association's InfiniBand Architecture Specification. It's a lossless, credit-based fabric built for HPC. RoCEv2 runs the same RDMA semantics (remote direct memory access, bypassing the remote CPU) over standard Ethernet, which is cheaper and reuses Ethernet operational tooling. Ethernet has no native lossless guarantee, though. RoCE fakes it with Priority Flow Control (PFC) and Explicit Congestion Notification (ECN), and mistuning those is a classic large-cluster failure (below).

**GPUDirect RDMA** is what makes either fabric fast for GPU work. The NIC reads and writes GPU HBM directly over PCIe, skipping the CPU and a staging copy through host DRAM. Without it, every cross-node tensor transfer takes an extra GPU→host→NIC→network→host→GPU bounce, which can cut achievable bandwidth by more than half and adds CPU-mediated latency to every collective step.

## In practice

The bandwidth hierarchy, **NVLink (TB/s aggregate) ≫ InfiniBand/RoCE (~50 GB/s) ≫ PCIe host-staged path**, is the design constraint for every distributed-training layout. Tensor parallelism does an [[Concept - All-Reduce and Collective Operations]]-heavy sync on every layer, so it has to stay inside the NVLink domain: one node, or one NVLink-connected rack-scale domain ([[Concept - Rack-Scale Systems and NVLink Domains]]). At that frequency it can't live with the ~50 GB/s scale-out ceiling. Data and pipeline parallelism communicate far less often, and those are what you route across InfiniBand/RoCE between nodes (see [[Concept - Tensor and Pipeline Parallelism]]).

Production clusters wire this physically. Each node has 8 GPUs behind an NVSwitch, and each GPU gets its own NIC ("rail") into a leaf switch, so cross-node traffic never shares a NIC with a same-node neighbor's traffic ([[Concept - Network Topology for AI Clusters]]). NCCL, NVIDIA's collective communication library, schedules ring and tree algorithms across this two-tier topology at runtime ([[Breakdown - NCCL]]). Schedulers matter too. [[Concept - GPU Orchestration on Kubernetes]] has to place pods topology-aware, respecting NVLink domains and rail assignment, or it recreates the affinity failure below at the scheduling layer without anyone noticing. At the buildout level, interconnect bandwidth (NVLink domain size, optics for the scale-out fabric) limits how fast a new cluster comes online as much as GPU allocation does; see [[Deep Dive - The AI Compute Buildout]].

## Failure modes

- **Wrong NUMA / PCIe-switch affinity.** On a multi-socket host, a GPU's NIC can sit on a different CPU socket or PCIe root complex than the GPU doing the transfer. Traffic then crosses the inter-socket link (UPI/Infinity Fabric) and achieved bandwidth silently halves. No error, just a slow all-reduce. Check with `nvidia-smi topo -m` and NCCL topology logs; fix by pinning processes to the right NUMA node.
- **RoCE congestion collapse.** Without correctly tuned PFC and ECN, incast patterns (many senders to one receiver, common in all-to-all MoE dispatch or gradient reduction) set off PFC "pause storms" that cascade back through the fabric, stalling unrelated flows and sometimes the whole rail. Look at switch PFC pause-frame counters and NCCL timeout/hang symptoms (see [[Playbook - Debugging a Hung Distributed Training Job]]).
- **GPUDirect RDMA silently disabled.** A misconfigured driver, IOMMU setting or virtualization layer can push traffic through the CPU-staged bounce buffer instead of direct HBM access. The job runs, 2-3x slower on cross-node collectives. Check `NCCL_DEBUG=INFO` output for `GDRDMA` status and compare achieved bandwidth with the NIC's rated line rate.
- **IB link flaps / bad optics.** A marginal transceiver or cable causes intermittent link resets that look like random stalls on specific ranks. `ibstat` and switch port-error counters isolate the physical link.

## The non-obvious

Single-pair microbenchmarks (e.g., `nccl-tests` between two GPUs) routinely show near-peak bandwidth on a badly misconfigured production topology, because a two-GPU test never exercises NUMA affinity, rail assignment or incast congestion. Those problems only appear at 512+ GPU scale under real all-reduce traffic. Large-lab infra teams run continuous fabric-health checks (synthetic all-reduce sweeps at production scale) for that reason and don't trust a one-time acceptance test.

RoCE vs InfiniBand is also an organizational bet as much as a technical one. RoCE is cheaper and lets you hire generic network engineers, but every large RoCE deployment has PFC-storm war stories that IB deployments don't. On IB, lossless behavior is built into the hardware; on Ethernet it was bolted on afterward.

## Connections

- [[Concept - Anatomy of an AI Training Cluster]] — defines the node/rack/pod hierarchy that NVLink and InfiniBand each occupy one tier of.
- [[Concept - All-Reduce and Collective Operations]] — the traffic pattern that actually rides these links; ring bandwidth math assumes a known per-link bandwidth.
- [[Concept - Network Topology for AI Clusters]] — how the scale-out fabric is wired (fat-tree, rail-optimized) to avoid oversubscribing InfiniBand/RoCE.
- [[Concept - Rack-Scale Systems and NVLink Domains]] — how GB200 NVL72 extends the NVLink domain beyond a single 8-GPU node.
- [[Concept - Tensor and Pipeline Parallelism]] — the parallelism decision this bandwidth hierarchy directly constrains.
- [[Breakdown - NCCL]] — the library that schedules collectives across exactly this two-tier topology.
- [[Concept - GPU Orchestration on Kubernetes]] — schedulers must respect NVLink/rail topology when placing pods, or they recreate the affinity failure mode above.
- [[Deep Dive - The AI Compute Buildout]] — interconnect bandwidth and optics supply are a binding constraint on how fast new clusters can be stood up.

## Sources

- NVIDIA — "NVIDIA H100 Tensor Core GPU Architecture" whitepaper (2022) — NVLink4/NVSwitch bandwidth and topology specs.
- InfiniBand Trade Association — InfiniBand Architecture Specification — the standard behind IB NDR and RDMA semantics.
- NVIDIA/Mellanox — GPUDirect RDMA and RoCEv2 documentation — the direct-HBM-access mechanism and the PFC/ECN requirements for lossless Ethernet.
