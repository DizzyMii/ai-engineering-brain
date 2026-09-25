---
tags: [concept, domain/hardware-systems, level/surface]
aliases: []
summary: "Compute has outgrown memory bandwidth for decades, so most deep learning kernels are bottlenecked by data movement, not arithmetic."
---

# Concept - The Memory Wall

> **One-paragraph hook:** One fact organizes almost everything in GPU systems engineering: FLOPs got cheap much faster than bytes per second did. Peak arithmetic rate has grown roughly 3x every two years, memory bandwidth roughly 1.6x. Compound that gap and most deep learning kernels never get near a chip's advertised peak. They spend their time waiting on memory.

## The mechanism

Every GPU kernel does two things. It moves bytes from HBM into the faster tiers of the [[Concept - GPU Memory Hierarchy|on-chip memory hierarchy]], and it does arithmetic on them. Whether it's *compute-bound* or *memory-bound* depends on its **arithmetic intensity** (FLOPs per byte moved) relative to the chip's own FLOP:byte ratio, which [[Concept - The Roofline Model]] formalizes. On an H100 that ratio, the *ridge point*, is roughly 989 TFLOP/s ÷ 3.35 TB/s ≈ 295 FLOP/byte. A kernel has to reuse each byte it loads from HBM around 300 times to be compute-bound. A large GEMM does, since its output tile amortizes each input element over many multiply-adds. Softmax, LayerNorm/RMSNorm, elementwise activations and naive attention don't. They touch each element a handful of times, sit far below the ridge point, and stay memory-bound however fast the tensor cores are.

The gap behind the ridge point is widening. Gholami et al., "AI and Memory Wall" (2024), measured it: peak compute has scaled roughly 3x every two years across recent accelerator generations, while DRAM/HBM bandwidth scaled only about 1.6x. Each new generation raises the ridge point, so a growing share of a model's operations, anything that isn't a large, well-shaped GEMM, lands in the memory-bound region by default.

## In practice

In a running system the memory wall is two walls. The **bandwidth wall** sets kernel speed: an elementwise op or normalization layer is capped by how fast HBM streams data, full stop, regardless of tensor-core throughput. The **capacity wall** sets what fits. H100 has 80 GB of HBM3, H200 has 141 GB of HBM3e at ~4.8 TB/s, and B200 has 192 GB at roughly 8 TB/s. Those are hard ceilings on model plus optimizer state plus KV cache on one device. The capacity wall drives [[Concept - Post-Training Quantization Formats|quantizing weights and KV cache to fewer bytes]] and [[Concept - Why Models Don't Fit on One GPU|sharding a model across GPUs]] once it stops fitting on one.

Nearly every performance technique in this domain fights one wall or the other. [[Concept - Kernel Fusion|Kernel fusion]] turns a chain of memory-bound elementwise ops into one HBM read and one HBM write instead of N of each. [[Deep Dive - FlashAttention|FlashAttention]] tiles attention so the O(N²) score matrix never round-trips through HBM, spending extra recomputed FLOPs (cheap now) to move fewer bytes (scarce now). Activation recomputation makes the same trade for training memory. All three make sense once you accept that FLOPs are the cheap resource and bytes the expensive one, which is also why [[Concept - Why GPUs for Deep Learning|GPUs are built the way they are]].

## Failure modes

**Silent sub-peak throughput.** A kernel runs "correctly" at 10-30% of the chip's advertised FLOP/s and raises no error. Cause: the op is memory-bound, and more parallelism won't fix that. Detection: Nsight Compute's roofline/Speed-of-Light section shows achieved DRAM throughput near its ceiling while achieved FLOP/s sits far below the compute ceiling. That's what a memory-bound kernel looks like; nothing is broken. Fix: raise arithmetic intensity with fusion or tiling. Adding compute won't help.

**Capacity overflow (OOM).** Model, optimizer state and KV cache exceed the device's HBM. It fails loudly (CUDA OOM), but the *design-time* miss is not checking the [[Reference - Memory Math for Transformers|memory budget]] against HBM capacity before launch. Fix: quantization, sharding or activation recomputation, depending on which term of the budget dominates.

**Treating the wall as fixed.** Teams tune a kernel against last generation's ridge point and are surprised when the "optimized" kernel turns memory-bound again on newer hardware with more compute. The wall moves every generation, and yesterday's compute-bound kernel can be tomorrow's memory-bound one.

## The non-obvious

The memory wall is also an energy story, and the energy story runs deeper than the performance one. Mark Horowitz's widely cited ISSCC 2014 keynote, "Computing's Energy Problem (and what we can do about it)," put numbers on it: moving a word from off-chip DRAM costs on the order of 100-1000x the energy of the floating-point operation that uses it. That ratio is why data movement, not arithmetic, dominates a datacenter's power draw and so its operating cost, the same accounting that appears at rack level as [[Concept - GPU Clocks, Power, and Thermal Throttling|power and thermal limits]]. Kernel fusion, tiling and recomputation are framed as performance work, but underneath they minimize energy.

Folklore, weakly sourced: several practitioners say this is also the real reason accelerator vendors shrink numeric formats (BF16 → FP8 → FP4) faster than they grow raw FLOPs. A smaller format halves both the bytes moved *and* the energy per bit, hitting the wall from the capacity side as much as the compute side.

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
