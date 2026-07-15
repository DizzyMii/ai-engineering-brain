---
tags: [concept, domain/hardware-systems, level/core]
aliases: [roofline analysis, arithmetic intensity, ridge point]
summary: "Predicts whether a kernel is compute- or memory-bound from FLOPs-per-byte, and gives a single plot to decide what to optimize."
---
> **One-paragraph hook:** Before you spend an afternoon hand-tuning a kernel, the roofline model tells you in one division whether tuning compute can help at all. Most non-GEMM operations in a transformer — softmax, LayerNorm, naive attention — are capped not by how fast the chip can multiply, but by how fast it can move bytes from HBM, and no amount of instruction-level cleverness fixes a bandwidth problem. The roofline model is the formalization of [[Concept - The Memory Wall]]: a two-line plot that tells you which wall you're actually up against.

## The mechanism

Define **arithmetic intensity** as the ratio of compute to data movement for a kernel, where "data movement" means traffic to and from HBM — the bottom, highest-capacity, lowest-bandwidth tier of the [[Concept - GPU Memory Hierarchy]], not the fast on-chip tiers above it:

$$I = \frac{\text{FLOPs}}{\text{bytes moved from HBM}}$$

The model's core claim is that attainable performance is capped by the *lower* of two ceilings — what the chip can compute, and what the memory system can feed it:

$$\text{Attainable FLOP/s} = \min(\pi, \; I \times \beta)$$

where $\pi$ is the chip's peak FLOP/s and $\beta$ is its peak HBM bandwidth. Plotted with $I$ (FLOP/byte) on the x-axis (log scale) and attainable FLOP/s on the y-axis (log scale), this traces a diagonal "memory roof" ($I \times \beta$) that rises until it hits a flat "compute roof" ($\pi$) — the shape that gives the model its name:

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

The **ridge point** $I^*= \pi / \beta$ is the intensity at which the two roofs meet — below it, a kernel is memory-bound and its speed scales linearly with intensity; above it, a kernel is compute-bound and more intensity buys nothing. On an H100 (BF16 tensor cores): $I^* \approx 989\,\text{TFLOP/s} / 3.35\,\text{TB/s} \approx 295$ FLOP/byte. That number is the practical takeaway: **you must reuse every byte loaded from HBM roughly 300 times** before the H100's tensor cores stop being starved.

Worked intensities make the ridge point concrete:
- A large FP16/BF16 GEMM has intensity that grows with the matrix dimension ($O(N)$ for an $N\times N \times N$ multiply, since FLOPs grow as $N^3$ but bytes moved as $N^2$) — for large enough matrices it comfortably clears 295 and is compute-bound.
- Softmax, LayerNorm/RMSNorm, and other elementwise or reduction ops have intensity $O(1)$ — a handful of FLOPs per element loaded — and are deeply memory-bound regardless of how well the arithmetic itself is optimized.
- Naive attention (materializing the full $N \times N$ score matrix in HBM) is memory-bound because it writes and rereads that matrix; [[Deep Dive - FlashAttention]] doesn't reduce the FLOP count, it *raises the effective arithmetic intensity* by tiling the computation so the score matrix never leaves SRAM — the roofline model is exactly why that trick works and exactly what it's optimizing.

## In practice

Using the model on a real kernel means measuring, not guessing: profile with Nsight Compute's Speed-of-Light and roofline sections to get achieved FLOP/s and achieved HBM bytes moved, compute $I$ = FLOPs / bytes, and place the point on the chart. If the point sits well below the memory roof at its intensity, you have unrealized bandwidth headroom (something else — occupancy, launch overhead — is the actual bottleneck, not the roofline ceiling itself; see [[Concept - Occupancy and Latency Hiding]]). If it sits near the memory roof but at low intensity, the fix is to raise intensity: [[Concept - Kernel Fusion]] cuts the number of HBM round-trips, and tiling reuses each loaded operand more times (see [[Concept - Matmul Tiling on GPUs]]). If it sits near the compute roof, you're done optimizing memory traffic and further gains require touching the algorithm's FLOP count or moving to a faster numeric format (see [[Concept - Tensor Cores]]). The same reasoning applied outside training explains a core fact about serving economics: autoregressive decode processes one token at a time per sequence, so its intensity is pinned near the memory-bound end of the chart regardless of how big the model is — which is why [[Concept - Latency, Throughput, and Cost in LLM Serving]] treats decode bandwidth, not FLOPs, as the binding constraint.

## Failure modes

- **Treating the model as gospel for small kernels**: the roofline assumes the chip can perfectly overlap memory access with compute and reach steady-state bandwidth; it says nothing about launch latency, warp-scheduling stalls, or a kernel too small to saturate the memory system before it finishes. A grid of only a few blocks can sit far below even the memory roof for reasons the roofline model doesn't model — a latency ceiling has to be added on top for these regimes.
- **Using vendor peak instead of achievable peak**: peak FLOP/s and peak bandwidth numbers on a spec sheet often assume boost clocks or sparsity; using them as $\pi$ and $\beta$ inflates the ridge point and makes a kernel look worse-bound than it is. Use sustained, dense numbers (see [[Concept - GPU Clocks, Power, and Thermal Throttling]] and the caveat in [[Concept - Model FLOPs Utilization (MFU)]]).
- **Ignoring cache effects**: the basic model treats "bytes moved" as HBM traffic only; a kernel with high L2 reuse can look memory-bound by the naive HBM-bytes calculation while actually being bound by something else entirely, because a lot of its traffic never left the chip. Nsight Compute's L2 hit-rate metric is the check.

## The non-obvious

The most common misuse of the roofline model isn't in the math, it's in the framing: engineers new to GPU performance work assume "optimize" means "make the compute faster," and reach for loop unrolling or instruction-level tricks on a kernel that the roofline model would immediately reveal is memory-bound — where those tricks are a rounding error next to fixing the memory access pattern. Running the ridge-point division *first*, before touching any code, is the highest-leverage five minutes in kernel optimization: it tells you which of two completely different toolkits (data-movement reduction vs. compute-throughput tricks) is even worth opening.

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
