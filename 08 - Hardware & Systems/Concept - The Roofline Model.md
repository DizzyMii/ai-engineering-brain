---
tags: [concept, domain/hardware-systems, level/core]
aliases: [roofline analysis, arithmetic intensity, ridge point]
summary: "Predicts whether a kernel is compute- or memory-bound from FLOPs-per-byte, and gives a single plot to decide what to optimize."
---
> **One-paragraph hook:** Before you spend an afternoon hand-tuning a kernel, the roofline model tells you with one division whether tuning compute can help at all. Most non-GEMM operations in a transformer (softmax, LayerNorm, naive attention) are limited by how fast the chip moves bytes from HBM, not how fast it multiplies, and instruction-level cleverness doesn't fix a bandwidth problem. The roofline model formalizes [[Concept - The Memory Wall]] as a two-line plot that shows which wall you're up against.

## The mechanism

**Arithmetic intensity** is a kernel's ratio of compute to data movement, where data movement means traffic to and from HBM, the bottom tier of the [[Concept - GPU Memory Hierarchy]] with the most capacity and least bandwidth, not the fast on-chip tiers above it:

$$I = \frac{\text{FLOPs}}{\text{bytes moved from HBM}}$$

The model's claim is that attainable performance is capped by the *lower* of two ceilings: what the chip can compute, and what the memory system can feed it:

$$\text{Attainable FLOP/s} = \min(\pi, \; I \times \beta)$$

where $\pi$ is peak FLOP/s and $\beta$ is peak HBM bandwidth. Plot $I$ (FLOP/byte) on a log x-axis and attainable FLOP/s on a log y-axis and you get a diagonal "memory roof" ($I \times \beta$) rising until it meets a flat "compute roof" ($\pi$). That shape is where the name comes from:

```
 FLOP/s (log)
   ^
   |                 __________________  <- compute roof (peak FLOP/s, π)
   |                /
   |               /
   |              /   <- memory roof (slope = β, bandwidth)
   |             /
   |            /
   |___________/______________________________> Arithmetic Intensity (log)
              I*  (ridge point = π / β)
   memory-bound  |  compute-bound
```

The **ridge point** $I^*= \pi / \beta$ is where the two roofs meet. Below it a kernel is memory-bound and its speed scales linearly with intensity. Above it the kernel is compute-bound and more intensity buys nothing. On an H100 (BF16 tensor cores), $I^* \approx 989\,\text{TFLOP/s} / 3.35\,\text{TB/s} \approx 295$ FLOP/byte. The takeaway: **every byte loaded from HBM has to be reused roughly 300 times** before the H100's tensor cores stop starving.

Some worked intensities:
- A large FP16/BF16 GEMM's intensity grows with matrix dimension ($O(N)$ for an $N\times N \times N$ multiply, since FLOPs grow as $N^3$ and bytes moved as $N^2$). Large enough matrices clear 295 comfortably and are compute-bound.
- Softmax, LayerNorm/RMSNorm and other elementwise or reduction ops have intensity $O(1)$, a handful of FLOPs per element loaded. They're deeply memory-bound however well the arithmetic is optimized.
- Naive attention (materializing the full $N \times N$ score matrix in HBM) is memory-bound because it writes and rereads that matrix. [[Deep Dive - FlashAttention]] leaves the FLOP count alone and *raises effective arithmetic intensity* by tiling so the score matrix never leaves SRAM. The roofline model explains why that works and what it optimizes.

## In practice

On a real kernel you measure instead of guessing. Profile with Nsight Compute's Speed-of-Light and roofline sections to get achieved FLOP/s and achieved HBM bytes, compute $I$ = FLOPs / bytes, and put the point on the chart.

