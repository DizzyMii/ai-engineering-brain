---
tags: [concept, domain/hardware-systems, level/core]
aliases: [MMA units, mma.sync, wgmma, WMMA]
summary: "Dedicated warp-collective matrix-multiply-accumulate units that supply ~90% of a modern GPU's FLOPs and must be explicitly targeted to be used."
---
> **One-paragraph hook:** The headline TFLOP/s number on a GPU spec sheet is not what the general-purpose CUDA cores can do — it's what the tensor cores can do, and the gap is close to an order of magnitude. An H100 delivers ~989 BF16 TFLOP/s through its tensor cores versus ~67 FP32 TFLOP/s through its ordinary [[Concept - The CUDA Programming Model]] CUDA cores — dedicated matmul silicon is, in fact, most of the reason [[Concept - Why GPUs for Deep Learning]] answers "yes." A kernel that fails to route its matmul through tensor cores — wrong dtype, misaligned dimensions, an unsupported shape — silently falls back to the CUDA-core path and gives up roughly 15x of the chip's compute for free.

## The mechanism

A tensor core executes a small, fixed-shape matrix-multiply-accumulate in a single instruction: `D = A * B + C`, where A, B, C, D are tiles rather than scalars — for example a 16x8x16 MMA (`m16n8k16`) on Ampere/Hopper via `mma.sync`. Crucially, this is a **warp-collective** operation: the instruction is issued once per warp, but the 32 threads of the warp jointly hold the operand and accumulator data as distributed *fragments*, staged through registers and the shared-memory tier of the [[Concept - GPU Memory Hierarchy]] — no single thread has the whole tile, and the hardware assembles the full computation from the pieces each thread contributes. This is fundamentally different from a CUDA core, where 32 threads in a warp each independently perform one scalar FMA per cycle; a tensor core is one piece of dedicated multiply-accumulate silicon that a whole warp drives together, purpose-built for the [[Concept - Matrix Multiplication as the Atom of Deep Learning]] workload that dominates a transformer's FLOP budget.

The precision each generation of tensor core supports has expanded steadily — each of these is a distinct number format covered in [[Concept - Floating Point for Deep Learning]] — and the format used directly sets the FLOP ceiling:

| Generation (GPU) | New precisions added |
|---|---|
| Volta (V100) | FP16 accumulate |
| Ampere (A100) | BF16, TF32, INT8, 2:4 structured sparsity |
| Hopper (H100) | FP8 (E4M3/E5M2) + Transformer Engine |
| Blackwell (B200) | FP4, microscaling (MX) formats |

**TF32** deserves special mention as the practical default: it's a 19-bit internal format (8-bit exponent like FP32, but a 10-bit mantissa like FP16) that tensor cores consume as a drop-in replacement for FP32 inputs, running at roughly 8x the speed of true FP32 while keeping FP32's dynamic range. In PyTorch this is the `torch.backends.cuda.matmul.allow_tf32` flag — it is close to a free lunch for training stability-insensitive matmuls, and its default value has flipped between PyTorch versions, which is a real source of silent numerical/performance drift across environments.

Programming tensor cores has a ladder of abstraction, from portable-but-coarse to hardware-specific-but-fast:
1. **WMMA API** (`nvcuda::wmma`) — a portable C++ template interface across architectures, coarse-grained control.
2. **`mma.sync` PTX** — inline PTX giving fine-grained control over tile shapes and fragment layout.
3. **`wgmma`** (Hopper) — warpgroup-level asynchronous MMA, operating across 128 threads (4 warps) at once with `ldmatrix`-style asynchronous loads and TMA-fed operands, the basis of peak-performance Hopper kernels (see [[Concept - Warp Specialization and Async Pipelines on Hopper]]).

In practice almost nobody writes any of these by hand for production GEMMs — **cuBLAS** and **CUTLASS** template this entire ladder and pick tile shapes per architecture and problem size, and [[Concept - Matmul Tiling on GPUs]] covers how the surrounding tiling hierarchy feeds tensor cores their operands from shared memory.

Ampere's **2:4 structured sparsity** — requiring exactly 2 nonzero values in every contiguous group of 4 — doubles claimed throughput by skipping the zeroed half of the computation in hardware. In practice it is rarely used in production inference or training: it requires a specific pruning pattern imposed on weights, a compatible fine-tuning/calibration step to recover accuracy, and most model architectures and serving stacks don't bother, making the "2x" a mostly-marketing number that few production systems actually realize.

## In practice

Every dense GEMM in a transformer's forward and backward pass — QKV projections, the MLP up/down projections, the attention score and output matmuls — is routed through tensor cores whenever dtype and shape allow. [[Concept - Mixed Precision Training]] exists largely *because* tensor cores only reach peak throughput on FP16/BF16/FP8 inputs, not FP32; training in BF16 isn't primarily about memory savings, it's about unlocking the ~15x FLOP advantage. On Hopper, FP8 training and inference (see [[Concept - FP8 and Low-Precision Hardware Formats]]) roughly doubles tensor-core throughput again over BF16 (~1979 FP8 TFLOP/s vs ~989 BF16 TFLOP/s on H100), at the cost of needing per-tensor or per-block scaling to keep FP8's narrow dynamic range from underflowing or overflowing gradients.

## Failure modes

- **Falling off the tensor-core path**: dimensions not a multiple of the MMA tile shape (commonly 8 or 16 — e.g., a hidden size or sequence length that isn't divisible by 16) or an unsupported dtype silently redirects the matmul to the ~10x-slower CUDA-core fallback with no error, only a mysteriously slow kernel. Detection: Nsight Compute's tensor-core utilization metric reads near zero on a kernel you expected to be tensor-core-bound; fix by padding shapes to the nearest tile multiple.
- **The TF32 footgun**: a framework's `allow_tf32` (or equivalent) flag toggling between runs — CI, a library upgrade, a different default per PyTorch version — changes both speed and (slightly) numerical results without any code change, producing "it got faster/slower for no reason" bug reports.
- **Precision mismatch between operand and accumulator**: accumulating FP8 matmuls in FP8 instead of FP32 compounds rounding error catastrophically over thousands of accumulation steps; tensor cores generally accumulate in higher precision than the input operands specifically to guard against this, and code that doesn't respect that (e.g., custom kernels that downcast the accumulator too early) reproduces training instability that looks like a modeling bug.

## The non-obvious

The FLOP-dominance numbers above (~989 vs ~67 TFLOP/s) mean that for any workload dominated by GEMMs, *ignoring tensor cores isn't a 20% inefficiency, it's giving up over 90% of the chip*. This reframes a lot of kernel-optimization work: the question is rarely "how do I make this CUDA-core loop faster" and almost always "how do I reshape this computation so it's expressible as a tensor-core MMA at all." It's also why odd tensor shapes — a vocabulary size, an attention head count, a LoRA rank — that don't divide evenly into 8 or 16 are not just an aesthetic annoyance; they are a direct, measurable throughput tax, and production model architects pad dimensions to tensor-core-friendly multiples specifically to avoid it.

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
