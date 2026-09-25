---
tags: [gotchas, domain/hardware-systems, level/advanced]
aliases: []
summary: "The silent 2-10x kernel slowdowns that never raise an error: coalescing, bank conflicts, tensor-core misses, spills, launch overhead, precision flags."
---

All of these share a signature. The kernel returns the right answer, nvidia-smi says the GPU is "busy," code review passes, and you're leaving 2-10x on the table with nothing to tell you. Only a profiler shows them. Correctness testing will never catch them, which is why they're gotchas and not bugs.

## 1. Falling off the tensor-core path

**Symptom:** a matmul-heavy kernel runs ~10x slower than the same shape did a moment ago. Nothing in the math changed, only a shape or dtype upstream.

**Cause:** [[Concept - Tensor Cores]] execute fixed-shape MMA instructions (e.g., `mma.sync` tiles like 16x8x16 on Ampere). If a dimension isn't a multiple of the tile's alignment requirement (commonly 8 or 16, depending on dtype and architecture), or an operand dtype isn't one the tensor-core pipeline supports (a stray `fp32` tensor in a `bf16` graph, an odd `int8`/`fp8` scale shape), cuBLAS/cuDNN silently falls back to the CUDA-core (SIMT ALU) path. No error. On an H100 the CUDA cores deliver ~67 FP32 TFLOP/s against ~989 BF16 TFLOP/s on tensor cores, roughly a 15x gap, and real fallbacks commonly measure ~10x in wall-clock.

**Fix:** pad sequence length, hidden dim or batch to the nearest tile-friendly multiple (8/16/32 depending on precision). Audit dtype consistency across the whole op, especially at reshape/concat boundaries where a default dtype sneaks in.

**Detection:** Nsight Compute's tensor-core utilization metric (`sm__pipe_tensor_op_hmma_cycles_active`) reads near zero on a kernel you expected to be tensor-core-bound. On any unexpectedly slow matmul, check this metric first; nothing else pays off as much.

## 2. Non-coalesced global memory access

**Symptom:** a kernel touching a modest amount of data is HBM-bandwidth-bound anyway, and achieved DRAM throughput is a small fraction of peak.

**Cause:** a warp's 32 threads issue one memory instruction together, and the [[Concept - GPU Memory Hierarchy]] serves it as 32B/64B/128B sector transactions. When consecutive threads touch consecutive addresses, one warp access coalesces into a handful of transactions. When access is strided (row-major access to a column, an unswizzled transpose), the same instruction fans out into up to 32 separate transactions, each fetching a full sector to use a few bytes. That's a 4-32x blowup in HBM traffic for the same useful work.

**Fix:** restructure access so consecutive threads touch consecutive memory. Transpose in shared memory instead of global memory, change the launch's thread-to-data mapping, or use vectorized loads like `float4`.

**Detection:** Nsight Compute's "sectors per request." Anything meaningfully above 1 (for a 32-bit access) or 4 (for a 128-bit access) means you're paying the fan-out tax.

## 3. Kernel launch overhead: death by a thousand tiny kernels

**Symptom:** the profiler's GPU timeline shows short kernels with visible gaps between them, and wall-clock time is much higher than the sum of kernel durations.

**Cause:** each kernel launch costs roughly 5-10 microseconds of CPU-side dispatch and driver overhead in the CUDA runtime. A fused kernel doing 50us of real work barely notices. A PyTorch eager-mode graph with hundreds of tiny elementwise ops per layer, each a few microseconds of compute, can spend more wall-clock time launching kernels than running them. That's the pathology behind [[Concept - Kernel Fusion]].

**Fix:** CUDA graphs (capture the launch sequence once, replay it with near-zero per-launch overhead), or fuse the op chain into fewer kernels (`torch.compile`, hand-written [[Concept - Triton]] kernels).

**Detection:** the Nsight Systems timeline shows CPU-bound gaps between GPU kernels. The GPU is idle waiting for the next launch.

## 4. Register spilling

**Symptom:** a kernel that should be compute-bound shows unexpected local-memory (i.e., HBM-backed) traffic, and gets slower as you unroll loops or add per-thread state.

**Cause:** each SM has a fixed register file (~256 KB, i.e., 64K 32-bit registers, per SM on recent NVIDIA architectures), which the compiler divides among resident threads. If per-thread register demand is too high, `ptxas` spills the excess to "local memory." Despite the name, that's physically HBM, with HBM's ~400-800 cycle latency instead of a register's ~1 cycle.

**Fix:** cap register use with `--maxrregcount` or `__launch_bounds__`, or split an overgrown kernel into smaller ones with less live state per thread.

