---
tags: [playbook, domain/hardware-systems, level/advanced]
aliases: [GPU kernel profiling, kernel optimization workflow]
summary: "The end-to-end procedure to find a slow kernel's true bottleneck via Nsight Systems/Compute and apply the fix that actually moves the needle."
---

# Playbook - Profiling and Optimizing a GPU Kernel

> **Goal:** find the real bottleneck in a slow kernel and apply the specific fix for that bottleneck, instead of guessing and hand-tuning blind.
> **When to run this:** a kernel or model region runs slower than a reference implementation, slower than its [[Concept - The Roofline Model|roofline-predicted]] bound, or overall [[Concept - Model FLOPs Utilization (MFU)|MFU]] is unexpectedly low.
> **Prerequisites:** Nsight Systems and Nsight Compute (or vendor equivalent) installed and permitted on the target hardware; a reproducible, isolated repro of the slow region; the target GPU's sustained (not boost-clock) peak FLOPs and HBM bandwidth numbers on hand.

## Steps

1. **Profile the timeline first, before touching any kernel.** Capture the region with Nsight Systems or `torch.profiler`. *Expected observation:* a wall-clock breakdown across kernel execution, host-device memcpy, CPU-bound gaps between kernels, and launch overhead. *Deviation meaning:* if the timeline shows large CPU-bound gaps between GPU kernels rather than kernels themselves running slow, you have a launch-overhead or host-synchronization problem — the fix is CUDA graphs or batching launches, not rewriting any kernel's internals. Skip straight to the fix map in step 6.

2. **Pick the actual hot kernel(s).** From step 1's timeline, rank kernels by total time contribution and ignore anything under roughly 5% of total runtime. *Expected observation:* one or two kernels dominate. *Deviation meaning:* if time is spread flat across dozens of small kernels with none dominating, the problem is likely fusion opportunity or launch overhead across the board, not a single kernel to hand-tune — reconsider at the [[Concept - Kernel Fusion]] level instead of the single-kernel level.

3. **Classify the hot kernel with the roofline.** Run Nsight Compute's Speed-of-Light and roofline sections on it to get achieved GFLOP/s and achieved HBM GB/s, and place that point against the chip's compute and memory ceilings (see [[Concept - The Roofline Model]]). *Expected observation:* the point lands clearly below the memory roof, near the memory roof, or near the compute roof. *Deviation meaning:* well below the memory roof at low measured intensity means something other than bandwidth is the limiter — proceed to step 4. Sitting near either roof means you're close to that ceiling already and the fix is algorithmic (raise intensity via fusion/tiling, or move to a faster numeric format via [[Concept - Tensor Cores]]), not micro-tuning.

4. **Read the warp-stall-reason breakdown.** Nsight Compute's warp state statistics report why warps aren't issuing: *long scoreboard* (waiting on a memory operation), *barrier* (`__syncthreads` contention), or *MIO throttle* (shared-memory/special-function-unit saturation). *Expected observation:* one stall reason clearly dominates. *Deviation meaning:* long-scoreboard-dominant stalls at low SM-busy percentage is the signature of a latency-hiding failure — proceed to step 5 to find out why. Barrier-dominant stalls point at synchronization granularity inside the kernel, not memory access.

5. **Check the occupancy limiter.** Nsight Compute's occupancy section reports theoretical vs. achieved [[Concept - Occupancy and Latency Hiding|occupancy]] and names the binding resource: registers/thread, shared memory/block, or threads/block. *Expected observation:* achieved occupancy at or near theoretical for the given limiter. *Deviation meaning:* achieved well below theoretical for the *same* limiter usually means the launch configuration (grid too small, blocks too few to fill the GPU) is the problem, not resource pressure — check grid size against the GPU's SM count before touching register/shared-memory usage.

6. **Apply the fix from the fix map, then re-profile.** Memory-bound → fuse operations or fix non-coalesced access patterns to cut HBM traffic (see [[Concept - Kernel Fusion]] and [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]]). Low-occupancy, latency-bound → raise occupancy (`__launch_bounds__`, smaller per-thread footprint) or raise per-thread instruction-level parallelism instead, per [[Concept - Occupancy and Latency Hiding]]. Bank-conflict-dominated → pad or swizzle shared-memory strides. Off the tensor-core path entirely → align shapes to MMA tile dimensions (multiples of 8/16) and confirm the dtype is supported, per [[Gotchas - GPU Kernel Performance]]. Ranked by typical payoff: fixing non-coalesced access and enabling tensor cores are usually the largest single wins; fusion and tile-reuse improvements are the next tier.

