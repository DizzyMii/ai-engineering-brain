---
tags: [moc, domain/hardware-systems, level/surface]
aliases: []
summary: "Map of the hardware domain: GPU/TPU internals, kernel programming, cluster networking, and the failure modes that surface only at scale."
---

# MOC - Hardware & Systems

This domain covers the physical layer the rest of the vault assumes: what a GPU or TPU does with a matmul, why memory bandwidth decides most kernels' speed more often than raw FLOPs do, and how thousands of accelerators get wired into one training run. It includes the execution model (CUDA, warps, tensor cores), the performance math (roofline, MFU, memory formulas) that turns hardware specs into dollars per token, the kernel tools (Triton, FlashAttention) that close the gap between theoretical and achieved throughput, and the networking and failure modes you only see on hundreds or thousands of chips.

Every claim elsewhere in the vault about training cost, inference latency or model scale is bounded by numbers from here: HBM bandwidth, NVLink bisection bandwidth, MFU. Algorithmic cleverness alone doesn't get around them. An architecture that looks elegant on paper is unusable if it doesn't fit the memory hierarchy and interconnect topology.

## Start here

- **Surface** → [[Concept - Why GPUs for Deep Learning]]: why dense matmul lands on SIMT throughput hardware. The rest of the domain assumes it.
- **Core** → [[Concept - The Roofline Model]]: one plot that tells you whether you're optimizing compute or memory bandwidth. The rest of the domain reasons from it.
- **Advanced** → [[Deep Dive - FlashAttention]]: the flagship worked example, with tiling, online softmax and HBM avoidance all in one real production kernel.
- **Frontier** → [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]]: the current hardware generation that the frontier-tier notes here (FP8, warp specialization, rack-scale NVLink) target.
- **Unicorn** → [[Lore - Silent Data Corruption at Scale]]: a failure that throws no error and just corrupts a training run. It's why fleets run canary checks.

## Why hardware shapes everything

- [[Concept - Why GPUs for Deep Learning]]: dense matmul is embarrassingly parallel and bandwidth-hungry, which is what SIMT throughput hardware is built for.
- [[Concept - The Memory Wall]]: compute has outgrown memory bandwidth for decades, so most deep learning kernels are limited by data movement, not arithmetic.
- [[Concept - Anatomy of an AI Training Cluster]]: the physical hierarchy (GPU → node → rack → pod → datacenter) and the two-tier network that connects it.

## GPU execution model and memory

- [[Concept - GPU Memory Hierarchy]]: registers, shared memory/L1, L2, HBM. Each tier trades roughly 1000x capacity for roughly 1000x bandwidth.
- [[Concept - The CUDA Programming Model]]: the thread-block-grid hierarchy that maps scalar-looking code onto SM/warp hardware. For performance you think in warps, not threads.
- [[Concept - Tensor Cores]]: warp-collective matrix-multiply-accumulate units that supply ~90% of a modern GPU's FLOPs. You have to target them explicitly to use them.
- [[Concept - Occupancy and Latency Hiding]]: a GPU hides 400-800 cycle HBM latency by keeping many warps resident per SM, and more occupancy isn't always faster.
- [[Concept - Matmul Tiling on GPUs]]: GEMM tiled at threadblock, warp and instruction level so operands get reused instead of reloaded from HBM.
- [[Concept - Kernel Fusion]]: several ops in one kernel so intermediates stay on-chip and skip the HBM round trip. The top lever for memory-bound ops.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]]: the two lowest-level GPU memory rules, and the padding and swizzle fixes for when you break them.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]]: the Hopper pattern behind peak GEMM and FA3. Producer warpgroups issue TMA copies, consumers run wgmma, and mbarriers keep them in sync.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]]: why real GPUs run below spec (boost clocks, power caps, throttling), which causes stragglers and MFU variance.
- [[Concept - Systolic Arrays]]: the 2D grid-of-MACs dataflow in TPUs, which reuses each SRAM read across a whole row with no register file.

## Measuring performance

