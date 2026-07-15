---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [GEMM tiling, blocked matrix multiplication, tiled GEMM, threadblock tiling]
summary: "How GEMM is tiled into threadblock/warp/instruction levels matched to the memory hierarchy so operands are reused, not reloaded, from HBM."
---

# Concept - Matmul Tiling on GPUs

> **One-paragraph hook:** A naive GEMM kernel — one thread computes one output element by walking the full K dimension, reloading operands from HBM every time — is memory-bound no matter how many [[Concept - Tensor Cores|tensor cores]] the chip has, because every output element reloads its entire input row and column from global memory independently. Tiling is the fix: decompose the matmul into a hierarchy of blocks sized to fit successive levels of the [[Concept - GPU Memory Hierarchy|memory hierarchy]], so each loaded byte is multiplied against many other bytes before it's evicted. This single idea — reuse before eviction — is what turns matmul from a memory-bound operation into the compute-bound one the [[Concept - The Roofline Model|roofline model]] promises, and it's the reason cuBLAS/CUTLASS/Triton kernels look nothing like the matmul loop from a textbook.

## The mechanism

For $C = A \times B$ with $A \in \mathbb{R}^{M \times K}$, $B \in \mathbb{R}^{K \times N}$, a naive per-element kernel loads a full row of $A$ and column of $B$ from HBM for every output element — $O(M N K)$ HBM reads for $O(MNK)$ FLOPs, an arithmetic intensity of $O(1)$: deeply memory-bound. High-performance GEMM instead tiles the problem across three nested levels, each level reusing data loaded by the level above it:

1. **Threadblock tile** — a block of threads (e.g., 128×128 output elements) cooperatively computes one output tile by iterating over the K dimension in chunks, staging each $A$-chunk and $B$-chunk into **shared memory** once and reusing it across every thread in the block.
2. **Warp tile** — within a threadblock, each warp owns a sub-tile of the output and stages its operands from shared memory into **registers** (or, on tensor-core paths, into MMA fragments) for the actual multiply-accumulate.
3. **Instruction tile** — the smallest granularity, the exact shape one hardware MMA instruction consumes (e.g., a 16×8×16 tile for `mma.sync`), executed directly against register-resident data.

Each level down the hierarchy reuses the level above it many times before that data is evicted, which is precisely what drives arithmetic intensity above the ridge point. The reuse math for a single threadblock tile makes this concrete: a $128 \times 128$ output tile computed from a $128 \times K_{tile}$ slice of $A$ and a $K_{tile} \times 128$ slice of $B$ does $128^2 \times K_{tile}$ multiply-adds while loading only $2 \times 128 \times K_{tile}$ elements from HBM into shared memory — an arithmetic intensity of roughly $128^2 K_{tile} / (2 \cdot 128 K_{tile}) = 64$ FLOPs/element loaded. Once converted to bytes and compared against a chip's ridge point (~295 FLOP/byte on H100 BF16, per [[Concept - The Roofline Model]]), this reuse factor is what pushes a well-tiled GEMM from memory-bound territory into comfortably compute-bound territory — the tile size is chosen specifically so this ratio clears the ridge point.

Getting data into shared memory and registers is not free, so high-performance kernels overlap it with computation via **software pipelining / double buffering**: while the tensor cores chew through the current K-tile, the next K-tile is already being copied from HBM into shared memory in the background. On Ampere this uses `cp.async` (asynchronous copy that bypasses registers entirely); on Hopper this is subsumed by **TMA** (Tensor Memory Accelerator), which moves whole multi-dimensional tiles asynchronously with a single instruction and frees up threads that would otherwise be issuing copy instructions. Without this overlap, every K-tile boundary would stall the tensor cores on a fresh HBM round trip — pipelining is what lets a tiled kernel actually sustain near-peak throughput rather than merely being *capable* of it.

A final refinement, **epilogue fusion**, applies the operations that would otherwise follow the GEMM — bias add, activation, residual add, output scaling — directly to the output tile while it still sits in registers, before it's ever written to HBM. This is where GEMM tiling meets [[Concept - Kernel Fusion]]: the epilogue is free real estate, since the tile is already resident on-chip and about to be written out regardless.

## In practice

Almost nobody hand-writes this tiling hierarchy for production GEMMs. **CUTLASS** and **cuBLAS** template the entire three-level structure — threadblock tile shape, warp tile shape, instruction shape, pipelining depth — and select a configuration per GPU architecture and problem shape from a library of pre-tuned kernels; [[Concept - Triton]] automates the same hierarchy at a higher level of abstraction, letting a kernel author specify block sizes and grid dimensions while the compiler handles the warp- and instruction-level tiling, coalescing, and pipelining underneath. A practical consequence of tile-based dispatch is **wave quantization**: a GPU launches threadblocks in waves that each occupy the full set of SMs, and a problem size that doesn't divide evenly into an integer number of full waves leaves some SMs idle on the final, partial wave — a matmul with $M=4097$ instead of $M=4096$ can run meaningfully slower than the larger, evenly-tiled size, which is why production kernel libraries publish "preferred" or padded shapes.

