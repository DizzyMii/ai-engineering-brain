---
tags: [concept, domain/hardware-systems, level/core]
aliases: [CUDA, SIMT programming model, grid/block/thread]
summary: "CUDA's thread-block-grid hierarchy maps scalar-looking code onto SM/warp hardware; performance depends on thinking in warps, not threads."
---
> **One-paragraph hook:** CUDA lets you write what looks like ordinary per-thread scalar code — `c[i] = a[i] + b[i]` — and have it run correctly on hardware that actually executes in lockstep groups of 32. Every kernel you ever profile, from a hand-written matmul to a [[Concept - Triton]]-generated fused softmax, is CUDA's grid/block/thread abstraction being lowered onto real SMs and warps — the abstract machine underneath every reason [[Concept - Why GPUs for Deep Learning]] gives for putting deep learning on a GPU in the first place. Misunderstanding that mapping is the single most common reason a "correct" kernel runs at 10% of the speed it should.

## The mechanism

CUDA exposes a four-level hierarchy that is simultaneously a *logical* programming model and a *literal* description of the hardware:

```
grid
 └─ thread block(s)      -- maps to one Streaming Multiprocessor (SM)
     └─ warp(s)          -- 32 threads, the true unit of execution
         └─ thread(s)    -- what you actually write code for
```

A **thread** is the unit you write scalar code for: `int i = blockIdx.x * blockDim.x + threadIdx.x;`. But the hardware never schedules a single thread — it schedules a **warp**, 32 threads that share one program counter and execute the same instruction on every cycle (SIMT: Single Instruction, Multiple Threads). A **thread block** is a group of up to 1024 threads that the runtime assigns, whole, to one SM; all threads in a block can synchronize via `__syncthreads()` and share the block's on-chip shared memory. A **grid** is the full set of blocks launched by one kernel call, and blocks are scheduled to SMs independently — there is no built-in barrier across blocks within a single kernel launch. On Hopper, NVIDIA added a fifth rung, the **thread-block cluster**, which lets a group of blocks on different SMs share a *distributed shared memory* address space via SM-to-SM network, closing part of the gap that used to require a full kernel boundary to synchronize across SMs.

Memory is scoped to match this hierarchy: **registers** are per-thread and the fastest tier (see [[Concept - GPU Memory Hierarchy]]) and typically hold [[Concept - Floating Point for Deep Learning]] values in FP32, FP16, or BF16; **shared memory** is per-block, software-managed, and the mechanism that lets threads in a block cooperate cheaply; **global memory** (HBM) is visible to the whole grid and is the only way blocks communicate across a kernel launch; **constant** and **local** memory round out the space — "local" memory is per-thread but physically lives in HBM, which is the trap register spilling falls into.

Branch divergence is where the SIMT abstraction leaks hardest. If threads within a warp take different paths of an `if/else`, the warp does not run both threads' code in parallel — it serializes: the hardware executes the taken branch with the not-taken threads masked off, then the other branch with the roles reversed. An `if (threadIdx.x % 2 == 0)` inside a warp literally halves throughput for that warp, because you pay for both paths sequentially even though only 16 threads execute usefully on each.

Kernel launches are asynchronous with respect to the host: a call like `kernel<<<grid, block>>>(args)` returns to the CPU immediately, and the actual dispatch is queued. Each launch costs roughly 5-10 microseconds of fixed overhead, which is negligible for a kernel that runs for a millisecond but dominates when you chain thousands of tiny kernels back to back — this is exactly the problem CUDA Graphs and kernel fusion (see [[Concept - Kernel Fusion]]) exist to solve. **Streams** are CUDA's unit of independent concurrency: kernels and memory copies queued to the same stream execute in order, but different streams can overlap, which is how you hide a `cudaMemcpyAsync` behind compute or run two independent kernels concurrently on the same GPU.

The SIMT execution model itself changed generation to generation. Pre-Volta GPUs had **one program counter per warp** — divergent branches were not just slow, they made certain lock-free algorithms (e.g., a warp-level spinlock where different threads hold different roles) outright unsafe, because the hardware could not guarantee forward progress for a masked-off thread until the other path finished. Volta introduced **independent thread scheduling**, giving each thread its own program counter and call stack, which makes divergent code correct rather than merely slow. This is why `__syncwarp()` and the cooperative-groups API exist: with independent scheduling, threads in a warp are no longer implicitly reconverged at every branch, so you need an explicit primitive to force it when your algorithm assumes warp-synchronous behavior (the old, informally-relied-upon "warp is a hardware lockstep unit, so I don't need to synchronize" assumption became a real bug source post-Volta).