7. **Re-run steps 1-5 on the patched kernel.** Confirm the specific metric you targeted moved (achieved DRAM GB/s for a memory-bound fix, SM-busy/occupancy for a latency-bound fix, tensor-core utilization for a shape/dtype fix) and that nothing else regressed.

## Verification

- The targeted Nsight Compute metric moved in the expected direction — not just wall-clock time, since wall-clock alone is noisy and can mask a fix that helped one metric while a different bottleneck absorbed the gain.
- End-to-end wall-clock time improved commensurately with the kernel-level gain. If the kernel got measurably faster in isolation but total runtime didn't move, the kernel you optimized was not actually on the critical path — return to step 1's timeline.
- Numerical output is unchanged within tolerance against a known-good reference. Fusion and precision changes (accumulation dtype, rescaling inside a fused reduction) are the most common source of a silent correctness regression riding along with a performance win.
- If the kernel is a meaningful fraction of total training/inference time, the model-level [[Concept - Model FLOPs Utilization (MFU)]] (or equivalent utilization metric) moved, not just the isolated kernel benchmark.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Targeted metric didn't move after the fix | Wrong bottleneck was identified in step 3/4 | Re-run the roofline classification (step 3); confirm the stall-reason breakdown (step 4) before assuming the fix's category was right |
| Faster on the profiled input shape, slower on others | Fix (tile size, block config) was overfit to one shape/batch size | Re-tune or autotune across the real shape distribution the kernel actually sees in production, not a single benchmark input |
| Correctness drifted after the fix | A fusion or precision change altered accumulation order or dropped a rescale step | Bisect the change; check accumulation dtype in any fused reduction and rescaling factors in fused softmax/norm kernels |
| Wall-clock unchanged despite kernel-level GB/s or occupancy improving | The optimized kernel wasn't actually the critical-path bottleneck | Re-check the Nsight Systems timeline from step 1 for a different real bottleneck — launch overhead or host-side sync are common culprits |
| Occupancy went up per the profiler, but the kernel got slower | Raising occupancy reduced per-thread register budget and killed data reuse (a compute-bound kernel didn't need more occupancy) | Revisit [[Concept - Occupancy and Latency Hiding]] — this kernel likely wants fewer, fatter threads with more register-resident reuse, not more resident warps |

## Connections
- [[Concept - The Roofline Model]] — supplies the classification step (compute- vs. memory-bound) that determines which half of the fix map applies.
- [[Concept - Occupancy and Latency Hiding]] — the theory behind steps 4-5's stall-reason and occupancy-limiter analysis, including why higher occupancy is sometimes the wrong fix.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the specific access-pattern diagnosis and fix referenced when the bottleneck is memory-bound with poor coalescing.
- [[Concept - Kernel Fusion]] — the primary technique applied when the fix map calls for cutting HBM round-trips.
- [[Concept - Tensor Cores]] — what "off the tensor-core path" in step 6 means, and the ~10x penalty for falling off it.
- [[Gotchas - GPU Kernel Performance]] — the compiled list of exactly the symptom-cause-fix-detection patterns this playbook's steps 3-6 walk through one at a time.
- [[Concept - Model FLOPs Utilization (MFU)]] — the model-level metric this playbook's kernel-level fixes are ultimately meant to move.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where this exact profiling workflow gets applied to real training-run kernels to diagnose MFU shortfalls, not synthetic benchmarks.
- [[Breakdown - vLLM]] — a production inference engine whose decode-kernel optimization work follows this same profile-classify-fix loop.

## Sources
- Williams, S., Waterman, A., Patterson, D. (2009) — "Roofline: An Insightful Visual Performance Model for Multicore Architectures" — the model underlying step 3's classification.
- Volkov, V. (2010) — "Better Performance at Lower Occupancy" — the reasoning behind step 5's occupancy-isn't-everything caveat, elaborated in [[Concept - Occupancy and Latency Hiding]].
- NVIDIA — Nsight Compute documentation ("Kernel Profiling Guide") — the Speed-of-Light, roofline, and warp-state-statistics sections this playbook's steps 3-5 are built directly on.