## Failure modes

- **Bad tile-shape choice causing shared-memory bank conflicts**: if a tile's memory layout causes multiple threads in a warp to hit the same shared-memory bank simultaneously, those accesses serialize instead of completing in parallel — see [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] for the mechanism and fix (padding, swizzling). Detection: Nsight Compute's shared-memory bank-conflict counter, or a kernel that's mysteriously slower than a nearly-identical tile-shape variant.
- **Low occupancy from oversized tiles**: a threadblock tile sized to maximize register/shared-memory reuse can also consume so many registers or so much shared memory per block that only one or two blocks fit per SM — see [[Concept - Occupancy and Latency Hiding]] for why this caps the machine's ability to hide memory latency. The fix is rarely "always increase tile size"; it's a search over the tile-size/occupancy tradeoff, which is exactly what CUTLASS's and Triton's autotuners do.
- **Falling off the tensor-core path entirely**: if the instruction tile shape doesn't match the problem's dimensions (a K-dimension or head-dim not divisible by 8 or 16), the kernel silently falls back to a much slower path, discussed in full in [[Concept - Tensor Cores]].
- **Wave quantization tail effects**: problem sizes just over a multiple of the threadblock tile size leave a nearly-idle final wave, producing a "why is this slightly bigger matmul so much slower" surprise that looks like a bug but is a tiling/occupancy artifact; detection is comparing measured FLOP/s against the padded-shape FLOP/s for the same kernel.

## The non-obvious

The three-level tiling hierarchy is not really about matmul specifically — it's a direct physical mapping of the compute hierarchy onto the [[Concept - GPU Memory Hierarchy|memory hierarchy]]: threadblock tile ↔ shared memory, warp tile ↔ registers, instruction tile ↔ the MMA unit itself. Once you see tiling this way, it stops being "a matmul optimization technique" and becomes the *general* recipe for mapping any reuse-heavy computation onto a GPU: identify the data each output depends on, find the largest chunk of that data that fits in a given memory tier, and structure the loop nest so that chunk is loaded once and consumed many times before eviction. [[Deep Dive - FlashAttention]] is exactly this recipe applied to an operator with a softmax wedged between two matmuls — its $Q$/$K$/$V$ block sizes are chosen by the same shared-memory-capacity constraint that sets a GEMM's threadblock tile size, which is why FlashAttention reads like "GEMM tiling with an online-softmax epilogue" once you already understand this note.

## Connections
- [[Concept - GPU Memory Hierarchy]] — the capacity/bandwidth pyramid that directly dictates each tiling level's size.
- [[Concept - Tensor Cores]] — the instruction-tile-level hardware every warp tile ultimately feeds operands to.
- [[Concept - The Roofline Model]] — the formal reason tiling raises arithmetic intensity above the compute-bound ridge point.
- [[Concept - Kernel Fusion]] — epilogue fusion folds bias/activation/scaling into the tiled GEMM's final register-resident tile for free.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the failure mode that a poorly chosen tile layout triggers.
- [[Concept - Occupancy and Latency Hiding]] — the tile-size-vs-occupancy tradeoff that CUTLASS's and Triton's autotuners search over.
- [[Concept - Triton]] — the higher-level language that automates this tiling hierarchy instead of hand-writing CUTLASS templates.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — the producer/consumer async pipelining pattern that keeps tensor cores fed across K-tile boundaries.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the workload this entire tiling discipline exists to accelerate (cross-domain: foundations).
- [[Concept - Mixed Precision Training]] — the training technique whose speedup depends on tiled GEMMs actually reaching the tensor-core path (cross-domain: training at scale).
- [[Deep Dive - FlashAttention]] — the same tiling hierarchy applied to an operator with a softmax between two matmuls.

## Sources
- NVIDIA — CUTLASS documentation and design notes — the canonical open-source template library for the threadblock/warp/instruction tiling hierarchy described here.
- NVIDIA — Ampere and Hopper Architecture Whitepapers (2020, 2022) — `cp.async` and TMA asynchronous copy mechanisms used for software pipelining across K-tiles.
- Volkov, Demmel (2008) — "Benchmarking GPUs to Tune Dense Linear Algebra" — early, still-influential characterization of tile-size and occupancy tradeoffs for GEMM on GPUs.
