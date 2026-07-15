---
tags: [gotchas, domain/hardware-systems, level/advanced]
aliases: []
summary: "The silent 2-10x kernel slowdowns that never raise an error: coalescing, bank conflicts, tensor-core misses, spills, launch overhead, precision flags."
---

Every one of these bugs shares a signature: the kernel returns the right answer, nvidia-smi shows the GPU "busy," and the code review passes — but you're leaving 2-10x on the table and nothing tells you. They only show up in a profiler, which is why they're gotchas rather than bugs: correctness testing will never catch them.

## 1. Falling off the tensor-core path

**Symptom:** A matmul-heavy kernel runs ~10x slower than the same shape run a moment ago, with no code change to the math — just a shape or dtype change upstream.

**Cause:** [[Concept - Tensor Cores]] execute fixed-shape MMA instructions (e.g., `mma.sync` tiles like 16x8x16 on Ampere). If a dimension isn't a multiple of the tile's alignment requirement (commonly 8 or 16, depending on dtype and architecture), or the operand dtype isn't one the tensor-core pipeline supports (a stray `fp32` tensor mixed into a `bf16` graph, or an odd `int8`/`fp8` scale shape), cuBLAS/cuDNN silently falls back to the CUDA-core (SIMT ALU) path instead of erroring. CUDA cores deliver ~67 FP32 TFLOP/s versus ~989 BF16 TFLOP/s on tensor cores on an H100 — roughly a 15x gap, and real fallbacks commonly measure out to ~10x wall-clock.

**Fix:** Pad sequence length, hidden dim, or batch to the nearest tile-friendly multiple (8/16/32 depending on precision); audit dtype consistency across the whole op, especially at reshape/concat boundaries where a default dtype sneaks in.

**Detection:** Nsight Compute's tensor-core utilization metric (`sm__pipe_tensor_op_hmma_cycles_active`) reads near zero on a kernel you expect to be tensor-core-bound. This is the single highest-value metric to check first on any unexpectedly slow matmul.

## 2. Non-coalesced global memory access

**Symptom:** A kernel that touches modest data volume is HBM-bandwidth-bound anyway; achieved DRAM throughput in the profiler is a small fraction of peak.

**Cause:** A warp's 32 threads issue one memory instruction together; the [[Concept - GPU Memory Hierarchy]] services it as 32B/64B/128B sector transactions. If consecutive threads touch consecutive addresses, one warp access coalesces into a handful of transactions. If access is strided (row-major access to a column, or an unswizzled transpose), the same warp instruction fans out into up to 32 separate transactions, each fetching a full sector to use only a few bytes of it — a 4-32x blowup in HBM traffic for identical useful work.

