---
tags: [concept, domain/hardware-systems, level/unicorn]
aliases: [coalescing, memory coalescing, shared memory bank conflicts, bank conflict, smem swizzle, padding trick]
summary: "The two lowest GPU memory rules: coalesced global loads and conflict-free shared-memory bank access, plus padding and swizzle fixes."
---
> **One-paragraph hook:** Two access-pattern rules explain most of the silent 2–32x slowdowns in GPU kernels, and neither ever raises an error. First, a warp's 32 global-memory accesses want to fall in one aligned 128-byte line so the hardware services them as one transaction — scatter them and you pay up to 32x the memory traffic for the same data. Second, shared memory is physically 32 banks, and if several threads hit *different* words in the *same* bank the accesses serialize. These aren't micro-optimizations you reach for last; they are the difference between a kernel that runs at bandwidth and one that runs at a thirty-second of it, and the tricks that fix them — a `+1` of padding, an XOR swizzle — look absurd until you know the [[Concept - GPU Memory Hierarchy|memory hardware]] underneath.

## The mechanism

### Global memory: coalescing

A warp issues its 32 threads' memory accesses together, and the memory subsystem services them at **sector (32-byte) and cache-line (128-byte) granularity**, not per-thread. If all 32 threads of a warp read consecutive 4-byte words from one aligned 128-byte line (`32 × 4 B = 128 B`), the hardware coalesces them into a single 128-byte transaction — 4 sectors, 100% of the bytes fetched are used. This is the ideal: one transaction, zero waste.

Break the pattern and it degrades sharply. A **stride-2** access (each thread reads every other word) spans two cache lines and uses half of each — 2x the traffic. A **fully scattered / random** access — every thread hitting a different 128-byte line — fans out to up to **32 separate transactions**, a 32x bandwidth loss, because DRAM still delivers a whole burst per access and you use one word of it. Misalignment does the same in miniature: a contiguous but 4-byte-offset warp load straddles two lines.

The classic instance is **matrix transpose**. Reading `A[i][j]` row-major with `threadIdx.x → j` is coalesced (adjacent threads → adjacent columns → one line). But writing the transposed result `B[j][i]` with the same thread mapping means adjacent threads write to addresses `stride` apart — every write is a separate transaction. You cannot make both the read and the write coalesced in one direct pass; the standard fix is to **stage through shared memory**: read the input tile coalesced into a shared-memory tile, then read the shared tile in transposed order and write the output coalesced. Which brings the second rule into play.

### Shared memory: banks and conflicts

Shared memory is organized into **32 banks of 4-byte words**, interleaved so that word address `a` lives in bank `(a / 4) mod 32`. The 32 threads of a warp can each access shared memory in one cycle **only if they hit 32 distinct banks** (or the same word — see broadcast). If `k` threads access `k` different words that map to the *same* bank, that's a **k-way bank conflict**, and the hardware serializes it into `k` cycles.

The transpose staging tile exposes this immediately. Declare `__shared__ float tile[32][32]`. Column access — 32 threads reading `tile[0..31][j]` for a fixed `j` — touches addresses `j, 32+j, 64+j, …`, all with `(addr) mod 32 == j`. **Every thread hits bank `j`: a 32-way conflict**, a 32x shared-memory slowdown.

The **`+1` padding trick** fixes it for one word of waste:

```
  tile[32][32]                          tile[32][33]   (one padding column)
  addr(i,j) = i*32 + j                  addr(i,j) = i*33 + j
  bank      = (i*32 + j) mod 32         bank      = (i*33 + j) mod 32
            = j          (for all i)              = (i + j) mod 32   (since 33 ≡ 1 mod 32)
  → column j: all 32 threads → bank j   → column j: threads → banks j, j+1, …, j+31
    ***32-way conflict***                 ***all distinct — conflict-free***
```

Padding to `[32][33]` makes the row stride coprime-ish to 32, so successive rows land in successive banks. The extra column is never read; you waste `32 × 4 B = 128 B` per tile to buy back a 32x access.

**Broadcast is the exception that isn't a conflict.** If all 32 threads read the *same* word (not just the same bank — the same address), the hardware broadcasts it in one access. This is why reading a single scalar or a shared coefficient across a warp is free, and why constant-memory-style access patterns are cheap.

### Swizzling — the version tensor-core kernels actually use

Padding wastes shared memory and doesn't compose well with the 128-bit vectorized `ldmatrix` loads that feed [[Concept - Tensor Cores|tensor-core]] fragments. High-performance libraries instead **swizzle**: permute the logical→physical shared-memory mapping with an XOR, `phys_addr = logical_addr XOR ((logical_addr >> s) & mask) << b`, chosen so that the specific access pattern of `ldmatrix`/`wgmma` is conflict-free with *zero* padding waste. This is the deep arcana inside CUTLASS/CuTe layouts and the [[Concept - Warp Specialization and Async Pipelines on Hopper|async-pipeline]] kernels — the swizzle is baked into the tile's layout type so every fragment load across the whole GEMM avoids conflicts by construction. It is also where hand-written kernels most often go subtly wrong.

## In practice

- **Detection is a two-counter job in Nsight Compute.** For global memory, watch *sectors per request* (ideal 4 for a coalesced fp32 warp load; a value near 32 means scatter) and *global load efficiency*. For shared memory, the *shared-memory bank conflicts* counter reports serialized accesses directly.
- **Where it bites hardest:** [[Concept - Attention Mechanism|attention]] and GEMM kernels (the `Kᵀ` in `QKᵀ` is a transpose that must be swizzled), and **embedding-table lookups** — an [[Concept - Embeddings as Learned Representations|embedding gather]] indexes a huge table by token id, so each warp reads 32 unrelated rows: the textbook uncoalesced access, and often the least-optimized memory op in a training step.

## Failure modes

- **Non-coalesced global access:** *symptom* — a memory-bound kernel runs 2–32x under its expected bandwidth; *cause* — strided/transposed/misaligned layout; *fix* — restructure the access or stage through shared memory; *detection* — sectors-per-request ≫ 4.
- **Bank conflicts after "fixing" coalescing:** you move data through a shared tile to fix global coalescing and introduce a 32-way conflict on the transposed read; the kernel is fast on paper and slow in practice until you pad or swizzle.
- **Padding that breaks vectorized loads:** `+1` padding fixes scalar column access but can misalign 128-bit `ldmatrix`/`float4` loads, trading a bank conflict for a misaligned-access penalty — the reason libraries swizzle instead of pad.

## The non-obvious

The counterintuitive part is that **coalescing and conflict-freedom often trade off against each other**, and the whole game is a two-sided constraint, not a single rule. The transpose is the canonical proof: any direct layout makes exactly one of {read, write} coalesced and the other strided, so you're *forced* into shared memory — and the moment you land there, the naive tile hands you a 32-way bank conflict, so you're *forced* to pad or swizzle. Beginners optimize one side, see no speedup (or a regression), and conclude the effort was wasted; the metric moved from "bad global pattern" to "bad shared pattern." The second non-obvious thing: these rules survive every abstraction layer above them. [[Concept - Triton|Triton]] and `torch.compile` generate coalesced loads and pad/swizzle shared memory *for you*, TMA generates addresses in hardware — but the underlying warp-of-32 and 32-bank facts are unchanged, so when a generated kernel is mysteriously slow, "is this access coalesced, is that tile conflict-free" is still the first question, one abstraction level down.

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
