---
tags: [moc, domain/hardware-systems, level/surface]
aliases: []
summary: "Map of the hardware domain: GPU/TPU internals, kernel programming, cluster networking, and the failure modes that surface only at scale."
---

# MOC - Hardware & Systems

This domain owns the physical substrate every other layer of the vault takes for granted: what a GPU or TPU actually does with a matmul, why memory bandwidth rather than raw FLOPs decides most kernels' speed, and how thousands of accelerators get wired into a single training run. It covers the execution model (CUDA, warps, tensor cores), the performance math (roofline, MFU, memory formulas) that turns hardware specs into dollars per token, the kernel-level tools (Triton, FlashAttention) that close the gap between theoretical and achieved throughput, and the networking and failure modes that only appear once you're running on hundreds or thousands of chips. It matters because every claim elsewhere in this vault about training cost, inference latency, or model scale is ultimately bounded by the numbers in this domain — HBM bandwidth, NVLink bisection bandwidth, MFU — not by algorithmic cleverness alone. An architecture that looks elegant on paper is unusable in practice if it doesn't map onto this hardware's memory hierarchy and interconnect topology.

## Start here

- **Surface** → [[Concept - Why GPUs for Deep Learning]] — why dense matmul lands on SIMT throughput hardware; the fact everything else in this domain assumes.
- **Core** → [[Concept - The Roofline Model]] — the single plot that decides whether you're optimizing compute or memory bandwidth; everything downstream reasons from it.
- **Advanced** → [[Deep Dive - FlashAttention]] — the flagship worked example of tiling, online softmax, and HBM avoidance landing in one real, load-bearing kernel.
- **Frontier** → [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — the current hardware generation everything frontier-tier here (FP8, warp specialization, rack-scale NVLink) targets.
- **Unicorn** → [[Lore - Silent Data Corruption at Scale]] — the failure mode that throws no error, just quietly corrupts a training run; the war story behind why fleets run canary checks.

## Why hardware shapes everything

- [[Concept - Why GPUs for Deep Learning]] — dense matmul is embarrassingly parallel and bandwidth-hungry, exactly what SIMT throughput hardware is built for.
- [[Concept - The Memory Wall]] — compute has outgrown memory bandwidth for decades, so most deep learning kernels are bottlenecked by data movement, not arithmetic.
- [[Concept - Anatomy of an AI Training Cluster]] — the physical hierarchy (GPU → node → rack → pod → datacenter) and the two-tier network that binds it.

## GPU execution model and memory

- [[Concept - GPU Memory Hierarchy]] — registers, shared memory/L1, L2, HBM: roughly 1000x capacity traded for roughly 1000x bandwidth at each tier.
- [[Concept - The CUDA Programming Model]] — the thread-block-grid hierarchy that maps scalar-looking code onto SM/warp hardware; performance means thinking in warps, not threads.
- [[Concept - Tensor Cores]] — warp-collective matrix-multiply-accumulate units that supply ~90% of a modern GPU's FLOPs, and must be explicitly targeted to be used.
- [[Concept - Occupancy and Latency Hiding]] — how a GPU hides 400-800 cycle HBM latency by keeping many warps resident per SM, and why more occupancy isn't always faster.
- [[Concept - Matmul Tiling on GPUs]] — GEMM tiled to threadblock/warp/instruction levels so operands are reused, not reloaded, from HBM.
- [[Concept - Kernel Fusion]] — combining ops into one kernel so intermediates stay on-chip instead of round-tripping HBM; the top lever for memory-bound ops.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the two lowest-level GPU memory rules, plus the padding and swizzle fixes for when you break them.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — the Hopper pattern behind peak GEMM and FA3: producer warpgroups issue TMA copies, consumers run wgmma, synced by mbarriers.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — why real GPUs drift below spec — boost clocks, power caps, throttling — creating stragglers and MFU variance.
- [[Concept - Systolic Arrays]] — the 2D grid-of-MACs dataflow behind TPUs, reusing each SRAM read across a whole row without a register file.

## Measuring performance

- [[Concept - The Roofline Model]] — predicts whether a kernel is compute- or memory-bound from FLOPs-per-byte, on a single plot.
- [[Concept - Model FLOPs Utilization (MFU)]] — the fraction of a chip's peak FLOPs actually spent on useful model math; real runs land at 30-60% and it sets $/token directly.
- [[Reference - Memory Math for Transformers]] — byte formulas for parameters, optimizer state, activations, and KV cache — what actually fits on a GPU, worked for 7B and 70B.

## Kernel programming and tooling

- [[Concept - Triton]] — OpenAI's Python-embedded kernel language: program at the block level, let the compiler handle threading and coalescing.
- [[Snippet - Fused Softmax Kernel in Triton]] — a runnable kernel fusing row-max, exp, sum, and divide into one bandwidth-bound pass, replacing four HBM round-trips.
- [[Snippet - A Minimal FlashAttention Kernel in Triton]] — a runnable forward FlashAttention kernel showing the online-softmax streaming loop that keeps the N×N score matrix out of HBM.
- [[Deep Dive - FlashAttention]] — how attention is tiled with online softmax and recomputation so the O(N²) score matrix never touches HBM, across v1-v3.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the end-to-end procedure to find a slow kernel's true bottleneck via Nsight Systems/Compute and apply the fix that actually moves the needle.
- [[Gotchas - GPU Kernel Performance]] — the silent 2-10x slowdowns that never raise an error: coalescing, bank conflicts, tensor-core misses, spills, launch overhead.

## Networking and cluster scale

- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — a 10-18x bandwidth cliff separates the two link tiers, and that cliff dictates where parallelism strategies live.
- [[Concept - All-Reduce and Collective Operations]] — all-reduce, all-gather, reduce-scatter, all-to-all: the ring/tree algorithms distributed training runs on.
- [[Concept - Network Topology for AI Clusters]] — how fat-tree/Clos fabrics wire 10k-100k+ GPUs; topology, not link speed, caps collective bandwidth at scale.
- [[Concept - Rack-Scale Systems and NVLink Domains]] — extending the NVLink scale-up domain from an 8-GPU node to a 72-GPU rack moves the bandwidth cliff and rewrites parallelism math.
- [[Breakdown - NCCL]] — how NVIDIA's collective library discovers cluster topology, builds rings/trees, and pipelines the reduce-and-copy kernels behind nearly every distributed job.

## Hardware platforms and precision

- [[Breakdown - The Google TPU]] — the systolic MXU, compiler-managed VMEM, ICI torus plus optical circuit switches, and the compile-first XLA model, as one system.
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — how H100/H200 and B200/GB200 are actually built: SM/tensor-core generations, async data movement, HBM, the rack-scale turn.
- [[Concept - FP8 and Low-Precision Hardware Formats]] — the 8-bit and 4-bit floating-point formats tensor cores execute natively, and the block-scaling machinery that keeps them from over/underflowing.
- [[Reference - AI Accelerator Landscape]] — date-stamped 2026 spec comparison of NVIDIA GPUs, Google TPUs, AMD MI300, AWS Trainium/Inferentia, and inference ASICs.
- [[Decision - Selecting GPUs for Training and Inference]] — pick by capacity fit, then compute- vs memory-bound profile, then latency/throughput SLO, then $/hr — not by peak TFLOPs.

## Operating at scale: failures and debugging

- [[Playbook - Debugging a Hung Distributed Training Job]] — the diagnostic sequence for a stalled multi-GPU job: isolate collective deadlock, straggler, dead GPU, or network fault.
- [[Gotchas - Hardware Failures at Scale]] — the at-scale failure taxonomy: fall-off-bus/Xid errors, ECC, silent data corruption, thermal stragglers, IB flaps.
- [[Lore - Silent Data Corruption at Scale]] — Meta and Google found chips that silently compute wrong answers — mercurial cores — and what SDC taught large-fleet ML training.

## Adjacent domains

- [[MOC - Training at Scale]] — distributed training's data/tensor/pipeline parallelism is the software layer built directly on top of this domain's interconnects and collectives.
- [[MOC - Inference & Serving]] — serving throughput and $/token are downstream of the same MFU, KV-cache memory math, and kernel fusion covered here.
- [[MOC - Architectures]] — FlashAttention and tensor-core kernels exist because attention and matmul are the architecture primitives this hardware has to execute fast.
