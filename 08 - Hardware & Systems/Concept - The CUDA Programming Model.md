---
tags: [concept, domain/hardware-systems, level/core]
aliases: [CUDA, SIMT programming model, grid/block/thread]
summary: "CUDA's thread-block-grid hierarchy maps scalar-looking code onto SM/warp hardware; performance depends on thinking in warps, not threads."
---
> **One-paragraph hook:** CUDA lets you write what looks like ordinary per-thread scalar code, `c[i] = a[i] + b[i]`, and have it run correctly on hardware that executes in lockstep groups of 32. Every kernel you'll profile, from a hand-written matmul to a [[Concept - Triton]]-generated fused softmax, is CUDA's grid/block/thread abstraction lowered onto real SMs and warps. It's the abstract machine under every reason [[Concept - Why GPUs for Deep Learning]] gives for running deep learning on a GPU. Misreading that mapping is the most common reason a "correct" kernel runs at 10% of the speed it should.

## The mechanism

CUDA exposes a four-level hierarchy that is both a *logical* programming model and a *literal* description of the hardware:

```
grid
 └─ thread block(s)      -- maps to one Streaming Multiprocessor (SM)
     └─ warp(s)          -- 32 threads, the true unit of execution
         └─ thread(s)    -- what you actually write code for
```

A **thread** is what you write scalar code for: `int i = blockIdx.x * blockDim.x + threadIdx.x;`. The hardware never schedules one thread, though. It schedules a **warp**, 32 threads sharing one program counter and executing the same instruction every cycle (SIMT: Single Instruction, Multiple Threads). A **thread block** is up to 1024 threads that the runtime assigns, whole, to one SM. Threads in a block can synchronize with `__syncthreads()` and share the block's on-chip shared memory. A **grid** is every block one kernel call launches, and blocks go to SMs independently; there's no built-in barrier across blocks inside one launch. Hopper added a fifth rung, the **thread-block cluster**: a group of blocks on different SMs can share a *distributed shared memory* address space over the SM-to-SM network. That closes part of the gap that used to need a full kernel boundary to synchronize across SMs.

Memory is scoped to match. **Registers** are per-thread and the fastest tier (see [[Concept - GPU Memory Hierarchy]]), typically holding [[Concept - Floating Point for Deep Learning]] values in FP32, FP16 or BF16. **Shared memory** is per-block and software-managed, and it's how threads in a block cooperate cheaply. **Global memory** (HBM) is visible to the whole grid and is the only way blocks communicate across a launch. **Constant** and **local** memory round it out. "Local" memory is per-thread but physically lives in HBM, which is the trap register spilling falls into.

Branch divergence is where the SIMT abstraction leaks worst. If threads in a warp take different sides of an `if/else`, the warp serializes. The hardware runs the taken branch with the other threads masked off, then the other branch with the roles swapped. An `if (threadIdx.x % 2 == 0)` inside a warp halves that warp's throughput, because you pay for both paths one after the other while only 16 threads do useful work on each.

Kernel launches are asynchronous to the host. `kernel<<<grid, block>>>(args)` returns to the CPU immediately and the dispatch is queued. Each launch has roughly 5-10 microseconds of fixed overhead. That's nothing for a kernel that runs a millisecond and dominant when you chain thousands of tiny kernels, which is the problem CUDA Graphs and [[Concept - Kernel Fusion]] exist to solve. **Streams** are CUDA's unit of independent concurrency. Kernels and copies in the same stream run in order; different streams can overlap. That's how you hide a `cudaMemcpyAsync` behind compute or run two independent kernels at once on one GPU.

The SIMT model itself has changed across generations. Pre-Volta GPUs had **one program counter per warp**. Divergent branches there were worse than slow: they made some lock-free algorithms (e.g., a warp-level spinlock where threads hold different roles) outright unsafe, because the hardware couldn't guarantee forward progress for a masked-off thread until the other path finished. Volta added **independent thread scheduling**, with a program counter and call stack per thread, so divergent code became correct instead of merely slow. `__syncwarp()` and the cooperative-groups API exist because of this. Threads in a warp are no longer implicitly reconverged at every branch, so an algorithm that assumes warp-synchronous behavior needs an explicit primitive to force it. The old informal assumption, "a warp is a hardware lockstep unit, so I don't need to synchronize," became a real source of bugs after Volta.

## In practice

You'll rarely hand-tune raw CUDA C++ for whole kernels now; cuBLAS, cuDNN, CUTLASS and [[Concept - Triton]] cover most production GEMM and fusion needs. Knowing the model is still what lets you read an Nsight Compute report, reason about why a [[Concept - Tensor Cores]] kernel stages its operands through shared memory (tensor cores compute the [[Concept - Matrix Multiplication as the Atom of Deep Learning]] operation directly on this execution model), or work out why a custom fused kernel is 3x slower than expected. Block sizes are typically 128-256 threads (4-8 warps), balancing parallelism per block against register and shared-memory pressure per SM (see [[Concept - Occupancy and Latency Hiding]]). Grids routinely reach millions of blocks for elementwise ops over large tensors, since blocks are cheap to schedule and the hardware queues them onto SMs as earlier blocks retire. Every call in a PyTorch [[Concept - The Training Loop]], each linear layer and each normalization, becomes one or more of these asynchronous kernel launches queued on a stream under the Python.

## Failure modes

- **Uncoalesced global memory access.** When a warp's 32 threads read non-contiguous addresses (e.g., walking a matrix by row when it's stored column-major), the memory controller issues up to 32 separate transactions instead of one wide one. Nsight Compute's "global load efficiency" or sectors-per-request metric shows it. Fix it by transposing the access pattern or staging through shared memory; see [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]].
- **Branch divergence in hot loops.** The kernel is "correct" but 2-8x slower than a divergence-free rewrite. Warp-execution-efficiency counters show it.
- **Assuming cross-block synchronization inside one launch.** There's no global barrier inside a kernel. Cross-block dependencies need a second launch (or, on Hopper, careful cluster-scoped barriers). Code that assumes otherwise gives silently wrong results that depend on scheduling order, so it's nondeterministic and miserable to debug.
- **Register spilling.** A kernel using too many registers per thread gets some "register" variables silently moved to local memory (HBM-backed), which tanks performance with no compile error. `ptxas -v` reports spill loads/stores. Fix with `__launch_bounds__` or `maxrregcount` (see [[Concept - Occupancy and Latency Hiding]]).

## The non-obvious

Even experienced kernel authors make this costly mistake: they write scalar-looking code and reason about it thread by thread, while the hardware works warp by warp. A `for` loop whose trip count "only" varies per thread really runs as long as the *warp*'s slowest thread, because the warp doesn't retire until all 32 threads finish. One straggler with a long loop stalls the other 31 the whole time. That's why algorithms get re-derived at the warp level (warp shuffles, warp-level reductions, `mma.sync` over a whole warp's fragments). The warp is the unit of computation. Treat it as an implementation detail instead of the thing you're programming and naive CUDA code loses most of its performance there.

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
