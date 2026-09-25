---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [operator fusion, fused kernels, op fusion]
summary: "Combining multiple GPU ops into one kernel so intermediates stay on-chip instead of round-tripping HBM — the top lever for memory-bound ops."
---

# Concept - Kernel Fusion

> **One-paragraph hook:** An unfused GPU kernel pays a fixed HBM tax however little arithmetic it does: read the whole input tensor from HBM, write the whole output back. Chain five elementwise ops (bias add, GELU, dropout, residual add, a norm) in a framework that dispatches one kernel per op and you pay that tax five times, though the math per element is trivial. Kernel fusion collapses the chain into one kernel that reads the input once, keeps every intermediate in registers or [[Concept - GPU Memory Hierarchy|shared memory]], and writes only the final output. $N$ read/write passes become essentially one. Most non-GEMM ops in a transformer are bound by [[Concept - The Memory Wall|HBM bandwidth]], not compute, so this is usually the biggest win available before you touch any algorithm.

## The mechanism

Every GPU kernel launch has the same shape: read tensor(s) from HBM into on-chip memory, compute, write result tensor(s) back. For an elementwise or reduction-style op, where FLOPs per element are few, the read and write dominate runtime; the [[Concept - The Roofline Model|roofline model]] calls this low arithmetic intensity. Express a computation as $N$ separate launches and each does its own full read-compute-write against HBM. An input of size $s$ chained through $N$ ops costs roughly $2N \cdot s$ bytes of HBM traffic (one read and one write per op), though the data that actually has to move is the original input and the final output, $2s$ bytes. Fusing the $N$ ops into one kernel keeps intermediates in registers or shared memory between ops and cuts the $2N \cdot s$ traffic toward the $2s$ minimum, roughly an $N\times$ reduction for a chain of $N$ memory-bound ops. The proof that a fusion helped is a measured drop in HBM bytes moved. FLOP counts don't show it; they're typically unchanged or even slightly higher after fusion.

Fusion comes in two shapes. **Vertical fusion** chains a producer straight into a consumer, so op A's output becomes op B's input without leaving the chip (bias-add feeding an activation, say). **Horizontal fusion** puts independent ops into one launch (same grid, same data locality) even though neither needs the other's output. It saves launch overhead, not HBM traffic. Reduction-based fusions such as [[Concept - RMSNorm and LayerNorm|LayerNorm/RMSNorm]] and softmax are a special case. They need a full pass over a row to compute a statistic (mean, variance, max, sum) before any per-element output exists, so the fused kernel has to implement the reduction itself, with shared-memory accumulation or warp-shuffle instructions, instead of just chaining independent elementwise ops.

## In practice

The standard fusion targets in a transformer are the ops [[Concept - The Roofline Model]] flags as memory-bound: bias + activation + dropout in the MLP block, the normalize-and-scale sequence in RMSNorm/LayerNorm, the full softmax reduction, and the biggest one in the stack, the whole multi-stage attention computation. [[Deep Dive - FlashAttention]] fuses attention into one kernel with the same "never materialize the intermediate in HBM" logic, applied to an entire operator instead of a short elementwise chain. Fusion reaches the optimizer too. A **fused AdamW step** applies the update rule to every parameter in one launch instead of one launch per tensor per sub-operation (first moment, second moment, bias correction, weight update). With thousands of parameter tensors, launch overhead alone adds up, so this matters enormously.

Tooling has mostly automated it. **`torch.compile`/TorchInductor** traces a model's forward (and backward) graph and generates fused [[Concept - Triton]] kernels for eligible op chains. **nvFuser** does similar graph-level fusion inside the PyTorch/JIT stack, and XLA runs whole-program fusion as a first-class compiler pass for TPU workloads. Hand-written fusion in Triton or raw CUDA is still common for operators the auto-fusers don't reach. Attention is the main example, which is why FlashAttention is hand-engineered and not compiler-generated. The wins are concrete and unglamorous: fusing a norm-plus-residual-add sequence typically cuts that block's wall-clock time by roughly 2-3x, all from less HBM traffic. Same algorithm, same math, fewer trips to memory.

## Failure modes

