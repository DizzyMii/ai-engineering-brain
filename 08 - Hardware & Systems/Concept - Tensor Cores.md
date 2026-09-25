---
tags: [concept, domain/hardware-systems, level/core]
aliases: [MMA units, mma.sync, wgmma, WMMA]
summary: "Dedicated warp-collective matrix-multiply-accumulate units that supply ~90% of a modern GPU's FLOPs and must be explicitly targeted to be used."
---
> **One-paragraph hook:** The headline TFLOP/s on a GPU spec sheet is what the tensor cores can do. The general-purpose CUDA cores manage close to an order of magnitude less. An H100 delivers ~989 BF16 TFLOP/s through its tensor cores against ~67 FP32 TFLOP/s through the ordinary [[Concept - The CUDA Programming Model]] CUDA cores, and that dedicated matmul silicon is most of why [[Concept - Why GPUs for Deep Learning]] answers "yes." A kernel that doesn't route its matmul through tensor cores (wrong dtype, misaligned dimensions, an unsupported shape) silently falls back to the CUDA-core path and throws away roughly 15x of the chip's compute.

## The mechanism

A tensor core runs a small, fixed-shape matrix-multiply-accumulate in one instruction: `D = A * B + C`, where A, B, C, D are tiles, not scalars. On Ampere/Hopper that's, for example, a 16x8x16 MMA (`m16n8k16`) via `mma.sync`. The key point is that it's **warp-collective**. The instruction is issued once per warp, and the warp's 32 threads jointly hold the operand and accumulator data as distributed *fragments*, staged through registers and the shared-memory tier of the [[Concept - GPU Memory Hierarchy]]. No single thread holds the whole tile; the hardware assembles the computation from each thread's pieces. On a CUDA core, by contrast, each of the warp's 32 threads does its own scalar FMA per cycle. A tensor core is one block of dedicated multiply-accumulate silicon that the whole warp drives together, built for the [[Concept - Matrix Multiplication as the Atom of Deep Learning]] workload that dominates a transformer's FLOP budget.

Each tensor-core generation has added precisions, each a distinct number format covered in [[Concept - Floating Point for Deep Learning]], and the format you use sets the FLOP ceiling:

| Generation (GPU) | New precisions added |
|---|---|
| Volta (V100) | FP16 accumulate |
| Ampere (A100) | BF16, TF32, INT8, 2:4 structured sparsity |
| Hopper (H100) | FP8 (E4M3/E5M2) + Transformer Engine |
| Blackwell (B200) | FP4, microscaling (MX) formats |

**TF32** is the practical default and worth a note. It's a 19-bit internal format (8-bit exponent like FP32, 10-bit mantissa like FP16) that tensor cores take as a drop-in replacement for FP32 inputs, at roughly 8x the speed of true FP32 with FP32's dynamic range. In PyTorch it's the `torch.backends.cuda.matmul.allow_tf32` flag. For matmuls where training stability isn't sensitive to it, it's close to a free lunch. Its default has flipped between PyTorch versions, which is a real source of silent numerical and performance drift across environments.

Tensor-core programming comes in levels, from portable and coarse to hardware-specific and fast:
1. **WMMA API** (`nvcuda::wmma`): a portable C++ template interface across architectures, with coarse control.
2. **`mma.sync` PTX**: inline PTX with fine control over tile shapes and fragment layout.
3. **`wgmma`** (Hopper): warpgroup-level asynchronous MMA across 128 threads (4 warps) at once, with `ldmatrix`-style asynchronous loads and TMA-fed operands. Peak-performance Hopper kernels are built on it (see [[Concept - Warp Specialization and Async Pipelines on Hopper]]).

Almost nobody writes these by hand for production GEMMs. **cuBLAS** and **CUTLASS** template the whole ladder and pick tile shapes per architecture and problem size. [[Concept - Matmul Tiling on GPUs]] covers how the tiling hierarchy around them feeds tensor cores their operands from shared memory.

Ampere's **2:4 structured sparsity** requires exactly 2 nonzero values in every contiguous group of 4 and doubles claimed throughput by skipping the zeroed half in hardware. Production inference and training rarely use it. It needs a specific pruning pattern on the weights plus a fine-tuning/calibration step to recover accuracy, and most architectures and serving stacks don't bother. The "2x" is mostly a marketing number that few production systems realize.