**Detection:** `ptxas -v` reports spill stores/loads directly at compile time ("X bytes spill stores, Y bytes spill loads"). Check it before you ever profile.

## 5. Shared-memory bank conflicts

**Symptom:** a kernel that's meant to be fast because it stages data through shared memory shows high shared-load latency anyway.

**Cause:** shared memory is 32 banks of 4 bytes each. When several threads in a warp access different addresses in the *same* bank in the same cycle, the hardware serializes them, so an N-way conflict costs N cycles instead of 1. The classic trigger is a `[32][32]` shared tile read column-wise, where consecutive threads hit the same bank stride for stride.

**Fix:** pad the inner dimension by one element (`[32][33]` instead of `[32][32]`) to break the stride alignment, or swizzle the addressing.

**Detection:** Nsight Compute's bank-conflict counter (shared-memory-access stalls) flags it directly. [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] has the full mechanism.

## 6. Small-batch decode and excessive `__syncthreads()`

**Symptom:** SM-busy is low even though occupancy (active warps/SM) looks fine on paper.

**Cause:** high occupancy doesn't guarantee throughput when the kernel is latency-bound instead of bandwidth-bound (see [[Concept - Occupancy and Latency Hiding]]). LLM decode at batch size 1 is the standard case. Each step runs tiny GEMVs (matrix-vector, not matrix-matrix) against the full weight matrix, so speed is set by how fast weights stream from HBM per token, not by available parallelism. Excessive `__syncthreads()` barriers inside a kernel make it worse by serializing warps that could otherwise run ahead.

**Fix:** for decode-bound serving, batch requests. [[Concept - KV Cache]]-aware continuous batching spreads the same weight-streaming cost over many sequences. For barrier-heavy kernels, narrow the synchronization scope or restructure to need fewer cross-warp dependencies.

**Detection:** warp-stall-reason sampling in Nsight Compute. A dominant "barrier" or "long scoreboard" stall reason confirms it.

## 7. The TF32 / `allow_tf32` precision footgun

**Symptom:** the same model, weights and input give a different runtime, or a small accuracy shift, on two machines or two PyTorch versions with no code change.

**Cause:** TF32 is a 19-bit internal tensor-core format NVIDIA uses as a drop-in for FP32 matmul on Ampere+, at roughly 8x the throughput. It's controlled by a global flag (`torch.backends.cuda.matmul.allow_tf32`) whose framework default has flipped more than once across versions. It changes *which hardware path* runs the matmul, so it silently changes both speed and the low bits of the output. Anyone chasing a performance regression or a numerics mismatch who doesn't think to check the flag falls into it.

**Fix:** set the flag explicitly in your training/inference entrypoint instead of relying on the framework default, and log its value with the rest of the run config.

**Detection:** check both `torch.backends.cuda.matmul.allow_tf32` and `torch.backends.cudnn.allow_tf32`. They're independent switches.

## Connections
- [[Concept - The Roofline Model]] — every one of these gotchas is really a way of falling below the roofline's compute ceiling; the model explains *why* they cost what they cost.
- [[Concept - Occupancy and Latency Hiding]] — gotchas #4 and #6 are occupancy-limiter and latency-hiding failures respectively; this note gives the theory this file gives the symptoms.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the full mechanism behind gotchas #1 and #5, at unicorn depth.
- [[Concept - Tensor Cores]] — gotcha #3 only makes sense once you know what a tensor core actually requires from its operands.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the systematic procedure that surfaces every symptom listed here; use it, don't just pattern-match against this list.
- [[Concept - Kernel Fusion]] — the standard fix for gotcha #3 (launch overhead) and a mitigation for several of the memory-bound ones.
- [[Concept - Mixed Precision Training]] — the TF32 footgun (#7) lives at the intersection of kernel performance and training numerics; training runs that silently change precision paths are a recurring source of "why did my loss curve change" tickets.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — gotcha #6 (small-batch decode) is the exact mechanism that makes batching the dominant lever in serving cost and latency tradeoffs.

## Sources
- NVIDIA Nsight Compute documentation — the profiling metrics (sectors-per-request, bank-conflict counters, tensor-core utilization, warp-stall reasons) referenced throughout are direct Nsight Compute output.
- Volkov, V. (2010) — "Better Performance at Lower Occupancy" — the occupancy/latency-hiding backdrop for gotcha #6.
- folklore, weakly sourced: the TF32 default-flip-between-versions footgun (#7) is widely reported by practitioners debugging cross-machine numerics drift, but no single canonical incident write-up exists.
