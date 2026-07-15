---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [occupancy, latency hiding, warp occupancy]
summary: "How a GPU hides ~400-800 cycle HBM latency by keeping many warps resident per SM, and why more occupancy isn't always faster."
---

# Concept - Occupancy and Latency Hiding

> **One-paragraph hook:** A single warp waiting on a global memory load stalls for roughly 400-800 cycles — long enough to issue hundreds of instructions if the SM had anything else to do. It does: the warp scheduler simply switches to a different resident warp for free, because each warp owns a private slice of the register file and needs no save/restore. This is latency hiding, and occupancy — how many warps are resident per SM — is the crudest lever for it. The trap is that occupancy is a means, not the end; a kernel can be latency-bound at 100% occupancy and blazing fast at 25%, and knowing which regime you're in is the difference between a productive afternoon of tuning and a wasted one.

## The mechanism

Each SM holds a fixed budget of resources — a register file (65,536 32-bit registers on Hopper-class SMs) and shared memory (up to ~228 KB) — and schedules work in warps of 32 threads, the true SIMT unit described in [[Concept - The CUDA Programming Model]]. When a resident block is launched, its threads' registers and shared-memory allocation are reserved for the block's entire lifetime; several warps from one or more blocks can be resident simultaneously, up to a hardware ceiling of 64 warps/SM on most recent architectures. Every cycle, each of the SM's warp schedulers picks one *eligible* warp — one not currently stalled on a memory operation, a barrier, or a dependent instruction — and issues its next instruction. A stalled warp doesn't block anything; it's simply skipped until it becomes eligible again. With enough resident warps, there is always another eligible one to issue from, and the SM's execution units never sit idle waiting on HBM.

**Occupancy** is defined as resident warps ÷ maximum warps per SM. It is capped by whichever of three resources runs out first:

- **Registers per thread.** A kernel using 128 registers/thread caps at 65,536 / 128 = 512 threads = 16 warps resident = 16/64 ≈ **25% occupancy**. Push register usage further and the compiler doesn't refuse — it silently *spills* the excess to local memory, which is HBM-backed, turning a register access into an HBM round-trip.
- **Shared memory per block**, which trades directly against how many blocks can co-reside on one SM.
- **Threads per block**, subject to per-SM block-count limits.

The formal justification is Little's Law: the number of memory requests that must be *in flight simultaneously* to saturate a given bandwidth at a given latency is

$$N_{\text{required}} = \text{latency} \times \text{bandwidth demand}$$

Occupancy supplies concurrency by having many warps each issue independent requests. But it isn't the only source of concurrency — a single warp can also keep multiple independent loads in flight via **instruction-level parallelism (ILP)**, e.g. prefetching operand B before it needs operand A's result. Volkov's 2010 analysis made this precise: throughput scales with *total outstanding requests*, which is occupancy × ILP-per-warp, not occupancy alone. A kernel with high per-thread ILP can hide the same latency at a fraction of the warp count.

```
SM timeline, 4 resident warps, one memory-bound warp per row:
W0: [compute][----- stall on HBM load -----][compute]
W1:           [compute][compute][compute]
W2:                    [compute][compute][compute]
W3:                              [compute][compute]
scheduler issues:  W0 W1 W1 W2 W1 W2 W3 W0(ready) ...
```
While W0 waits on its load, the scheduler keeps the SM's pipelines full from W1-W3 — no cycle is wasted, provided *someone* is always eligible.

## In practice

Tuning occupancy means manipulating the three limiters directly: `__launch_bounds__(maxThreadsPerBlock, minBlocksPerSM)` tells the compiler to cap register usage so a target occupancy is achievable; `maxrregcount` does it globally; block-size sweeps trade shared-memory allocation against resident-block count. Nsight Compute's occupancy section reports theoretical vs. achieved occupancy and names the binding limiter — the first thing to check before touching any code, matching the workflow in [[Playbook - Profiling and Optimizing a GPU Kernel]].

The counterintuitive practice this enables: many hand-tuned GEMM kernels in CUTLASS run deliberately at **25-50% occupancy**, using large per-thread register tiles (an 8×8 accumulator per thread is common) that hold far more data in registers than a "thin thread, many warps" design would allow. Fewer, fatter threads mean more data reuse per register load — exactly the goal of [[Concept - Matmul Tiling on GPUs]] — at the cost of the occupancy that a memory-bound kernel would need instead. This is why [[Concept - The Roofline Model|the roofline classification]] has to come first: a compute-bound GEMM wants register-resident reuse over occupancy; a memory-bound elementwise or reduction kernel wants enough independent outstanding loads (occupancy or ILP) to actually saturate HBM bandwidth.

The same tension shows up one layer up the stack in [[Concept - Continuous Batching|continuous batching]] for LLM serving: keeping enough decode requests in flight that the GPU is never waiting on the *next* request to arrive is the scheduling-level analog of keeping enough warps resident that an SM never waits on the next load — both are latency-hiding via oversubscription, just at different granularities.

## Failure modes

**Register spilling.** Symptom: unexpected local-memory traffic and a slower kernel with no algorithm change. Cause: per-thread register demand exceeds the budget for the block configuration in use. Fix: `maxrregcount`/`__launch_bounds__`, or restructure the kernel to hold less live state per thread. Detection: spill loads/stores reported by `ptxas -v` or Nsight Compute.

**Over-provisioned shared memory** silently caps the number of resident blocks per SM well below what registers alone would allow — a kernel can look register-cheap and still sit at low occupancy because of a shared-memory buffer sized for correctness, not performance.

**Chasing 100% occupancy on a compute-bound kernel.** The most common wasted-effort failure: a kernel is already near the compute roof, its latency is already hidden by ILP, and forcing higher occupancy (via `__launch_bounds__` with an aggressive register cap) *reduces* per-thread register budget, kills the accumulator tiling that made it fast, and the kernel gets slower despite a "better" occupancy number. Detection: occupancy improves in Nsight Compute but achieved GFLOP/s drops — the tell that occupancy was never the bottleneck.

**Low occupancy on a genuinely memory-bound kernel with low per-thread ILP.** Here occupancy actually matters: too few resident warps means too few outstanding HBM requests to reach peak bandwidth, and the fix really is more warps, not more independent loads per thread (there isn't enough independent work per thread to add).

## The non-obvious

The instinct carried over from general programming — "keep the machine as busy as possible, so maximize occupancy" — is wrong often enough to be a trap specifically in GPU kernel work. Volkov's insight (2010) is that occupancy is one of *two* independent levers for satisfying Little's Law, and the tensor-core-bound kernels that dominate modern deep learning workloads (see [[Concept - Tensor Cores]]) are frequently the case where trading occupancy for register-resident reuse wins outright: a 25% occupancy kernel using ILP and heavy register tiling can outperform a 100% occupancy version of the same kernel that was forced into thinner, more numerous threads to hit that occupancy number. The correct question is never "what's my occupancy," it's "am I latency-bound, and if so, by which of the two mechanisms should I fix it" — a question the roofline classification and warp-stall-reason breakdown in [[Playbook - Profiling and Optimizing a GPU Kernel]] answer directly.

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
