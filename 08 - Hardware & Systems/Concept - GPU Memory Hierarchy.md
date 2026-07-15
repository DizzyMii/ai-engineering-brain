---
tags: [concept, domain/hardware-systems, level/core]
aliases: []
summary: "The tiered memory system inside an NVIDIA GPU — registers, shared memory/L1, L2, HBM — trading roughly 1000x capacity for roughly 1000x bandwidth at each end."
---

# Concept - GPU Memory Hierarchy

> **One-paragraph hook:** Every fast GPU kernel is, underneath whatever algorithm it implements, an exercise in staging data down a four-tier memory pyramid — registers, shared memory/L1, L2, HBM — so that expensive operands are loaded from off-chip memory once and reused many times from on-chip memory before being evicted. Get the staging wrong and a kernel silently runs at a fraction of the chip's peak rate; get it right and you approach [[Concept - The Roofline Model|the roofline]].

## The mechanism

```
   FAST / SMALL                                          SLOW / LARGE
  ┌────────────────┐
  │   Registers     │  ~256 KB/SM (64K × 32-bit)   ~1 cycle     per-thread
  ├────────────────┤
  │ Shared mem / L1 │  up to ~228 KB/SM (Hopper)    ~20-30 cyc  per-block, SW-managed
  ├────────────────┤
  │   L2 cache      │  ~50 MB (H100)                ~200 cyc    chip-wide
  ├────────────────┤
  │   HBM3          │  80 GB @ ~3.35 TB/s (H100)     ~400-800c  off-chip
  └────────────────┘
   capacity: ~1000x growth (registers → HBM)
   bandwidth: ~1000x drop  (registers → HBM)
```

**Registers** are the fastest tier: ~256 KB per SM (64K 32-bit registers), allocated per-thread, accessible in about 1 cycle. Beyond holding scalar values, the register file is also where each thread stages the operand and accumulator fragments it feeds into the SM's [[Concept - Tensor Cores|tensor cores]] during a warp-level MMA instruction — registers are the last stop before the actual matmul math happens. They are also the scarcest tier: a kernel using too many registers per thread caps how many warps can be resident, and once a thread's register demand exceeds the hardware budget, the compiler silently *spills* the excess to local memory, which is physically backed by HBM. Register spilling is invisible in source code and devastating in practice: a kernel that "should" be register-resident quietly starts making HBM round-trips.

**Shared memory / L1** is a unified, software-managed scratchpad — up to ~228 KB per SM on Hopper — shared by all threads in a block, with ~20-30 cycle latency. Unlike a CPU's hardware-managed L1, the programmer explicitly stages data into it; this is the key enabler of [[Concept - Matmul Tiling on GPUs|GEMM tiling]], where a threadblock loads a tile of the input matrices into shared memory once and every thread in the block reuses it dozens of times instead of re-reading from HBM.

**L2 cache** is ~50 MB on H100, shared across all SMs, with roughly 200-cycle latency. It sits between the per-SM scratchpads and HBM, and modern CUDA exposes L2 residency/persistence controls so a kernel can pin frequently-reused data (a KV cache page, a small weight tensor) in L2 rather than letting the cache's normal LRU behavior evict it.

**HBM3** is the capacity tier: 80 GB at ~3.35 TB/s on H100, or 192 GB at ~8 TB/s HBM3e on B200, with a punishing ~400-800 cycle latency per access. This is simultaneously the layer with the most capacity and the one a kernel most wants to avoid touching more than necessary — it is both [[Concept - The Memory Wall|the bandwidth bottleneck and the capacity bottleneck]] of the entire chip.

## In practice

The pyramid tradeoff is stark and consistent across every GPU generation: capacity grows on the order of 1000x from registers to HBM, while bandwidth *drops* on the order of 1000x over the same span. A fast kernel's entire job is to exploit this — load an operand from HBM exactly once, stage it down through L2 and shared memory into registers, and reuse it as many times as the algorithm allows before it has to be evicted. Tiled GEMM is the canonical example: a 128×128 output tile computed from 128×K and K×128 input tiles does roughly 128²·K FLOPs while loading only about 2·128·K elements from HBM, giving an arithmetic intensity around 64 — comfortably above the ~295 FLOP/byte ridge point once accumulated over enough K.

The tightest real-world constraint this hierarchy imposes is on [[Deep Dive - FlashAttention|FlashAttention]]: its whole algorithm is built around keeping a tile of Q, K, V in shared memory so the N×N score matrix never touches HBM, but shared memory's fixed ~228 KB/SM budget directly caps the tile size the kernel can use — and that cap, in turn, forces a tradeoff between how many warps can be resident (occupancy) and how much work each warp does per tile (arithmetic intensity). Every FlashAttention block-size and warp-count choice is a negotiation with this one number.

