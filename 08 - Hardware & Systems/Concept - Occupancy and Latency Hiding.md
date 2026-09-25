---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [occupancy, latency hiding, warp occupancy]
summary: "How a GPU hides ~400-800 cycle HBM latency by keeping many warps resident per SM, and why more occupancy isn't always faster."
---

# Concept - Occupancy and Latency Hiding

> **One-paragraph hook:** A warp waiting on a global memory load stalls for roughly 400-800 cycles, long enough to issue hundreds of instructions if the SM had something else to do. It does. The warp scheduler switches to another resident warp for free, because each warp owns a private slice of the register file and nothing needs saving or restoring. That's latency hiding, and occupancy (how many warps are resident per SM) is the crudest lever for it. The trap: occupancy is a means. A kernel can be latency-bound at 100% occupancy and blazing fast at 25%, and knowing which case you're in decides whether an afternoon of tuning pays off.

## The mechanism

Each SM has a fixed resource budget, a register file (65,536 32-bit registers on Hopper-class SMs) and shared memory (up to ~228 KB), and schedules work in warps of 32 threads, the real SIMT unit described in [[Concept - The CUDA Programming Model]]. When a block launches, its threads' registers and shared memory are reserved for the block's whole lifetime. Warps from one or more blocks can be resident at once, up to a hardware ceiling of 64 warps/SM on most recent architectures. Every cycle, each of the SM's warp schedulers picks one *eligible* warp, meaning one not stalled on a memory operation, a barrier or a dependent instruction, and issues its next instruction. A stalled warp blocks nothing; it's skipped until it's eligible again. With enough resident warps there's always another eligible one, and the execution units never sit idle waiting on HBM.

**Occupancy** is resident warps ÷ maximum warps per SM. Whichever of three resources runs out first caps it:

- **Registers per thread.** At 128 registers/thread, the cap is 65,536 / 128 = 512 threads = 16 warps resident = 16/64 ≈ **25% occupancy**. Push register use higher and the compiler doesn't refuse. It silently *spills* the excess to local memory, which is HBM-backed, so a register access becomes an HBM round-trip.
- **Shared memory per block**, which trades directly against how many blocks can co-reside on one SM.
- **Threads per block**, subject to per-SM block-count limits.

The formal justification is Little's Law: the number of memory requests that must be *in flight simultaneously* to saturate a given bandwidth at a given latency is

$$N_{\text{required}} = \text{latency} \times \text{bandwidth demand}$$

Occupancy supplies that concurrency by having many warps each issue independent requests. It's not the only source. One warp can keep several independent loads in flight through **instruction-level parallelism (ILP)**, for example prefetching operand B before it needs operand A's result. Volkov's 2010 analysis made this precise: throughput scales with *total outstanding requests*, which is occupancy × ILP-per-warp. A kernel with high per-thread ILP can hide the same latency with a fraction of the warps.

```
SM timeline, 4 resident warps, one memory-bound warp per row:
W0: [compute][----- stall on HBM load -----][compute]
W1:           [compute][compute][compute]
W2:                    [compute][compute][compute]
W3:                              [compute][compute]
scheduler issues:  W0 W1 W1 W2 W1 W2 W3 W0(ready) ...
```
While W0 waits on its load, the scheduler fills the SM's pipelines from W1-W3. No cycle is wasted as long as *someone* is always eligible.

## In practice

Tuning occupancy means working the three limiters directly. `__launch_bounds__(maxThreadsPerBlock, minBlocksPerSM)` tells the compiler to cap register use so a target occupancy is reachable; `maxrregcount` does it globally; block-size sweeps trade shared-memory allocation against resident-block count. Nsight Compute's occupancy section reports theoretical vs. achieved occupancy and names the limiting resource. Check it before touching code, as in the workflow in [[Playbook - Profiling and Optimizing a GPU Kernel]].

This leads to a counterintuitive practice. Many hand-tuned CUTLASS GEMM kernels deliberately run at **25-50% occupancy**, with large per-thread register tiles (an 8×8 accumulator per thread is common) holding far more data in registers than a "thin threads, many warps" design allows. Fewer, fatter threads get more reuse per register load, which is the goal of [[Concept - Matmul Tiling on GPUs]], and they give up the occupancy a memory-bound kernel would need. So [[Concept - The Roofline Model|the roofline classification]] comes first. A compute-bound GEMM wants register-resident reuse over occupancy. A memory-bound elementwise or reduction kernel wants enough independent outstanding loads (via occupancy or ILP) to saturate HBM bandwidth.

