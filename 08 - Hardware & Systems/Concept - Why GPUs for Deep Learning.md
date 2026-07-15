---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "Deep learning maps to GPUs because dense matmul is embarrassingly parallel and bandwidth-hungry — exactly what SIMT throughput hardware is built for."
---

# Concept - Why GPUs for Deep Learning

> **One-paragraph hook:** A GPU is not a faster CPU — it is a different transistor budget entirely, one that trades single-thread speed for raw parallel throughput. Deep learning turned out to be almost the ideal customer for that trade: the overwhelming majority of the work is dense matrix multiplication, an operation that is embarrassingly parallel and reuses data heavily, so the same architecture built for shading millions of pixels in lockstep turned out to be the architecture for training neural networks.

## The mechanism

A CPU core spends most of its transistor budget on making *one* instruction stream fast: branch predictors, deep out-of-order execution windows, large multi-level caches, speculative execution. A GPU spends the equivalent budget on raw arithmetic units and register files, and hides memory and pipeline latency by *oversubscription* instead of prediction. NVIDIA's SIMT (Single Instruction, Multiple Thread) model groups 32 threads into a **warp** that executes the same instruction in lockstep across 32 ALU lanes; an H100 packs 132 Streaming Multiprocessors (SMs), each capable of holding dozens of resident warps. When one warp stalls on a load from [[Concept - GPU Memory Hierarchy|HBM]] — a ~400-800 cycle round trip — the warp scheduler simply issues an instruction from a different, ready warp. With enough warps in flight, the SM's ALUs never idle waiting on memory; this is latency *hiding* through parallelism, not latency *reduction* through caching.

This only pays off if the workload has enough independent, uniform arithmetic to keep thousands of warps busy. Deep learning workloads are roughly 90% dense [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiplication (GEMM)]] by FLOPs — every linear layer, every attention projection, every convolution reduces to fused multiply-adds over regularly-strided tensors. That's exactly the shape SIMT wants: no branching, uniform control flow across threads, and each output element's computation is independent of its neighbors. The workload and the hardware are a fit almost by definition, not by accident — the same GPUs built to rasterize triangles turned out to already be matmul machines.

The other half of the mechanism is where the real FLOPs live. On an H100, general-purpose CUDA cores deliver ~67 TFLOP/s FP32 and ~34 TFLOP/s FP64, but dedicated [[Concept - Tensor Cores|tensor cores]] deliver ~989 TFLOP/s dense BF16 — about 15x the CUDA-core FP32 rate. Deep learning's tolerance for reduced precision (BF16/FP8, see [[Concept - Floating Point for Deep Learning]]) is what lets it actually collect that 15x; a workload stuck on FP32 CUDA cores is leaving most of the chip's silicon unused.

## In practice

The real bottleneck, and the reason this whole domain exists, is not FLOPs — it's bytes. H100 HBM3 delivers ~3.35 TB/s of bandwidth; a typical dual-socket server CPU's DDR5 delivers ~100-400 GB/s. Every FLOP the tensor cores execute needs operands fed from memory, and the FLOP:byte ratio a chip can sustain compute-bound is set by [[Concept - The Memory Wall|the widening gap between compute growth and bandwidth growth]] — on an H100 that ratio is roughly 295 FLOP/byte (the teaser for [[Concept - The Roofline Model]]). Below that arithmetic intensity, more FLOPs on the chip buy you nothing; the chip is waiting on HBM regardless of how fast its multipliers are.

This is why "peak TFLOPs" from a spec sheet or [[Reference - AI Accelerator Landscape]] is a ceiling, not a promise — realized performance depends on whether the kernel can reuse loaded data enough times before evicting it. Training and large-batch inference (big GEMMs) comfortably clear that bar; small-batch autoregressive decode, elementwise ops, and normalization layers usually don't, and run memory-bound regardless of how many TFLOP/s the chip advertises.

## Failure modes

**Branch divergence:** if threads within a warp take different control-flow paths (an `if` that only some lanes satisfy), the warp executes both paths serially with the non-participating lanes masked off — a 2x+ slowdown for a two-way branch. Deep learning code is mostly branch-free tensor math, which is exactly why it avoids the trap that generic control-heavy code doesn't.

**Low arithmetic intensity:** ops that touch a tensor once and do little math per byte (softmax, LayerNorm, elementwise activations) never approach peak FLOPs no matter how parallel they are — they're bandwidth-bound by construction. Symptom: Nsight Compute shows high achieved-DRAM-throughput but low SM/tensor-core utilization. Fix: fuse these ops rather than expect raw parallelism to save them.

**Tiny-batch / latency-critical workloads:** a single autoregressive decode step, or any workload where you need *one* answer fast rather than many answers eventually, under-fills the thousands of resident warps a GPU needs to be efficient. This is the regime — small batch, branchy control flow, latency SLO over throughput — where a CPU, or a purpose-built low-latency accelerator, still wins.

## The non-obvious

The GPU/DL fit wasn't obvious in advance — it was demonstrated, not designed. Krizhevsky, Sutskever, and Hinton's AlexNet (2012) trained on two consumer GTX 580s and beat the next-best ImageNet entry by roughly 10 points, and that result is arguably what pulled an entire hardware industry toward reorganizing itself around this workload; GPUs existed for graphics for a decade before deep learning found them.

The subtler insight: buying peak FLOPs is not the same as buying performance. NVIDIA's actual moat, as much as the silicon itself, is the software stack (cuBLAS, cuDNN, NCCL, the compiler toolchain) that lets a workload actually *reach* a meaningful fraction of those peak numbers — see [[Concept - The CUDA Moat]]. A competitor chip with equal or better peak TFLOPs but an immature kernel library routinely delivers a fraction of the realized throughput, which is the recurring story behind why raw spec-sheet comparisons in this space mislead.

## Connections
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the workload primitive that makes the SIMT bet pay off; without matmul dominance the GPU fit collapses.
- [[Concept - GPU Memory Hierarchy]] — the tiered memory system that latency-hiding and arithmetic intensity are actually reasoning about.
- [[Concept - Tensor Cores]] — the dedicated units that deliver the ~15x FLOP advantage over general CUDA cores, the real source of GPU throughput for DL.
- [[Concept - The Roofline Model]] — formalizes the compute-vs-memory-bound question this note only gestures at.
- [[Concept - The Memory Wall]] — the structural reason bandwidth, not FLOPs, is the binding constraint this note keeps returning to.
- [[Reference - AI Accelerator Landscape]] — where the H100 numbers here sit relative to TPUs, MI300X, and inference ASICs.
- [[Concept - The CUDA Moat]] — why the software stack, not just the SIMT architecture, is what makes NVIDIA GPUs the default choice.
- [[Concept - Floating Point for Deep Learning]] — the reduced-precision formats that let tensor cores actually deliver their peak rate.

## Sources
- Krizhevsky, Sutskever, Hinton (2012) — "ImageNet Classification with Deep Convolutional Neural Networks" (AlexNet) — trained on two GTX 580 GPUs; the result widely credited with pulling deep learning research onto GPU hardware.
- NVIDIA (2022) — "NVIDIA H100 Tensor Core GPU Architecture" whitepaper — source for the peak FLOP/s and HBM3 bandwidth figures used throughout.
