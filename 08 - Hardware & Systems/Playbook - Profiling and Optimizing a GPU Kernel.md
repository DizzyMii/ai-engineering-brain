---
tags: [playbook, domain/hardware-systems, level/advanced]
aliases: [GPU kernel profiling, kernel optimization workflow]
summary: "The end-to-end procedure to find a slow kernel's true bottleneck via Nsight Systems/Compute and apply the fix that actually moves the needle."
---

# Playbook - Profiling and Optimizing a GPU Kernel

> **Goal:** find the real bottleneck in a slow kernel and apply the fix for that bottleneck, instead of guessing and hand-tuning blind.
> **When to run this:** a kernel or model region is slower than a reference implementation or its [[Concept - The Roofline Model|roofline-predicted]] bound, or overall [[Concept - Model FLOPs Utilization (MFU)|MFU]] is unexpectedly low.
> **Prerequisites:** Nsight Systems and Nsight Compute (or the vendor equivalent) installed and permitted on the target hardware; an isolated, reproducible repro of the slow region; the target GPU's sustained (not boost-clock) peak FLOPs and HBM bandwidth.

## Steps

1. **Profile the timeline before touching any kernel.** Capture the region with Nsight Systems or `torch.profiler`. *Expected:* a wall-clock breakdown across kernel execution, host-device memcpy, CPU-bound gaps between kernels, and launch overhead. *If not:* large CPU-bound gaps between GPU kernels, with the kernels themselves running fine, mean a launch-overhead or host-sync problem. The fix is CUDA graphs or batched launches, and no kernel internals need rewriting. Skip to the fix map in step 6.

2. **Pick the hot kernel(s).** Rank kernels from step 1 by total time and ignore anything under roughly 5% of runtime. *Expected:* one or two kernels dominate. *If not:* time spread flat across dozens of small kernels is likely a fusion or launch-overhead problem across the board, with no single kernel worth hand-tuning. Work at the [[Concept - Kernel Fusion]] level instead.

3. **Classify the hot kernel with the roofline.** Run Nsight Compute's Speed-of-Light and roofline sections to get achieved GFLOP/s and HBM GB/s, and plot that point against the chip's compute and memory ceilings (see [[Concept - The Roofline Model]]). *Expected:* the point lands clearly below the memory roof, near it, or near the compute roof. *If not:* well below the memory roof at low measured intensity means bandwidth isn't what's limiting you. Go to step 4. Near either roof, you're already close to that ceiling, and the fix is algorithmic: raise intensity with fusion or tiling, or move to a faster numeric format via [[Concept - Tensor Cores]]. Micro-tuning won't help.

4. **Read the warp-stall breakdown.** Nsight Compute's warp state statistics say why warps aren't issuing: *long scoreboard* (waiting on memory), *barrier* (`__syncthreads` contention) or *MIO throttle* (shared-memory or special-function-unit saturation). *Expected:* one stall reason dominates. *If not:* long-scoreboard stalls with low SM-busy percentage are the signature of failed latency hiding; step 5 finds out why. Barrier-dominant stalls point at synchronization granularity inside the kernel, not memory access.

5. **Check the occupancy limiter.** Nsight Compute's occupancy section reports theoretical vs. achieved [[Concept - Occupancy and Latency Hiding|occupancy]] and names the limiting resource: registers/thread, shared memory/block or threads/block. *Expected:* achieved occupancy at or near theoretical for that limiter. *If not:* achieved well below theoretical for the *same* limiter usually means the launch configuration is wrong (grid too small, too few blocks to fill the GPU), not resource pressure. Compare grid size against the GPU's SM count before touching register or shared-memory usage.

6. **Apply the fix, then re-profile.** The fix map:
   - Memory-bound: fuse operations or fix non-coalesced access to cut HBM traffic ([[Concept - Kernel Fusion]], [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]]).
   - Low-occupancy, latency-bound: raise occupancy (`__launch_bounds__`, smaller per-thread footprint) or raise per-thread instruction-level parallelism instead, per [[Concept - Occupancy and Latency Hiding]].
   - Bank conflicts dominate: pad or swizzle shared-memory strides.
   - Off the tensor-core path: align shapes to MMA tile dimensions (multiples of 8/16) and confirm the dtype is supported, per [[Gotchas - GPU Kernel Performance]].

   By typical payoff, fixing non-coalesced access and enabling tensor cores are usually the biggest single wins. Fusion and better tile reuse come next.

7. **Re-run steps 1-5 on the patched kernel.** Confirm the metric you targeted moved (achieved DRAM GB/s for a memory-bound fix, SM-busy/occupancy for a latency-bound one, tensor-core utilization for a shape or dtype fix) and that nothing else regressed.

## Verification

- The targeted Nsight Compute metric moved the right way. Wall-clock alone is noisy and can hide a fix that improved one metric while a different bottleneck absorbed the gain.
- End-to-end wall-clock improved in line with the kernel-level gain. If the kernel got faster in isolation and total runtime didn't move, it wasn't on the critical path. Go back to step 1's timeline.
- Numerical output matches a known-good reference within tolerance. Fusion and precision changes (accumulation dtype, rescaling inside a fused reduction) are the most common way a silent correctness regression rides along with a speedup.
- If the kernel is a meaningful fraction of total training or inference time, model-level [[Concept - Model FLOPs Utilization (MFU)]] (or an equivalent utilization metric) moved too, beyond the isolated benchmark.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Targeted metric didn't move after the fix | Step 3/4 identified the wrong bottleneck | Redo the roofline classification (step 3) and confirm the stall breakdown (step 4) before trusting the fix category |
| Faster on the profiled shape, slower on others | The fix (tile size, block config) was overfit to one shape/batch size | Re-tune or autotune across the shape distribution the kernel sees in production, not one benchmark input |
| Correctness drifted after the fix | A fusion or precision change altered accumulation order or dropped a rescale | Bisect the change; check accumulation dtype in fused reductions and rescaling factors in fused softmax/norm kernels |
| Wall-clock unchanged although kernel GB/s or occupancy improved | The optimized kernel wasn't the critical-path bottleneck | Recheck the Nsight Systems timeline from step 1 for the real bottleneck; launch overhead and host-side sync are common culprits |
| Profiler shows higher occupancy, but the kernel got slower | More occupancy cut the per-thread register budget and killed data reuse (a compute-bound kernel didn't need it) | See [[Concept - Occupancy and Latency Hiding]]. This kernel likely wants fewer, fatter threads with more register-resident reuse |

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
