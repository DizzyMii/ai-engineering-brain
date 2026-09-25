---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "Deep learning maps to GPUs because dense matmul is embarrassingly parallel and bandwidth-hungry — exactly what SIMT throughput hardware is built for."
---

# Concept - Why GPUs for Deep Learning

> **One-paragraph hook:** A GPU isn't a faster CPU. It spends its transistor budget differently, giving up single-thread speed for raw parallel throughput. Deep learning turned out to be almost the ideal customer for that trade. Most of the work is dense matrix multiplication, which is embarrassingly parallel and reuses data heavily, so the architecture built to shade millions of pixels in lockstep turned out to be the architecture for training neural networks.

## The mechanism

A CPU core spends most of its transistors making *one* instruction stream fast: branch predictors, deep out-of-order windows, large multi-level caches, speculative execution. A GPU spends the same budget on arithmetic units and register files and hides memory and pipeline latency by *oversubscription* instead of prediction. NVIDIA's SIMT (Single Instruction, Multiple Thread) model groups 32 threads into a **warp** that runs the same instruction in lockstep across 32 ALU lanes. An H100 has 132 Streaming Multiprocessors (SMs), each holding dozens of resident warps. When one warp stalls on an [[Concept - GPU Memory Hierarchy|HBM]] load, a ~400-800 cycle round trip, the scheduler issues from another warp that's ready. With enough warps in flight the ALUs never sit waiting on memory. Parallelism *hides* the latency; caching doesn't *reduce* it.

That only pays off when the workload has enough independent, uniform arithmetic to keep thousands of warps busy. Deep learning is roughly 90% dense [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiplication (GEMM)]] by FLOPs. Every linear layer, attention projection and convolution reduces to fused multiply-adds over regularly strided tensors. That's the shape SIMT wants: no branching, uniform control flow across threads, and every output element independent of its neighbors. The fit is close to definitional. GPUs built to rasterize triangles were already matmul machines.

The other half is where the FLOPs live. On an H100, general-purpose CUDA cores deliver ~67 TFLOP/s FP32 and ~34 TFLOP/s FP64, while dedicated [[Concept - Tensor Cores|tensor cores]] deliver ~989 TFLOP/s dense BF16, about 15x the CUDA-core FP32 rate. Deep learning tolerates reduced precision (BF16/FP8, see [[Concept - Floating Point for Deep Learning]]), and that's what lets it collect the 15x. A workload stuck on FP32 CUDA cores leaves most of the chip unused.

## In practice

The real bottleneck, and the reason this domain exists, is bytes. H100 HBM3 delivers ~3.35 TB/s; a typical dual-socket server CPU's DDR5 delivers ~100-400 GB/s. Every tensor-core FLOP needs operands fed from memory, and the FLOP:byte ratio a chip needs to stay compute-bound is set by [[Concept - The Memory Wall|the widening gap between compute growth and bandwidth growth]]. On an H100 it's roughly 295 FLOP/byte (the preview of [[Concept - The Roofline Model]]). Below that arithmetic intensity, more FLOPs on the chip buy nothing; it's waiting on HBM however fast the multipliers are.

So the "peak TFLOPs" on a spec sheet or in [[Reference - AI Accelerator Landscape]] is a ceiling, not a promise. Realized performance depends on whether a kernel reuses loaded data enough times before evicting it. Training and large-batch inference (big GEMMs) clear that bar comfortably. Small-batch autoregressive decode, elementwise ops and normalization layers usually don't, and they run memory-bound whatever TFLOP/s the chip advertises.

## Failure modes

**Branch divergence.** When threads in a warp take different control-flow paths (an `if` only some lanes satisfy), the warp runs both paths serially with the other lanes masked off, a 2x+ slowdown for a two-way branch. Deep learning code is mostly branch-free tensor math, so it avoids a trap that control-heavy generic code falls into.

**Low arithmetic intensity.** Ops that touch a tensor once and do little math per byte (softmax, LayerNorm, elementwise activations) never approach peak FLOPs however parallel they are. They're bandwidth-bound by construction. Symptom: Nsight Compute shows high achieved DRAM throughput and low SM/tensor-core utilization. Fix: fuse these ops; raw parallelism won't save them.

**Tiny-batch, latency-critical work.** A single autoregressive decode step, or anything that needs *one* answer fast instead of many answers eventually, under-fills the thousands of resident warps a GPU needs to be efficient. In that regime (small batch, branchy control flow, latency SLO over throughput) a CPU or a purpose-built low-latency accelerator still wins.

## The non-obvious

Nobody designed the GPU/DL fit in advance; it was demonstrated. Krizhevsky, Sutskever and Hinton's AlexNet (2012) trained on two consumer GTX 580s and beat the next-best ImageNet entry by roughly 10 points. That result arguably pulled a whole hardware industry toward reorganizing around this workload, after GPUs had spent a decade serving graphics before deep learning found them.

Subtler: buying peak FLOPs isn't buying performance. NVIDIA's moat is the software stack (cuBLAS, cuDNN, NCCL, the compiler toolchain) as much as the silicon, because that stack is what lets a workload *reach* a meaningful fraction of peak; see [[Concept - The CUDA Moat]]. A competitor chip with equal or better peak TFLOPs and an immature kernel library routinely delivers a fraction of the realized throughput. That's the recurring reason raw spec-sheet comparisons in this space mislead.

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
