---
tags: [concept, domain/hardware-systems, level/unicorn]
aliases: [coalescing, memory coalescing, shared memory bank conflicts, bank conflict, smem swizzle, padding trick]
summary: "The two lowest GPU memory rules: coalesced global loads and conflict-free shared-memory bank access, plus padding and swizzle fixes."
---
> **One-paragraph hook:** Two access-pattern rules explain most of the silent 2–32x slowdowns in GPU kernels, and neither ever raises an error. First, a warp's 32 global-memory accesses should fall in one aligned 128-byte line so the hardware can serve them as one transaction. Scatter them and you pay up to 32x the memory traffic for the same data. Second, shared memory is physically 32 banks, and when several threads hit *different* words in the *same* bank, the accesses serialize. These aren't last-resort micro-optimizations. They separate a kernel running at bandwidth from one running at a thirty-second of it, and the fixes (a `+1` of padding, an XOR swizzle) look absurd until you know the [[Concept - GPU Memory Hierarchy|memory hardware]] underneath.

## The mechanism

### Global memory: coalescing

A warp issues its 32 threads' memory accesses together, and the memory subsystem serves them at **sector (32-byte) and cache-line (128-byte) granularity**, not per thread. If all 32 threads read consecutive 4-byte words from one aligned 128-byte line (`32 × 4 B = 128 B`), the hardware coalesces them into one 128-byte transaction: 4 sectors, 100% of the fetched bytes used. One transaction, zero waste.

Break the pattern and it degrades fast. A **stride-2** access (each thread reads every other word) spans two cache lines and uses half of each, so 2x the traffic. A **fully scattered / random** access, with every thread on a different 128-byte line, fans out to up to **32 separate transactions**, a 32x bandwidth loss, because DRAM delivers a whole burst per access and you use one word of it. Misalignment is the same thing in miniature: a contiguous warp load offset by 4 bytes straddles two lines.

The classic case is **matrix transpose**. Reading `A[i][j]` row-major with `threadIdx.x → j` is coalesced (adjacent threads → adjacent columns → one line). Writing the transposed `B[j][i]` with the same mapping puts adjacent threads' writes `stride` apart, and every write becomes its own transaction. One direct pass can't coalesce both the read and the write. The standard fix is to **stage through shared memory**: read the input tile coalesced into a shared tile, read that tile back in transposed order, and write the output coalesced. That's where the second rule comes in.

### Shared memory: banks and conflicts

Shared memory is split into **32 banks of 4-byte words**, interleaved so word address `a` sits in bank `(a / 4) mod 32`. A warp's 32 threads can all access shared memory in one cycle **only if they hit 32 distinct banks** (or the same word; see broadcast). When `k` threads access `k` different words in the *same* bank, that's a **k-way bank conflict**, and the hardware serializes it into `k` cycles.

The transpose staging tile runs straight into this. Declare `__shared__ float tile[32][32]`. A column access, 32 threads reading `tile[0..31][j]` for fixed `j`, touches addresses `j, 32+j, 64+j, …`, all with `(addr) mod 32 == j`. **Every thread hits bank `j`: a 32-way conflict**, and shared memory runs 32x slower.

The **`+1` padding trick** fixes it for one word of waste:

```
  tile[32][32]                          tile[32][33]   (one padding column)
  addr(i,j) = i*32 + j                  addr(i,j) = i*33 + j
  bank      = (i*32 + j) mod 32         bank      = (i*33 + j) mod 32
            = j          (for all i)              = (i + j) mod 32   (since 33 ≡ 1 mod 32)
  → column j: all 32 threads → bank j   → column j: threads → banks j, j+1, …, j+31
    ***32-way conflict***                 ***all distinct — conflict-free***
```

Padding to `[32][33]` makes the row stride coprime-ish to 32, so successive rows land in successive banks. Nobody reads the extra column; you spend `32 × 4 B = 128 B` per tile to win back a 32x access.

**Broadcast isn't a conflict.** If all 32 threads read the *same* word (the same address, not merely the same bank), the hardware broadcasts it in one access. Reading a single scalar or shared coefficient across a warp is free for this reason, and constant-memory-style access is cheap.

### Swizzling, which tensor-core kernels actually use

