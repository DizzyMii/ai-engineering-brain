---
tags: [concept, domain/hardware-systems, level/core]
aliases: []
summary: "The tiered memory system inside an NVIDIA GPU — registers, shared memory/L1, L2, HBM — trading roughly 1000x capacity for roughly 1000x bandwidth at each end."
---

# Concept - GPU Memory Hierarchy

> **One-paragraph hook:** Whatever algorithm a fast GPU kernel implements, underneath it is staging data down a four-tier memory pyramid (registers, shared memory/L1, L2, HBM) so expensive operands come from off-chip memory once and get reused many times on-chip before eviction. Stage badly and the kernel silently runs at a fraction of peak. Stage well and you approach [[Concept - The Roofline Model|the roofline]].

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

**Registers** are the fastest tier: ~256 KB per SM (64K 32-bit registers), allocated per thread, about 1 cycle to access. Besides scalar values, the register file holds the operand and accumulator fragments each thread feeds into the SM's [[Concept - Tensor Cores|tensor cores]] during a warp-level MMA instruction. Registers are the last stop before the matmul math. They're also the scarcest tier. Too many registers per thread caps how many warps can be resident, and once a thread's demand exceeds the hardware budget, the compiler silently *spills* the excess to local memory, which physically lives in HBM. You can't see spilling in the source, and it's devastating: a kernel that "should" be register-resident starts making HBM round-trips.

**Shared memory / L1** is a unified, software-managed scratchpad, up to ~228 KB per SM on Hopper, shared by all threads in a block, with ~20-30 cycle latency. A CPU's L1 is hardware-managed; here the programmer stages data in explicitly. That's what makes [[Concept - Matmul Tiling on GPUs|GEMM tiling]] work: a threadblock loads a tile of the input matrices into shared memory once, and every thread in the block reuses it dozens of times instead of re-reading HBM.

**L2 cache** is ~50 MB on H100, shared by all SMs, at roughly 200 cycles. It sits between the per-SM scratchpads and HBM. Modern CUDA exposes L2 residency/persistence controls, so a kernel can pin frequently reused data (a KV cache page, a small weight tensor) in L2 instead of leaving it to normal LRU eviction.

**HBM3** is the capacity tier: 80 GB at ~3.35 TB/s on H100, or 192 GB at ~8 TB/s HBM3e on B200, with a punishing ~400-800 cycle latency per access. It has the most capacity and it's the tier a kernel most wants to avoid. It's both [[Concept - The Memory Wall|the bandwidth bottleneck and the capacity bottleneck]] of the whole chip.

## In practice

The trade is stark and holds across every GPU generation: capacity grows on the order of 1000x from registers to HBM, and bandwidth *drops* on the order of 1000x over the same span. A fast kernel's job is to exploit that. Load an operand from HBM once, stage it through L2 and shared memory into registers, and reuse it as many times as the algorithm allows before eviction. Tiled GEMM is the textbook case. A 128×128 output tile computed from 128×K and K×128 input tiles does roughly 128²·K FLOPs while loading only about 2·128·K elements from HBM, an arithmetic intensity around 64, comfortably above the ~295 FLOP/byte ridge point once accumulated over enough K.

The tightest real constraint lands on [[Deep Dive - FlashAttention|FlashAttention]]. The algorithm keeps a tile of Q, K, V in shared memory so the N×N score matrix never touches HBM, but the fixed ~228 KB/SM shared-memory budget caps the tile size. That cap forces a trade between how many warps can be resident (occupancy) and how much work each warp does per tile (arithmetic intensity). Every FlashAttention block-size and warp-count choice is a negotiation with that one number.

For sizing above the kernel (how much a model, its optimizer state and its KV cache need), [[Reference - Memory Math for Transformers]] turns HBM's 80/141/192 GB capacities (H100/H200/B200) into per-model budgets. Those budgets drive the [[Concept - Post-Training Quantization Formats|precision choices]] and sharding decisions a deployment has to make.

Numeric format is a lever on every tier at once. Going from FP32 to BF16 or [[Concept - Floating Point for Deep Learning|FP8]] halves or quarters the bytes per operand, which stretches a fixed register/shared-memory/HBM budget and raises arithmetic intensity for the same algorithm.

Tooling: Nsight Compute's Speed-of-Light section reports achieved vs. peak DRAM throughput, L2 hit rate, and shared-memory usage per block. Those three numbers tell you which tier a kernel is bottlenecked on.

## Failure modes

**Register spilling.** Symptom: unexpected local-memory (i.e., HBM) traffic and a slower kernel with no algorithmic change. Cause: a thread uses more registers than the per-SM budget allows at the desired occupancy. Detection: spill stores/loads in `ptxas -v` or Nsight Compute. Fix: `maxrregcount`/`__launch_bounds__`, or restructure the kernel to do less per thread.

**Shared-memory bank conflicts.** Symptom: high shared-memory load latency even though the data is "on-chip." Cause: several threads in a warp hit the same 4-byte bank, serializing what should be a single-cycle broadcast. Detection: the bank-conflict counter in Nsight Compute. Fix: pad the array's stride (the `+1` trick) or swizzle the access pattern; see [[Concept - Memory Coalescing and Shared Memory Bank Conflicts]].

**Poor L2 reuse for hot, small tensors.** A [[Concept - KV Cache|KV cache]] page or small weight tensor read every step but not pinned in L2 gets evicted under pressure from other traffic. A ~200-cycle L2 hit becomes a ~600-cycle HBM miss on every access. Detection: L2 hit rate below expectation for a tensor that should be resident.

**HBM capacity overflow.** The blunt one: model + activations + KV cache exceed the device's HBM and you get a CUDA out-of-memory error. The fix is upstream of the kernel (quantization, activation recomputation, or sharding), sized with the memory-budget formulas above.

## The non-obvious

The number that surprises people from CPU work: the *whole* fast-memory budget of an H100, every SM's registers and shared memory plus the shared L2, adds up to well under 100 MB, against 80,000 MB of HBM. One modern server CPU's L3 cache can approach or exceed the GPU's *entire* on-chip fast memory. Nothing makes a multi-gigabyte tensor "mostly cached" the way a CPU cache hierarchy opportunistically keeps a hot working set resident. The kernel author decides *explicitly*, tile by tile, what stays on-chip and for how long, because nothing else will.

That's the mechanical reason GPU kernel engineering reads so differently from CPU performance work. On a CPU you can mostly assume caching works. On a GPU, non-coalesced or unstaged access is the default failure mode, and every optimization technique in this domain (tiling, fusion, recomputation) exists to make up for the pyramid having no hardware-managed layer above shared memory.

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
