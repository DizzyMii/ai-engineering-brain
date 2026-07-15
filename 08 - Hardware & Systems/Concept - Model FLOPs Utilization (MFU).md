---
tags: [concept, domain/hardware-systems, level/core]
aliases: [MFU, HFU, hardware FLOPs utilization]
summary: "The fraction of a chip's peak FLOPs actually spent on useful model math; real training runs land at 30-60%, and it sets $/token directly."
---
> **One-paragraph hook:** MFU is the single number that tells you whether a training run is well-engineered or leaving money on the table. Two teams can rent identical H100 clusters and train the same model architecture, and one finishes in 60% of the wall-clock time and cost of the other purely because their MFU is 55% instead of 35% — same hardware, same FLOPs required, wildly different bill. It's the training-run-level rollup of everything [[Concept - The Roofline Model]] measures at the kernel level.

## The mechanism

$$\text{MFU} = \frac{\text{achieved model FLOP/s}}{\text{peak hardware FLOP/s}}$$

"Achieved model FLOP/s" means the useful FLOPs the *model's forward and backward pass* requires, divided by wall-clock time — not the total FLOPs the hardware executed. A related metric, **HFU** (Hardware FLOPs Utilization), also counts FLOPs spent on activation recomputation (see [[Reference - Memory Math for Transformers]]) as "useful," since recomputation is a deliberate memory-for-compute trade rather than waste. Because HFU counts strictly more FLOPs as useful, $\text{HFU} \geq \text{MFU}$ always, and the gap between them tells you how much of your compute budget recomputation is consuming.

The numerator comes from the **6ND rule**: training a dense transformer for $N$ parameters on $D$ tokens costs approximately

$$\text{FLOPs} \approx 6ND$$

decomposed as roughly $2ND$ for the forward pass and $4ND$ for the backward pass (backward is ~2x forward because it computes gradients with respect to both activations and weights). This is the same $6ND$ estimate that underlies compute-optimal training budgets in [[Concept - Scaling Laws]] — MFU is what tells you how much of that budgeted compute you're actually realizing. Divide $6ND$ by measured wall-clock training time to get achieved FLOP/s, then divide by the chip's peak dense FLOP/s (see [[Concept - Tensor Cores]] for why "dense" matters) to get MFU.

## In practice

Reported numbers anchor expectations: Google's PaLM paper reported **46.2% MFU** on TPU v4 pods, treated at the time as an unusually strong result worth calling out explicitly. GPT-3-class dense-transformer training runs commonly land in the **30-50%** range. Well-tuned Megatron-LM-style runs on H100 clusters with careful 3D-parallelism tuning reach **~50-60%**, and anything above 60% is considered excellent — the theoretical ceiling is 100% but no real distributed training run gets close, because communication, synchronization, and memory-bound operations are structurally unavoidable in a transformer. In [[Deep Dive - Anatomy of a Pretraining Run]], MFU is tracked continuously on the training dashboard alongside loss, precisely because a sudden drop is often the first symptom of a hardware or communication problem, not a modeling one.

MFU sets cost and time-to-train almost mechanically: since total FLOPs required ($6ND$) is fixed by model size and token count, wall-clock time is inversely proportional to MFU. Going from 40% to 55% MFU cuts training time — and therefore GPU-hours cost — by roughly $1 - 40/55 \approx 27\%$, with zero change to the model or the data (see [[Concept - Cost Engineering for LLM Applications]]). This is why infrastructure teams treat MFU as a first-class KPI worth dedicated headcount to improve, not a vanity metric.

## Failure modes

- **What erodes MFU, ranked by how often it dominates**: memory-bound operations that tensor cores can't touch — LayerNorm/RMSNorm, softmax, attention's non-matmul steps (see [[Concept - The Memory Wall]]) — burn wall-clock time without contributing FLOPs to the numerator; exposed (non-overlapped) [[Concept - All-Reduce and Collective Operations]] from data/tensor/pipeline parallelism sits on the critical path doing zero model FLOPs; pipeline bubbles leave stages idle waiting for activations to flow through; small matmuls (short sequences, small per-GPU batch after aggressive sharding) fail to reach the compute roof; and kernel-launch overhead compounds across the tens of thousands of kernels a full forward/backward pass issues.
- **The peak-FLOPs denominator trap**: vendor spec sheets often quote *sparse* peak FLOPs (the 2:4-sparsity-inflated number) or boost-clock peak rather than sustained dense peak. Dividing achieved FLOP/s by an inflated denominator produces an MFU number that looks artificially low, or — used the other way, as a marketing denominator — an MFU that looks artificially high. Always confirm which peak a reported MFU used; see [[Concept - GPU Clocks, Power, and Thermal Throttling]] for why sustained clocks differ from boost-clock spec numbers in the first place.
- **Comparing MFU across different parallelism configurations without context**: a run with more aggressive tensor/pipeline parallelism can show lower MFU due to communication overhead even though it's the only way the model fits in memory at all — MFU is a real efficiency signal, not a context-free leaderboard number.

## The non-obvious

Chasing MFU past the point where memory-bound ops dominate the remaining gap has sharply diminishing returns, and teams sometimes over-invest in shaving the last few percentage points off MFU when the same engineering time spent on data pipeline throughput or checkpoint frequency would move total wall-clock cost more. The correct order of operations is almost always: fix the big structural leaks first (communication overlap, pipeline bubble minimization, activation recomputation tuning) using the fix-map in [[Playbook - Profiling and Optimizing a GPU Kernel]], and only chase kernel-level roofline optimization once the run is no longer obviously bottlenecked by parallelism-strategy choices — because a 50%→55% MFU gain from kernel tuning is worth far less engineering time than a 30%→50% gain from fixing a communication-overlap bug.

## Connections
- [[Concept - The Roofline Model]] — MFU is what you get when you aggregate roofline-style compute-vs-memory-bound reasoning across an entire training run instead of one kernel.
- [[Reference - Memory Math for Transformers]] — the source of the activation-recomputation FLOP overhead that separates MFU from HFU.
- [[Concept - Scaling Laws]] — scaling-law compute budgets ($6ND$-style estimates) are exactly the FLOP totals MFU measures the efficiency of realizing.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where MFU is tracked as a live health metric throughout an actual training run.
- [[Concept - Cost Engineering for LLM Applications]] — MFU converts directly into $/token and total training cost, making it a budgeting input, not just an engineering metric.
- [[Concept - All-Reduce and Collective Operations]] — exposed, non-overlapped collective communication is one of the largest real-world MFU erosion sources.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — the sustained-vs-boost-clock caveat that determines whether a reported MFU number is honest.
- [[Concept - The Memory Wall]] — the structural reason memory-bound ops (norms, softmax, attention) put a ceiling on MFU no amount of parallelism tuning removes.
- [[Concept - Tensor Cores]] — the source of the peak-FLOPs denominator in the MFU ratio, and the reason "dense" peak is the correct number to use.
- [[Playbook - Profiling and Optimizing a GPU Kernel]] — the procedure for closing the gap once MFU tracking has flagged a run as underperforming.

## Sources
- Chowdhery, A. et al. (2022) — "PaLM: Scaling Language Modeling with Pathways" — reports the 46.2% MFU figure that became a widely-cited benchmark.
- Korthikanti, V. et al. (2022) — "Reducing Activation Recomputation in Large Transformer Models" — the activation-memory/FLOP accounting behind the MFU/HFU distinction.
- Narayanan, D. et al. (2021) — "Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM" — reports achieved TFLOP/s and utilization across 3D-parallel configurations.