Padding wastes shared memory and doesn't mix well with the 128-bit vectorized `ldmatrix` loads that feed [[Concept - Tensor Cores|tensor-core]] fragments. Fast libraries **swizzle** instead. They permute the logical→physical shared-memory mapping with an XOR, `phys_addr = logical_addr XOR ((logical_addr >> s) & mask) << b`, chosen so the particular access pattern of `ldmatrix`/`wgmma` is conflict-free with *zero* padding. This is the deep arcana inside CUTLASS/CuTe layouts and the [[Concept - Warp Specialization and Async Pipelines on Hopper|async-pipeline]] kernels. The swizzle lives in the tile's layout type, so every fragment load across the GEMM avoids conflicts by construction. It's also where hand-written kernels most often go subtly wrong.

## In practice

- **Detection takes two counters in Nsight Compute.** For global memory, watch *sectors per request* (4 is ideal for a coalesced fp32 warp load; near 32 means scatter) and *global load efficiency*. For shared memory, the *shared-memory bank conflicts* counter reports serialized accesses directly.
- **Where it bites hardest:** [[Concept - Attention Mechanism|attention]] and GEMM kernels (the `Kᵀ` in `QKᵀ` is a transpose that has to be swizzled), and **embedding-table lookups**. An [[Concept - Embeddings as Learned Representations|embedding gather]] indexes a huge table by token id, so each warp reads 32 unrelated rows. That's the textbook uncoalesced access, and often the least-optimized memory op in a training step.

## Failure modes

- **Non-coalesced global access.** *Symptom:* a memory-bound kernel runs 2–32x under its expected bandwidth. *Cause:* strided, transposed or misaligned layout. *Fix:* restructure the access or stage through shared memory. *Detection:* sectors-per-request ≫ 4.
- **Bank conflicts after "fixing" coalescing.** You route data through a shared tile to fix global coalescing and create a 32-way conflict on the transposed read. The kernel is fast on paper and slow in practice until you pad or swizzle.
- **Padding that breaks vectorized loads.** `+1` padding fixes scalar column access but can misalign 128-bit `ldmatrix`/`float4` loads, swapping a bank conflict for a misaligned-access penalty. Libraries swizzle instead of padding for this reason.

## The non-obvious

**Coalescing and conflict-freedom often trade off against each other.** You're satisfying a two-sided constraint, not one rule. The transpose shows it. Any direct layout coalesces one of {read, write} and leaves the other strided, so you're *forced* into shared memory. Once there, the naive tile gives you a 32-way bank conflict, so you're *forced* to pad or swizzle. Beginners optimize one side, see no speedup (or a regression), and decide the effort was wasted, when the problem just moved from a bad global pattern to a bad shared one.

These rules also survive every abstraction layer above them. [[Concept - Triton|Triton]] and `torch.compile` generate coalesced loads and pad or swizzle shared memory *for you*, and TMA generates addresses in hardware. The warp-of-32 and 32-bank facts underneath don't change. When a generated kernel is mysteriously slow, "is this access coalesced, is that tile conflict-free" is still the first question, one level down.

## Connections
- [[Concept - GPU Memory Hierarchy]] — the register/SMEM/L2/HBM tiers whose access these two rules govern at the lowest level (down-link, core).
- [[Concept - The CUDA Programming Model]] — the warp-of-32 execution model that makes coalescing and bank-conflict a per-warp property (down-link, core).
- [[Concept - Matmul Tiling on GPUs]] — tiling stages operands through shared memory, which is exactly where bank conflicts and the padding/swizzle fixes live.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — peak Hopper kernels bake XOR-swizzled SMEM layouts into their tiles so wgmma/ldmatrix reads are conflict-free.
- [[Concept - Tensor Cores]] — `ldmatrix` fragment loads for tensor cores are the access pattern swizzling is designed to make conflict-free.
- [[Gotchas - GPU Kernel Performance]] — this note is the mechanism behind two of that note's top silent-slowdown traps.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the sectors-per-request and bank-conflict counters this note relies on are steps in that procedure.
- [[Concept - Attention Mechanism]] — attention kernels are where the transpose-coalescing-swizzle chain matters most in real transformers (domain 03, cross-domain).
- [[Concept - Embeddings as Learned Representations]] — embedding-table gather is the canonical uncoalesced global-memory access in a training step (domain 02, cross-domain).

## Sources
- NVIDIA CUDA C++ Best Practices Guide — coalesced global access rules, the 32-bank shared-memory model, and the `+1` padding recommendation.
- Harris, M. — "An Efficient Matrix Transpose in CUDA" (NVIDIA Developer Blog) — the coalescing/bank-conflict trade-off worked through the transpose, including the padding fix.
- NVIDIA CUTLASS / CuTe documentation — XOR-swizzled shared-memory layouts for conflict-free `ldmatrix`/`wgmma` operand loads.