The same tension appears one layer up in [[Concept - Continuous Batching|continuous batching]] for LLM serving. Keeping enough decode requests in flight that the GPU never waits for the *next* request is the scheduling-level version of keeping enough warps resident that an SM never waits for the next load. Both hide latency by oversubscription, at different granularities.

## Failure modes

**Register spilling.** Symptom: unexpected local-memory traffic and a slower kernel with no algorithm change. Cause: per-thread register demand exceeds the budget for the block configuration in use. Fix: `maxrregcount`/`__launch_bounds__`, or restructure the kernel to hold less live state per thread. Detection: spill loads/stores reported by `ptxas -v` or Nsight Compute.

**Over-provisioned shared memory.** It silently caps resident blocks per SM well below what registers alone would allow. A kernel can look register-cheap and still sit at low occupancy because a shared-memory buffer was sized for correctness, not performance.

**Chasing 100% occupancy on a compute-bound kernel.** The most common wasted effort. The kernel is already near the compute roof and ILP already hides its latency. Forcing higher occupancy (`__launch_bounds__` with an aggressive register cap) *shrinks* the per-thread register budget, kills the accumulator tiling that made it fast, and the kernel slows down despite a "better" occupancy number. Detection: occupancy goes up in Nsight Compute and achieved GFLOP/s goes down, which tells you occupancy was never the bottleneck.

**Low occupancy on a memory-bound kernel with little per-thread ILP.** Here occupancy does matter. Too few resident warps means too few outstanding HBM requests to reach peak bandwidth. The fix really is more warps, because there isn't enough independent work per thread to add more loads.

## The non-obvious

The instinct from general programming, "keep the machine busy, so maximize occupancy," is wrong often enough in GPU kernel work to be a trap. Volkov's point (2010) is that occupancy is one of *two* independent ways to satisfy Little's Law. The tensor-core-bound kernels that dominate modern deep learning ([[Concept - Tensor Cores]]) are frequently where trading occupancy for register-resident reuse wins outright. A 25% occupancy kernel using ILP and heavy register tiling can beat a 100% occupancy version of the same kernel forced into thinner, more numerous threads to reach that number. So don't ask "what's my occupancy." Ask whether you're latency-bound, and if so, which of the two mechanisms to fix it with. The roofline classification and warp-stall-reason breakdown in [[Playbook - Profiling and Optimizing a GPU Kernel]] answer that directly.

## Connections
- [[Concept - GPU Memory Hierarchy]] — supplies the actual latency numbers (registers ~1 cycle, HBM ~400-800 cycles) that occupancy exists to hide.
- [[Concept - The CUDA Programming Model]] — defines the warp as the scheduling quantum that occupancy counts.
- [[Concept - Matmul Tiling on GPUs]] — the concrete technique (register-resident tiles) that deliberately trades occupancy for reuse in compute-bound kernels.
- [[Concept - The Roofline Model]] — determines whether a kernel even needs high occupancy, or whether it's already compute-bound and occupancy is a red herring.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the end-to-end procedure that uses occupancy and warp-stall analysis as a diagnostic step.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — a second, independent source of stalls that occupancy alone cannot hide, since a bank conflict serializes work within an already-issued warp.
- [[Concept - Continuous Batching]] — the serving-level analog: keeping enough in-flight requests that the GPU never idles between them, the same oversubscription principle one layer up the stack.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where occupancy shortfalls in real kernels show up as measured MFU loss on an actual training run, not a synthetic benchmark.

## Sources
- Volkov, V. (2010) — "Better Performance at Lower Occupancy" (GTC talk) — the foundational argument that ILP, not occupancy alone, determines latency-hiding capacity, and that many fast GEMM kernels deliberately run at low occupancy.
- NVIDIA — CUDA C++ Programming Guide, "Occupancy" and "Execution Configuration Optimizations" — the register/shared-memory/block-count limiter mechanics and the `__launch_bounds__` API.