- **Well below the memory roof at its intensity:** you have unused bandwidth. Something else, such as occupancy or launch overhead, is the bottleneck, not the roofline ceiling (see [[Concept - Occupancy and Latency Hiding]]).
- **Near the memory roof at low intensity:** raise intensity. [[Concept - Kernel Fusion]] cuts HBM round-trips, and tiling reuses each loaded operand more times ([[Concept - Matmul Tiling on GPUs]]).
- **Near the compute roof:** memory traffic is done. More speed means cutting the algorithm's FLOP count or moving to a faster numeric format ([[Concept - Tensor Cores]]).

The same reasoning explains a core fact of serving economics. Autoregressive decode handles one token at a time per sequence, so its intensity stays near the memory-bound end of the chart however big the model is. [[Concept - Latency, Throughput, and Cost in LLM Serving]] treats decode bandwidth, not FLOPs, as the limit for that reason.

## Failure modes

- **Treating it as gospel for small kernels.** The roofline assumes perfect overlap of memory access and compute at steady-state bandwidth. It says nothing about launch latency, warp-scheduling stalls, or a kernel too small to saturate memory before it finishes. A grid of a few blocks can sit far below even the memory roof for reasons the model doesn't cover, and those regimes need a latency ceiling added on top.
- **Using vendor peak instead of achievable peak.** Spec-sheet peak FLOP/s and bandwidth often assume boost clocks or sparsity. Use them as $\pi$ and $\beta$ and the ridge point inflates, making a kernel look worse-bound than it is. Use sustained, dense numbers (see [[Concept - GPU Clocks, Power, and Thermal Throttling]] and the caveat in [[Concept - Model FLOPs Utilization (MFU)]]).
- **Ignoring cache effects.** The basic model counts only HBM traffic as bytes moved. A kernel with high L2 reuse can look memory-bound by the naive calculation while being bound by something else entirely, because much of its traffic never left the chip. Check Nsight Compute's L2 hit rate.

## The non-obvious

The usual misuse is in the framing, not the math. Engineers new to GPU performance assume "optimize" means "make the compute faster" and reach for loop unrolling or instruction-level tricks on a kernel the roofline would show is memory-bound. There, those tricks are a rounding error next to fixing the access pattern. Do the ridge-point division *first*, before touching code. Those five minutes pay off more than any others in kernel optimization, because they tell you which of two very different toolkits (reducing data movement vs. compute-throughput tricks) is worth opening.

## Connections
- [[Concept - GPU Memory Hierarchy]] — the bandwidth and latency numbers per tier that the memory roof is built from.
- [[Concept - The Memory Wall]] — the domain-level trend (compute growing faster than bandwidth) that the roofline model formalizes into a per-kernel diagnostic.
- [[Concept - Model FLOPs Utilization (MFU)]] — MFU is the training-run-level rollup of "how close to the compute roof are we running, on average."
- [[Concept - Kernel Fusion]] — the primary technique for moving a kernel's operating point rightward (higher intensity) on the roofline chart.
- [[Concept - Matmul Tiling on GPUs]] — the other main technique for raising intensity, by reusing each loaded operand more times.
- [[Concept - Occupancy and Latency Hiding]] — the reason a kernel can sit below the memory roof even when the roofline classification looks favorable.
- [[Deep Dive - FlashAttention]] — the canonical example of an algorithm redesigned specifically to raise arithmetic intensity past the ridge point.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the step-by-step procedure that uses the roofline model as its classification step.
- [[Concept - Tensor Cores]] — the source of the compute roof ($\pi$) itself; tensor-core throughput sets where the flat ceiling sits.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — why the $\pi$ and $\beta$ used in the model must be sustained, not boost-clock, numbers.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the archetypal compute-bound operation that sits at the far right of the roofline chart.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — why LLM decode is memory-bound (low intensity, one token at a time) is a direct roofline consequence that shapes serving economics.

## Sources
- Williams, S., Waterman, A., Patterson, D. (2009) — "Roofline: An Insightful Visual Performance Model for Multicore Architectures" — the original formulation of the model.