- [[Concept - The Roofline Model]]: predicts from FLOPs-per-byte whether a kernel is compute- or memory-bound, on one plot.
- [[Concept - Model FLOPs Utilization (MFU)]]: the fraction of a chip's peak FLOPs spent on useful model math. Real runs land at 30-60%, and it sets $/token directly.
- [[Reference - Memory Math for Transformers]]: byte formulas for parameters, optimizer state, activations and KV cache, i.e. what fits on a GPU, worked for 7B and 70B.

## Kernel programming and tooling

- [[Concept - Triton]]: OpenAI's Python-embedded kernel language. You program at the block level and the compiler handles threading and coalescing.
- [[Snippet - Fused Softmax Kernel in Triton]]: a runnable kernel that fuses row-max, exp, sum and divide into one bandwidth-bound pass, replacing four HBM round-trips.
- [[Snippet - A Minimal FlashAttention Kernel in Triton]]: a runnable forward FlashAttention kernel with the online-softmax streaming loop that keeps the N×N score matrix out of HBM.
- [[Deep Dive - FlashAttention]]: how attention gets tiled with online softmax and recomputation so the O(N²) score matrix never touches HBM, across v1-v3.
- [[Playbook - Profiling and Optimizing a GPU Kernel]]: the end-to-end procedure for finding a slow kernel's real bottleneck with Nsight Systems/Compute and applying the fix that helps.
- [[Gotchas - GPU Kernel Performance]]: 2-10x slowdowns that never raise an error, from coalescing, bank conflicts, tensor-core misses, spills and launch overhead.

## Networking and cluster scale

- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]]: a 10-18x bandwidth cliff separates the two link tiers, and that cliff decides where each parallelism strategy lives.
- [[Concept - All-Reduce and Collective Operations]]: all-reduce, all-gather, reduce-scatter, all-to-all, and the ring/tree algorithms distributed training runs on.
- [[Concept - Network Topology for AI Clusters]]: how fat-tree/Clos fabrics wire 10k-100k+ GPUs. At scale, topology caps collective bandwidth more than link speed does.
- [[Concept - Rack-Scale Systems and NVLink Domains]]: growing the NVLink scale-up domain from an 8-GPU node to a 72-GPU rack moves the bandwidth cliff and changes the parallelism math.
- [[Breakdown - NCCL]]: how NVIDIA's collective library discovers cluster topology, builds rings and trees, and pipelines the reduce-and-copy kernels under nearly every distributed job.

## Hardware platforms and precision

- [[Breakdown - The Google TPU]]: the systolic MXU, compiler-managed VMEM, ICI torus plus optical circuit switches, and the compile-first XLA model, taken as one system.
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]]: how H100/H200 and B200/GB200 are built. SM and tensor-core generations, async data movement, HBM, and the move to rack scale.
- [[Concept - FP8 and Low-Precision Hardware Formats]]: the 8-bit and 4-bit floating-point formats tensor cores run natively, and the block scaling that keeps them from over/underflowing.
- [[Reference - AI Accelerator Landscape]]: a date-stamped 2026 spec comparison of NVIDIA GPUs, Google TPUs, AMD MI300, AWS Trainium/Inferentia and inference ASICs.
- [[Decision - Selecting GPUs for Training and Inference]]: pick by capacity fit, then compute- vs memory-bound profile, then latency/throughput SLO, then $/hr. Peak TFLOPs is the wrong first filter.

## Operating at scale: failures and debugging

- [[Playbook - Debugging a Hung Distributed Training Job]]: the diagnostic sequence for a stalled multi-GPU job. Separate collective deadlock, straggler, dead GPU and network fault.
- [[Gotchas - Hardware Failures at Scale]]: the at-scale failure taxonomy of fall-off-bus/Xid errors, ECC, silent data corruption, thermal stragglers and IB flaps.
- [[Lore - Silent Data Corruption at Scale]]: Meta and Google found chips ("mercurial cores") that compute wrong answers without any error, and what SDC taught large-fleet ML training.

## Adjacent domains

- [[MOC - Training at Scale]]: data/tensor/pipeline parallelism is the software layer built directly on this domain's interconnects and collectives.
- [[MOC - Inference & Serving]]: serving throughput and $/token come from the same MFU, KV-cache memory math and kernel fusion covered here.
- [[MOC - Architectures]]: FlashAttention and tensor-core kernels exist because attention and matmul are the architecture primitives this hardware has to run fast.
