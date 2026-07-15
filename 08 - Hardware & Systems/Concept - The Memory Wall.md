---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "Compute has outgrown memory bandwidth for decades, so most deep learning kernels are bottlenecked by data movement, not arithmetic."
---

# Concept - The Memory Wall

> **One-paragraph hook:** The single fact that organizes almost everything in GPU systems engineering is this: FLOPs got cheap much faster than bytes-per-second got cheap. A chip's peak arithmetic rate has grown roughly 3x every two years while its memory bandwidth has grown roughly 1.6x every two years, and that compounding gap means most deep learning kernels never get anywhere near a chip's advertised peak — they are waiting on memory, not computing.

## The mechanism

Every GPU kernel does two things: it moves bytes from HBM into the faster tiers of the [[Concept - GPU Memory Hierarchy|on-chip memory hierarchy]], and it does arithmetic on those bytes. Whether a kernel is *compute-bound* or *memory-bound* is decided by its **arithmetic intensity** — FLOPs performed per byte moved — relative to the chip's own FLOP:byte ratio, formalized in [[Concept - The Roofline Model]]. On an H100 that ratio, the *ridge point*, works out to roughly 989 TFLOP/s ÷ 3.35 TB/s ≈ 295 FLOP/byte. To be compute-bound, a kernel must reuse each byte it loads from HBM around 300 times before moving on. A large GEMM does — its output tile amortizes each input element across many multiply-adds. Softmax, LayerNorm/RMSNorm, elementwise activations, and naive attention do not — they touch each element only a handful of times, so they sit far below the ridge point and are memory-bound no matter how fast the tensor cores are.

The gap that produces this ridge point is not standing still — it is widening. Gholami et al., "AI and Memory Wall" (2024), quantify the trend directly: peak compute has scaled roughly 3x every two years across recent accelerator generations, while DRAM/HBM bandwidth has scaled only about 1.6x every two years. Every new hardware generation makes the ridge point higher, which means a larger and larger share of a model's operations — anything that isn't a large, well-shaped GEMM — falls into the memory-bound region by default.

## In practice

The memory wall shows up as two distinct walls in a working system. The **bandwidth wall** determines kernel-level speed: an elementwise op or normalization layer is capped by how fast HBM can stream data, full stop, independent of tensor-core throughput. The **capacity wall** determines what fits at all: H100 offers 80 GB of HBM3, H200 offers 141 GB of HBM3e at ~4.8 TB/s, and B200 offers 192 GB at roughly 8 TB/s — and those numbers are hard ceilings on how large a model plus its optimizer state plus its KV cache can be before it no longer fits on one device. The capacity wall is the direct driver behind [[Concept - Post-Training Quantization Formats|quantizing weights and KV cache to fewer bytes]] and behind [[Concept - Why Models Don't Fit on One GPU|sharding a model across multiple GPUs]] once it no longer fits on one.

Nearly every performance technique in this domain exists to fight one wall or the other. [[Concept - Kernel Fusion|Kernel fusion]] collapses a chain of memory-bound elementwise ops into one HBM read and one HBM write instead of N of each. [[Deep Dive - FlashAttention|FlashAttention]] tiles the attention computation so the O(N²) score matrix never round-trips through HBM at all, trading extra recomputed FLOPs (which are now cheap) for fewer bytes moved (which are now scarce). Activation recomputation makes the identical trade for training memory. All three techniques are legible only once you accept that FLOPs are the cheap resource and bytes are the expensive one — which is precisely why [[Concept - Why GPUs for Deep Learning|GPUs are built the way they are]].

## Failure modes

**Silent sub-peak throughput:** a kernel runs "correctly" but achieves 10-30% of a chip's advertised FLOP/s with no error raised. Cause: the op is memory-bound and no amount of extra parallelism fixes that. Detection: Nsight Compute's roofline/Speed-of-Light section shows achieved DRAM throughput near its own ceiling while achieved FLOP/s sits far below the compute ceiling — the signature of a memory-bound kernel, not a broken one. Fix: raise arithmetic intensity via fusion or tiling, not by adding more compute.

**Capacity overflow (OOM):** a model, its optimizer state, and its KV cache exceed the HBM ceiling for the device generation in use. Detection: this fails loudly (CUDA OOM), but the *design-time* miss is not checking the [[Reference - Memory Math for Transformers|memory budget]] against the HBM capacity before launch. Fix: quantization, sharding, or activation recomputation, chosen by which term in the memory budget is dominant.

**Treating the wall as fixed:** teams tune a kernel against last generation's ridge point and are surprised when the "optimized" kernel is memory-bound again on newer, faster-compute hardware — the wall moves every generation, and yesterday's compute-bound kernel can become tomorrow's memory-bound one.

## The non-obvious

The memory wall is not just a performance story — it is an energy story, and the energy story is more fundamental. Mark Horowitz's widely cited ISSCC 2014 keynote, "Computing's Energy Problem (and what we can do about it)," put concrete numbers on it: moving a word from off-chip DRAM costs on the order of 100-1000x the energy of the floating-point operation that consumes it. That ratio is why data movement, not arithmetic, dominates a datacenter's power draw and therefore its operating cost — the same energy accounting that shows up at the rack level as [[Concept - GPU Clocks, Power, and Thermal Throttling|power and thermal limits]]. The entire discipline of kernel fusion, tiling, and recomputation that GPU engineers practice is, underneath the performance framing, an energy-minimization discipline. folklore, weakly sourced: several practitioners report that this is also the real reason accelerator vendors keep shrinking numeric formats (BF16 → FP8 → FP4) faster than they grow raw FLOPs — a smaller format halves both the bytes moved *and* the energy per bit, attacking the wall from the capacity side as much as the compute side.

## Connections
- [[Concept - The Roofline Model]] — the formal tool that turns "memory wall" from a slogan into a per-kernel, computable prediction.
- [[Concept - GPU Memory Hierarchy]] — the tiered memory system whose capacity/bandwidth tradeoff is the physical substrate of the wall.
- [[Concept - Kernel Fusion]] — the single most common tactic for pushing a kernel's arithmetic intensity above the ridge point.
- [[Deep Dive - FlashAttention]] — the canonical worked example of trading recomputed FLOPs for avoided HBM traffic.
- [[Concept - Post-Training Quantization Formats]] — the direct response to the capacity half of the wall, shrinking bytes per parameter.
- [[Concept - Why GPUs for Deep Learning]] — explains why the hardware is built to hide latency via parallelism, the other side of this same bandwidth story.
- [[Concept - Why Models Don't Fit on One GPU]] — the training-scale consequence when the capacity wall is hit and sharding becomes mandatory.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — where the energy angle of data movement resurfaces as a hard power/thermal constraint on real clusters.

## Sources
- Gholami, Yao, Kim, et al. (2024) — "AI and Memory Wall" — quantifies the ~3x/2yr compute growth vs. ~1.6x/2yr bandwidth growth gap that this note's arithmetic-intensity threshold depends on.
- Horowitz (2014) — "Computing's Energy Problem (and what we can do about it)," ISSCC keynote — the source for the ~100-1000x energy gap between a FLOP and an off-chip memory access.