**Fix:** Restructure the access pattern so consecutive threads touch consecutive memory (transpose in shared memory instead of in global memory, change the launch's thread-to-data mapping, or use vectorized loads like `float4`).

**Detection:** Nsight Compute's "sectors per request" metric — anything meaningfully above 1 (for a 32-bit access) or 4 (for a 128-bit access) means you're paying the fan-out tax.

## 3. Kernel launch overhead — death by a thousand tiny kernels

**Symptom:** The GPU timeline in a profiler shows short kernels separated by visible gaps; wall-clock time is much higher than the sum of individual kernel durations.

**Cause:** Each kernel launch costs the CUDA runtime roughly 5-10 microseconds of CPU-side dispatch and driver overhead. A single fused kernel doing real work for 50us barely notices this. A PyTorch eager-mode graph with hundreds of tiny elementwise ops per layer (each individually a few microseconds of actual compute) can spend more wall-clock time launching kernels than running them — this is exactly the pathology that motivates [[Concept - Kernel Fusion]].

**Fix:** CUDA graphs (capture the launch sequence once, replay it with near-zero per-launch overhead) or fuse the op chain into fewer kernels (`torch.compile`, hand-written [[Concept - Triton]] kernels).

**Detection:** Nsight Systems timeline shows CPU-bound gaps between GPU kernels — the GPU is idle waiting on the next launch, not computing.

## 4. Register spilling

**Symptom:** A kernel that should be compute-bound shows unexpected local-memory (i.e., HBM-backed) traffic in the profiler, and gets slower as you unroll loops or add per-thread state.

**Cause:** Each SM has a fixed register file (~256 KB, i.e., 64K 32-bit registers, per SM on recent NVIDIA architectures). The compiler divides this among resident threads. If a kernel's per-thread register demand is too high, `ptxas` spills the excess to "local memory" — which is physically backed by HBM despite the name, with HBM's ~400-800 cycle latency instead of a register's ~1 cycle.

**Fix:** Cap register usage with `--maxrregcount` or `__launch_bounds__`, or split an overgrown kernel into smaller ones with less live state per thread.

**Detection:** `ptxas -v` reports spill stores/loads directly ("X bytes spill stores, Y bytes spill loads") at compile time — check this before you ever profile.

## 5. Shared-memory bank conflicts

**Symptom:** A kernel that's supposed to be fast because it stages data through shared memory shows high shared-load latency anyway.

**Cause:** Shared memory is organized into 32 banks of 4 bytes each. If multiple threads in a warp access different addresses that map to the *same* bank in the same cycle, the hardware serializes those accesses instead of servicing them in parallel — an N-way conflict costs N cycles instead of 1. The classic trigger is a `[32][32]` shared-memory tile accessed column-wise: consecutive threads then hit the same bank stride-for-stride.

**Fix:** Pad the array's inner dimension by one element (`[32][33]` instead of `[32][32]`) to break the stride alignment, or swizzle the addressing pattern.

**Detection:** Nsight Compute's bank-conflict counter (shared-memory-access-related stalls) flags this directly; see also [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] for the full mechanism.

## 6. Small-batch decode and excessive `__syncthreads()`

**Symptom:** SM-busy is low even though occupancy (active warps/SM) looks fine on paper.

**Cause:** High occupancy doesn't guarantee throughput if the kernel is latency-bound rather than bandwidth-bound — see [[Concept - Occupancy and Latency Hiding]]. LLM decode at batch size 1 is the canonical example: each step does tiny GEMVs (matrix-vector, not matrix-matrix) against the full weight matrix, so the kernel is bound by how fast you can stream weights from HBM per token, not by available parallelism. Excessive `__syncthreads()` barriers inside a kernel compound this by serializing warps that could otherwise run ahead independently.

**Fix:** For decode-bound serving, batch requests ([[Concept - KV Cache]]-aware continuous batching amortizes the same weight-streaming cost across many sequences); for barrier-heavy kernels, reduce synchronization scope or restructure to need fewer cross-warp dependencies.

**Detection:** Warp-stall-reason sampling in Nsight Compute — a dominant "barrier" or "long scoreboard" stall reason confirms the diagnosis.

## 7. The TF32 / `allow_tf32` precision footgun

**Symptom:** The same model, same weights, same input produces a different runtime — or a small accuracy shift — on two machines or two PyTorch versions with no code change.

**Cause:** TF32 is a 19-bit internal tensor-core format that NVIDIA uses as a drop-in replacement for FP32 matmul on Ampere+, at roughly 8x the throughput, controlled by a global flag (`torch.backends.cuda.matmul.allow_tf32`) that framework defaults have flipped more than once across versions. Because it changes *which hardware path* executes the matmul, it silently changes both speed and the low bits of numerical output — a debugging trap when someone is chasing either a performance regression or a numerics mismatch and doesn't think to check this flag.

**Fix:** Pin the flag explicitly in your training/inference entrypoint rather than relying on the framework default; log its value alongside other run config.

**Detection:** `torch.backends.cuda.matmul.allow_tf32` and `torch.backends.cudnn.allow_tf32` — check both; they're independent switches.

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
