---
tags: [concept, domain/hardware-systems, level/core]
aliases: [NVLink, NVSwitch, InfiniBand, RoCE, RoCEv2, GPUDirect RDMA, scale-up networking, scale-out networking]
summary: "GPU-to-GPU links come in two tiers with a 10-18x bandwidth cliff between them, and that cliff dictates where parallelism strategies live."
---

# Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)

> **One-paragraph hook:** A GPU has two fundamentally different ways to talk to another GPU — a point-to-point fabric to its seven neighbors in the same box, and a network fabric to everything outside it — and the bandwidth gap between them is the single fact that decides where a distributed training job puts tensor parallelism versus data parallelism. Get this wrong and you spend a multi-million-dollar cluster shipping tensors over the slow path.

## The mechanism

**NVLink** is a point-to-point, high-bandwidth serial link between GPUs, distinct from PCIe. On Hopper, NVLink4 gives each GPU ~900 GB/s of aggregate bandwidth, built from 18 individual links at 50 GB/s each. On its own, NVLink only connects GPU pairs directly wired together; to get full any-to-any connectivity among all 8 GPUs in a node, NVIDIA adds **NVSwitch** — a crossbar ASIC that every GPU's NVLinks plug into, so any GPU can reach any other GPU at full NVLink bandwidth with no intermediate hop cost. This is what makes an 8-GPU DGX/HGX node behave, for communication purposes, like one big GPU (see [[Concept - Anatomy of an AI Training Cluster]]).

**PCIe is the slow path that traffic falls onto when NVLink isn't used or isn't available.** PCIe Gen5 x16 tops out around 64 GB/s — about 14x slower than NVLink4. Older or cost-reduced systems that connect GPUs only via PCIe switches (no NVSwitch) force all inter-GPU traffic through this narrower, higher-latency path, and even on NVLink-equipped nodes, host-staged transfers (GPU → host memory → GPU) fall back to PCIe speeds.

**Scale-out (node-to-node) uses a real network**, not a proprietary GPU fabric: either **InfiniBand** or **RoCE (RDMA over Converged Ethernet)**. InfiniBand NDR delivers 400 Gb/s (~50 GB/s) per GPU-attached NIC, defined by the InfiniBand Trade Association's InfiniBand Architecture Specification — a lossless, credit-based fabric purpose-built for HPC. RoCEv2 takes the same RDMA semantics (remote direct memory access, bypassing the remote CPU) and runs them over standard Ethernet, which is cheaper and lets you reuse Ethernet operational tooling, but Ethernet has no native lossless guarantee — RoCE has to fake losslessness with Priority Flow Control (PFC) and Explicit Congestion Notification (ECN), and getting that tuning wrong is a classic large-cluster failure mode (below).

**GPUDirect RDMA** is what makes either fabric actually fast for GPU workloads: the NIC reads and writes GPU HBM directly over PCIe, skipping the CPU and a staging copy through host DRAM. Without it, every cross-node tensor transfer pays an extra GPU→host→NIC→network→host→GPU bounce, which can cut achievable bandwidth by more than half and adds CPU-mediated latency to every collective step.

## In practice

The resulting bandwidth hierarchy — **NVLink (TB/s aggregate) ≫ InfiniBand/RoCE (~50 GB/s) ≫ PCIe host-staged path** — is not a curiosity, it's the design constraint for every distributed-training layout. Tensor parallelism, which does an [[Concept - All-Reduce and Collective Operations]]-heavy synchronization on every layer, must stay inside the NVLink domain (one node, or one NVLink-connected rack-scale domain — see [[Concept - Rack-Scale Systems and NVLink Domains]]) because it cannot tolerate the ~50 GB/s scale-out ceiling at that frequency. Data parallelism and pipeline parallelism, which communicate far less often, are the strategies you route across InfiniBand/RoCE between nodes (see [[Concept - Tensor and Pipeline Parallelism]]). A production cluster wires this physically: 8 GPUs per node behind an NVSwitch, and each GPU gets its own NIC ("rail") into a leaf switch, so cross-node traffic never has to share a NIC with a same-node neighbor's traffic (see [[Concept - Network Topology for AI Clusters]]). NCCL, NVIDIA's collective communication library, is what actually schedules ring/tree algorithms across this two-tier topology at runtime (see [[Breakdown - NCCL]]). Cluster schedulers matter here too: [[Concept - GPU Orchestration on Kubernetes]] has to place pods topology-aware, respecting NVLink domains and rail assignment, or it silently recreates the affinity failure mode below at the scheduling layer. At the buildout level, interconnect bandwidth (NVLink domain size, optics for the scale-out fabric) is as much a supply constraint on how fast a new cluster can come online as GPU allocation itself — see [[Deep Dive - The AI Compute Buildout]].

## Failure modes

- **Wrong NUMA / PCIe-switch affinity**: on a multi-socket host, a GPU's NIC may be attached to a different CPU socket or PCIe root complex than the GPU issuing the transfer. Traffic then crosses the inter-socket link (UPI/Infinity Fabric), silently halving achieved bandwidth with no error raised — only a slow all-reduce. Detect with `nvidia-smi topo -m` and NCCL topology logs; fix by pinning processes to the correct NUMA node.
- **RoCE congestion collapse**: without correctly tuned PFC and ECN, incast patterns (many senders to one receiver, common in all-to-all MoE dispatch or gradient reduction) trigger PFC "pause storms" that cascade backward through the fabric, stalling unrelated flows and sometimes the whole rail. Detect via switch PFC pause-frame counters and NCCL timeout/hang symptoms (see [[Playbook - Debugging a Hung Distributed Training Job]]).
- **GPUDirect RDMA silently disabled**: a misconfigured driver, IOMMU setting, or virtualization layer can force traffic through the CPU-staged bounce-buffer path instead of direct HBM access. The job still runs, just 2-3x slower on cross-node collectives — detect by checking `NCCL_DEBUG=INFO` output for `GDRDMA` status and comparing achieved bandwidth against the NIC's rated line rate.
- **IB link flaps / bad optics**: a marginal transceiver or cable produces intermittent link resets, which look like random stalls in specific ranks. `ibstat` and switch port-error counters isolate the physical link.

## The non-obvious

Single-pair micro-benchmarks (e.g., `nccl-tests` between two GPUs) routinely show near-peak bandwidth even when the production topology is badly misconfigured, because a two-GPU test doesn't exercise NUMA affinity, rail assignment, or incast congestion at all. Interconnect problems that never show up in a benchmark suite show up only at 512+ GPU scale under real all-reduce traffic patterns — which is why large-lab infra teams run continuous fabric-health checks (synthetic all-reduce sweeps at production scale) rather than trusting a one-time acceptance test. The RoCE-vs-InfiniBand choice is also as much an organizational bet as a technical one: RoCE is cheaper and lets you hire generic network engineers, but every large RoCE deployment carries war stories about PFC storms that IB deployments simply don't have, because IB's lossless behavior is a first-class hardware property rather than an Ethernet feature bolted on afterward.

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