For sizing decisions above the kernel level — how much a model, its optimizer state, and its KV cache actually require — see [[Reference - Memory Math for Transformers]], which turns HBM's 80/141/192 GB capacity numbers (H100/H200/B200) into concrete per-model budgets, and directly determines the [[Concept - Post-Training Quantization Formats|precision choices]] and sharding decisions a deployment has to make.

Choice of numeric format acts as a lever on every tier at once: dropping from FP32 to BF16 or [[Concept - Floating Point for Deep Learning|FP8]] halves or quarters the bytes an operand occupies, which stretches how far a fixed register/shared-memory/HBM budget goes and directly raises arithmetic intensity for the same algorithm.

Detection tooling: Nsight Compute's Speed-of-Light section reports achieved vs. peak DRAM throughput, L2 hit rate, and shared-memory usage per block — the three numbers that tell you which tier of this pyramid a kernel is actually bottlenecked on.

## Failure modes

**Register spilling:** symptom is unexpected local-memory (i.e., HBM) traffic and a slower-than-expected kernel with no algorithmic change; cause is a thread using more registers than the per-SM budget allows for the desired occupancy; detection is spill stores/loads reported by `ptxas -v` or Nsight Compute; fix is `maxrregcount`/`__launch_bounds__` or restructuring the kernel to do less per thread.

**Shared-memory bank conflicts:** symptom is high shared-memory load latency despite data being "on-chip"; cause is multiple threads in a warp hitting the same 4-byte memory bank, serializing what should be a single-cycle broadcast; detection is the bank-conflict counter in Nsight Compute; fix is padding the array's stride (`+1` trick) or swizzling the access pattern — see [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]].

**Poor L2 reuse for hot, small tensors:** a [[Concept - KV Cache|KV cache]] page or small weight tensor that's read every step but doesn't get pinned in L2 gets evicted under pressure from other traffic, turning what should be a ~200-cycle L2 hit into a ~600-cycle HBM miss on every access; detection is L2 hit-rate telemetry dropping below expectation for a tensor that should be resident.

**HBM capacity overflow:** the blunt failure — model + activations + KV cache exceed the device's HBM, producing a CUDA out-of-memory error. The fix is upstream of the kernel: quantization, activation recomputation, or sharding, chosen using the memory-budget formulas referenced above.

## The non-obvious

The number that surprises people coming from CPU work: the *entire* fast-memory budget of an H100 — every SM's registers and shared memory, plus the shared L2 — adds up to well under 100 MB across the whole chip, while HBM capacity is 80,000 MB. A single modern server CPU's L3 cache alone can approach or exceed the GPU's *entire* on-chip fast-memory footprint. There is no hardware magic that makes a multi-gigabyte tensor "mostly cached" the way a CPU's cache hierarchy would opportunistically keep a hot working set resident — a GPU kernel author has to *explicitly* decide, tile by tile, what stays on-chip and for how long, because nothing does it for them automatically. This is the direct, mechanical reason GPU kernel engineering reads so differently from CPU performance engineering: on a CPU you mostly get to assume caching works; on a GPU, non-coalesced or unstaged access is the default failure mode, not an edge case, and every optimization technique in this domain — tiling, fusion, recomputation — exists to compensate for the pyramid having no hardware-managed layer above shared memory.

## Connections
- [[Concept - The Roofline Model]] — the formal model that turns "which tier is this kernel bottlenecked on" into a computable, per-kernel prediction.
- [[Concept - Tensor Cores]] — the compute units this memory hierarchy has to keep fed; a tensor core's peak rate is meaningless if operands aren't staged fast enough.
- [[Reference - Memory Math for Transformers]] — turns the HBM capacity numbers in this note into concrete per-model memory budgets.
- [[Deep Dive - FlashAttention]] — the algorithm whose entire design is dictated by the shared-memory tile-size constraint described here.
- [[Concept - Matmul Tiling on GPUs]] — the general technique of staging operands down this pyramid to raise arithmetic intensity for GEMM.
- [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]] — the specific access-pattern failure modes that break the shared-memory and HBM tiers of this hierarchy.
- [[Concept - The Memory Wall]] — the structural, cross-generation reason this hierarchy exists and keeps getting more important, not less.
- [[Concept - Floating Point for Deep Learning]] — the numeric formats (BF16/FP8) that reduce bytes-per-element and therefore stretch every tier's effective capacity and bandwidth.
- [[Concept - KV Cache]] — the inference-time data structure whose placement across HBM and L2 is a direct, high-stakes application of this hierarchy.

## Sources
- NVIDIA (2022) — "NVIDIA H100 Tensor Core GPU Architecture" whitepaper — source for the per-SM register/shared-memory capacities, L2 size, and HBM3 bandwidth figures.
- Wong, Papadopoulou, Sadooghi-Alvandi, Moshovos (2010) — "Demystifying GPU Microarchitecture through Microbenchmarking" — the classic empirical methodology for measuring per-tier latencies (registers/shared/L2/global memory) cited by the cycle-count figures in this note's tradition.