- **Fusing across a large GEMM for nothing.** A large matmul is already compute-bound (high arithmetic intensity from [[Concept - Matmul Tiling on GPUs|GEMM tiling]]). Fusing an elementwise op *into* its epilogue helps, and it's free because the output tile is already on-chip. Fusing two independent large GEMMs buys nothing, since neither was memory-bound. Detection: no drop in achieved HBM throughput after the "optimization," because there was no HBM bottleneck to remove.
- **Register pressure and occupancy collapse.** More ops in one kernel means more live values in registers at once (every intermediate in the chain). Register use per thread can climb high enough to cut [[Concept - Occupancy and Latency Hiding|occupancy]] or trigger spills to local memory, and a fusion meant to reduce HBM traffic brings it back through spills. Detection: `ptxas -v` reporting spill loads/stores, or a fused kernel *slower* than the sum of its unfused parts.
- **Recompute-vs-materialize going the wrong way.** Aggressive fusion sometimes means recomputing an intermediate several times inside the kernel instead of storing it once. That's right when the intermediate is cheap to recompute and expensive to store (FlashAttention's backward-pass bet) and wrong when it's expensive. Copy a fusion strategy from one operator to a very different one without re-checking this and performance regresses without any obvious sign.
- **Correctness drift from precision mismatches.** A hand-fused kernel that accumulates a reduction (sum, mean, variance) at lower precision than the unfused reference produces numerically different results. They aren't wrong, but they differ enough to fail a bit-for-bit regression test of fused vs. unfused output. It's a common false alarm over what is a legitimate precision choice.

## The non-obvious

When a model is slow, the instinct is to look for a faster algorithm. For most non-GEMM ops in a transformer, the bottleneck was never the algorithm. It was how many times data crossed the HBM boundary. So before assuming a kernel needs smarter math, check whether it needs *fewer trips to memory*. The diagnostic is [[Concept - The Roofline Model|roofline]] classification (is achieved throughput near the memory ceiling or the compute ceiling?), not a stopwatch on the op.

Fusion also has a ceiling. Once a chain is fully fused down to $2s$ bytes of HBM traffic, you're at the memory-bound floor for it and more fusion does nothing. The only way to go faster then is to change what data has to move at all, which is a different algorithm and a bigger undertaking than fusion. That's FlashAttention's move: it restructures the computation with online softmax so the $O(N^2)$ intermediate never has to exist, instead of only fusing the existing attention formula.

## Connections
- [[Concept - The Memory Wall]] — the underlying reason nearly every fusible operation in a transformer is memory-bound to begin with.
- [[Concept - The Roofline Model]] — the diagnostic tool for deciding whether a given kernel would even benefit from fusion.
- [[Concept - GPU Memory Hierarchy]] — the on-chip tiers (registers, shared memory) that fused intermediates live in instead of round-tripping to HBM.
- [[Deep Dive - FlashAttention]] — the largest and most consequential fusion in the transformer stack, applying this exact logic to the whole attention operator.
- [[Concept - Matmul Tiling on GPUs]] — where fusion meets GEMM specifically, via epilogue fusion on an already-compute-bound operation.
- [[Concept - Triton]] — the kernel language `torch.compile`/TorchInductor emits auto-generated fused kernels in.
- [[Concept - RMSNorm and LayerNorm]] — a canonical reduction-based fusion target, requiring a full-row pass before the per-element output can be written (cross-domain: neural networks).
- [[Concept - Mixed Precision Training]] — the fused-AdamW-step optimization and the precision-mismatch failure mode both interact directly with mixed-precision training's dtype choices (cross-domain: training at scale).
- [[Concept - Occupancy and Latency Hiding]] — the register-pressure ceiling that limits how aggressively a kernel can be fused before occupancy collapses.
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — a more advanced fusion pattern that overlaps memory movement with computation across warps instead of merely collapsing kernel launches.

## Sources
- Sabne, A. (2020) — "XLA: Compiling Machine Learning for Peak Performance" — whole-program fusion as a compiler pass, the model TPU-side fusion follows.
- Dao, Fu, Ermon, Rudra, Ré (2022) — "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness" — the largest worked example of fusion applied to a full operator rather than an elementwise chain.
- PyTorch team — `torch.compile`/TorchInductor design notes (2023) — automatic fused-Triton-kernel generation from a traced model graph.