## In practice

You almost never hand-tune raw CUDA C++ for full kernels anymore — cuBLAS, cuDNN, CUTLASS, and [[Concept - Triton]] cover the vast majority of production GEMM and fusion needs. But understanding the model is what lets you read a Nsight Compute report, reason about why a [[Concept - Tensor Cores]]-using kernel needs its operands staged through shared memory (tensor cores compute the [[Concept - Matrix Multiplication as the Atom of Deep Learning]] operation directly on top of this execution model), or debug why a custom fused kernel is 3x slower than expected. A typical block size choice is 128-256 threads (4-8 warps), balancing enough parallelism per block against register and shared-memory pressure per SM (see [[Concept - Occupancy and Latency Hiding]]). Grid sizes routinely run into the millions of blocks for elementwise ops over large tensors, since blocks are cheap to schedule and the hardware queues them onto SMs as previous blocks retire. Every call in a PyTorch [[Concept - The Training Loop]] — each linear layer, each normalization — expands into one or more of exactly these asynchronous kernel launches queued onto a stream underneath the Python.

## Failure modes

- **Uncoalesced global memory access**: when the 32 threads of a warp read addresses that are not contiguous (e.g., iterating a matrix by row when it's stored column-major), the memory controller has to issue up to 32 separate transactions instead of one wide one. Detected via Nsight Compute's "global load efficiency" or sectors-per-request metric; fixed by transposing access patterns or staging through shared memory. See [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]].
- **Branch divergence inside hot loops**: symptom is a kernel that's "correct" but 2-8x slower than a divergence-free rewrite; detectable via warp-execution-efficiency counters.
- **No cross-block synchronization inside one launch**: a common bug is assuming a global barrier exists within a kernel — it doesn't. Cross-block dependencies require a second kernel launch (or, on Hopper, careful use of cluster-scoped barriers), and code that assumes otherwise produces silently wrong results depending on scheduling order, which makes it nondeterministic and miserable to debug.
- **Register spilling**: a kernel that uses too many registers per thread gets some of its "register" variables silently placed in local memory (HBM-backed), which tanks performance without any compile error — `ptxas -v` reports spill loads/stores; the fix is `__launch_bounds__` or `maxrregcount` (see [[Concept - Occupancy and Latency Hiding]]).

## The non-obvious

The costly mental error experienced kernel authors still make is writing scalar-looking code and reasoning about it thread-by-thread, when the hardware truth is warp-by-warp. A `for` loop with a data-dependent trip count that "only" varies per thread actually varies per *warp*'s slowest thread, because the warp doesn't retire until every one of its 32 threads is done — one straggler thread in a warp with a long loop stalls the other 31 for the whole duration. This is why algorithms are re-derived at the warp level (warp shuffles, warp-level reductions, `mma.sync` operating on a whole warp's worth of fragments) rather than the thread level: the warp, not the thread, is the actual unit of computation, and treating it as an implementation detail rather than the object you're programming against is where naive CUDA code loses most of its performance.

## Connections
- [[Concept - GPU Memory Hierarchy]] — registers/shared/global map directly onto the thread/block/grid scopes described here.
- [[Concept - Occupancy and Latency Hiding]] — how many blocks/warps fit per SM, and why more isn't always faster, is the direct sequel to this note.
- [[Concept - Triton]] — Triton raises the abstraction from per-thread to per-block, automating the coalescing and shared-memory management this note describes manually.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the concrete access-pattern failure modes that fall out of the warp/thread hierarchy.
- [[Concept - Tensor Cores]] — `mma.sync`/`wgmma` instructions are warp-collective operations layered on top of this exact execution model.
- [[Concept - Kernel Fusion]] — reducing the number of kernel launches is the direct answer to the ~5-10us per-launch overhead this note describes.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the workload this whole execution model exists to run efficiently.
- [[Concept - Why GPUs for Deep Learning]] — the surface-level motivation for why this SIMT model exists instead of a CPU-style core.
- [[Concept - Floating Point for Deep Learning]] — the per-thread/per-register data types (FP32, FP16, BF16) that CUDA's memory spaces actually hold.
- [[Concept - The Training Loop]] — a PyTorch forward/backward pass is, underneath the Python, a queue of asynchronous CUDA kernel launches onto a stream.

## Sources
- NVIDIA CUDA C++ Programming Guide (current) — the canonical reference for the execution and memory model described here.
- Volkov, V. (2010) — "Better Performance at Lower Occupancy" — the paper that established independent-thread-scheduling-era intuitions about warps, ILP, and occupancy referenced throughout this domain.
