---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [GEMM tiling, blocked matrix multiplication, tiled GEMM, threadblock tiling]
summary: "How GEMM is tiled into threadblock/warp/instruction levels matched to the memory hierarchy so operands are reused, not reloaded, from HBM."
---

# Concept - Matmul Tiling on GPUs

> **One-paragraph hook:** A naive GEMM kernel has one thread compute one output element by walking the full K dimension, reloading operands from HBM each time. It's memory-bound however many [[Concept - Tensor Cores|tensor cores]] the chip has, because every output element reloads its whole input row and column from global memory on its own. Tiling fixes that. Split the matmul into a hierarchy of blocks sized to successive levels of the [[Concept - GPU Memory Hierarchy|memory hierarchy]], so each loaded byte gets multiplied against many others before eviction. Reuse before eviction is what turns matmul into the compute-bound operation the [[Concept - The Roofline Model|roofline model]] promises, and it's why cuBLAS/CUTLASS/Triton kernels look nothing like the textbook matmul loop.

## The mechanism

For $C = A \times B$ with $A \in \mathbb{R}^{M \times K}$, $B \in \mathbb{R}^{K \times N}$, a naive per-element kernel loads a full row of $A$ and a full column of $B$ from HBM for every output element. That's $O(M N K)$ HBM reads for $O(MNK)$ FLOPs, arithmetic intensity $O(1)$, deeply memory-bound. High-performance GEMM tiles the problem across three nested levels, each reusing data loaded by the level above:

1. **Threadblock tile.** A block of threads (e.g., 128×128 output elements) computes one output tile together by iterating over K in chunks. Each $A$-chunk and $B$-chunk is staged into **shared memory** once and reused by every thread in the block.
2. **Warp tile.** Inside a threadblock, each warp owns a sub-tile of the output and moves its operands from shared memory into **registers** (or MMA fragments on tensor-core paths) for the multiply-accumulate.
3. **Instruction tile.** The smallest granularity: the shape one hardware MMA instruction consumes (e.g., a 16×8×16 tile for `mma.sync`), run directly on register-resident data.

Each level reuses the one above it many times before that data is evicted, and that's what pushes arithmetic intensity past the ridge point. The math for one threadblock tile: a $128 \times 128$ output tile computed from a $128 \times K_{tile}$ slice of $A$ and a $K_{tile} \times 128$ slice of $B$ does $128^2 \times K_{tile}$ multiply-adds while loading only $2 \times 128 \times K_{tile}$ elements from HBM into shared memory. That's an arithmetic intensity of roughly $128^2 K_{tile} / (2 \cdot 128 K_{tile}) = 64$ FLOPs per element loaded. Convert to bytes and compare with the chip's ridge point (~295 FLOP/byte on H100 BF16, per [[Concept - The Roofline Model]]) and this reuse is what moves a well-tiled GEMM from memory-bound into comfortably compute-bound territory. Tile size is picked so the ratio clears the ridge point.

Moving data into shared memory and registers costs time, so fast kernels overlap it with compute using **software pipelining / double buffering**. While the tensor cores work through the current K-tile, the next one is already copying from HBM into shared memory. Ampere does this with `cp.async`, an asynchronous copy that skips registers entirely. Hopper folds it into **TMA** (Tensor Memory Accelerator), which moves whole multi-dimensional tiles asynchronously with one instruction and frees the threads that would otherwise issue copies. Without the overlap, every K-tile boundary stalls the tensor cores on a fresh HBM round trip. Pipelining is what lets a tiled kernel sustain near-peak throughput instead of merely being *capable* of it.

The last refinement is **epilogue fusion**: apply whatever follows the GEMM (bias add, activation, residual add, output scaling) to the output tile while it's still in registers, before it goes to HBM. Here GEMM tiling meets [[Concept - Kernel Fusion]]. The epilogue is free real estate, since the tile is already on-chip and about to be written out anyway.

## In practice

Almost nobody hand-writes this hierarchy for production GEMMs. **CUTLASS** and **cuBLAS** template the whole three-level structure (threadblock tile shape, warp tile shape, instruction shape, pipelining depth) and pick a configuration per GPU architecture and problem shape from a library of pre-tuned kernels. [[Concept - Triton]] automates the same hierarchy at a higher level: the kernel author sets block sizes and grid dimensions, and the compiler handles warp- and instruction-level tiling, coalescing and pipelining.

Tile-based dispatch has a side effect called **wave quantization**. A GPU launches threadblocks in waves that each fill every SM, and a problem size that doesn't divide into a whole number of full waves leaves SMs idle on the last, partial wave. A matmul with $M=4097$ can run meaningfully slower than one with $M=4096$, which is why production kernel libraries publish "preferred" or padded shapes.

## Failure modes

- **Tile shape causes shared-memory bank conflicts.** If a tile's layout makes several threads in a warp hit the same shared-memory bank at once, those accesses serialize. [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] covers the mechanism and fix (padding, swizzling). Detection: Nsight Compute's bank-conflict counter, or a kernel that's mysteriously slower than a nearly identical tile-shape variant.
- **Oversized tiles kill occupancy.** A threadblock tile sized for maximum register/shared-memory reuse can use so much of both that only one or two blocks fit per SM, which limits how well the machine hides memory latency ([[Concept - Occupancy and Latency Hiding]]). The answer is rarely "bigger tiles." It's a search over the tile-size/occupancy trade, which is what CUTLASS's and Triton's autotuners do.
- **Falling off the tensor-core path.** If the instruction tile shape doesn't match the problem dimensions (a K-dimension or head-dim not divisible by 8 or 16), the kernel silently drops to a much slower path. Details in [[Concept - Tensor Cores]].
- **Wave quantization tails.** Sizes just over a multiple of the threadblock tile leave a nearly idle final wave. "Why is this slightly bigger matmul so much slower" looks like a bug and is a tiling/occupancy artifact. Compare measured FLOP/s with the padded-shape FLOP/s for the same kernel.

## The non-obvious

The three-level hierarchy isn't really about matmul. It maps the compute hierarchy straight onto the [[Concept - GPU Memory Hierarchy|memory hierarchy]]: threadblock tile ↔ shared memory, warp tile ↔ registers, instruction tile ↔ the MMA unit. Seen that way, tiling is the *general* recipe for putting any reuse-heavy computation on a GPU. Find the data each output depends on, find the largest chunk of it that fits in a given memory tier, and structure the loop nest so that chunk is loaded once and consumed many times before eviction. [[Deep Dive - FlashAttention]] applies this recipe to an operator with a softmax wedged between two matmuls. Its $Q$/$K$/$V$ block sizes come from the same shared-memory capacity limit that sets a GEMM's threadblock tile, so once you understand this note, FlashAttention reads like GEMM tiling with an online-softmax epilogue.

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