## In practice

Every dense GEMM in a transformer's forward and backward pass (QKV projections, MLP up/down projections, attention score and output matmuls) goes through tensor cores whenever dtype and shape allow. [[Concept - Mixed Precision Training]] exists largely *because* tensor cores only hit peak throughput on FP16/BF16/FP8 inputs, not FP32. Training in BF16 is mainly about getting the ~15x FLOP advantage; memory savings are secondary. On Hopper, FP8 training and inference ([[Concept - FP8 and Low-Precision Hardware Formats]]) roughly doubles tensor-core throughput again over BF16 (~1979 FP8 TFLOP/s vs ~989 BF16 TFLOP/s on H100). The cost is per-tensor or per-block scaling to keep FP8's narrow dynamic range from underflowing or overflowing gradients.

## Failure modes

- **Falling off the tensor-core path.** Dimensions that aren't a multiple of the MMA tile shape (commonly 8 or 16; e.g., a hidden size or sequence length not divisible by 16), or an unsupported dtype, silently send the matmul to the ~10x-slower CUDA-core fallback. No error, just a mysteriously slow kernel. Detection: Nsight Compute's tensor-core utilization reads near zero on a kernel you expected to be tensor-core-bound. Fix: pad shapes to the nearest tile multiple.
- **The TF32 footgun.** A framework's `allow_tf32` (or equivalent) flag changing between runs (CI, a library upgrade, a different default per PyTorch version) changes speed and, slightly, numerical results with no code change. You get "it got faster/slower for no reason" bug reports.
- **Operand/accumulator precision mismatch.** Accumulating FP8 matmuls in FP8 instead of FP32 compounds rounding error catastrophically over thousands of accumulation steps. Tensor cores generally accumulate at higher precision than the inputs to prevent this. Code that ignores it, such as a custom kernel that downcasts the accumulator too early, brings back training instability that looks like a modeling bug.

## The non-obvious

With ~989 vs ~67 TFLOP/s, for any GEMM-dominated workload *skipping tensor cores gives up over 90% of the chip*. A 20% inefficiency would be the wrong mental model. That changes a lot of kernel-optimization work. The question is rarely how to make a CUDA-core loop faster and almost always how to reshape the computation so it can be expressed as a tensor-core MMA at all. It's also why odd tensor shapes (a vocabulary size, an attention head count, a LoRA rank) that don't divide evenly by 8 or 16 are a measurable throughput tax and more than an aesthetic annoyance. Production model architects pad dimensions to tensor-core-friendly multiples to avoid it.

## Connections
- [[Concept - GPU Memory Hierarchy]] — tensor cores consume operands staged in shared memory/registers; feeding them fast enough is a memory-hierarchy problem, not a compute one.
- [[Concept - The CUDA Programming Model]] — `mma.sync`/`wgmma` are warp- and warpgroup-collective instructions built on the thread/warp execution model.
- [[Concept - FP8 and Low-Precision Hardware Formats]] — the newest precision generation tensor cores support, and the scaling machinery it requires.
- [[Concept - Mixed Precision Training]] — the training technique that exists specifically to keep matmuls on the tensor-core path.
- [[Concept - Matmul Tiling on GPUs]] — the tiling hierarchy that determines how operands reach the tensor core at all.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — `wgmma` and TMA-fed async pipelines are the Hopper-specific programming style that reaches peak tensor-core throughput.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the workload tensor cores are purpose-built to accelerate.
- [[Concept - Floating Point for Deep Learning]] — TF32, FP16, BF16, FP8 are all format definitions this note assumes.
- [[Concept - Why GPUs for Deep Learning]] — the surface-level framing of why dedicated matmul silicon exists on a GPU at all.

## Sources
- NVIDIA Ampere Architecture Whitepaper (2020) and Hopper Architecture Whitepaper (2022) — tensor-core generation specs, TF32 definition, Transformer Engine.
- Markidis, S. et al. (2018) — "NVIDIA Tensor Core Programmability, Performance & Precision" — early characterization of tensor-core numerics and throughput.
