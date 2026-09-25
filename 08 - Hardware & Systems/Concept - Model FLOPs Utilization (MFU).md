---
tags: [concept, domain/hardware-systems, level/core]
aliases: [MFU, HFU, hardware FLOPs utilization]
summary: "The fraction of a chip's peak FLOPs actually spent on useful model math; real training runs land at 30-60%, and it sets $/token directly."
---
> **One-paragraph hook:** MFU is the one number that tells you whether a training run is well-engineered or leaving money on the table. Two teams rent identical H100 clusters and train the same architecture. One finishes in 60% of the other's wall-clock time and cost, purely because its MFU is 55% and the other's is 35%. Same hardware, same FLOPs required, very different bill. It's the run-level rollup of everything [[Concept - The Roofline Model]] measures per kernel.

## The mechanism

$$\text{MFU} = \frac{\text{achieved model FLOP/s}}{\text{peak hardware FLOP/s}}$$

"Achieved model FLOP/s" is the useful FLOPs the *model's forward and backward pass* needs, divided by wall-clock time. It isn't the total FLOPs the hardware executed. The related **HFU** (Hardware FLOPs Utilization) also counts FLOPs spent on activation recomputation (see [[Reference - Memory Math for Transformers]]) as useful, since recomputation is a deliberate memory-for-compute trade. HFU counts strictly more FLOPs as useful, so $\text{HFU} \geq \text{MFU}$ always, and the gap tells you how much of the compute budget recomputation is eating.

The numerator comes from the **6ND rule**. Training a dense transformer with $N$ parameters on $D$ tokens costs approximately

$$\text{FLOPs} \approx 6ND$$

split as roughly $2ND$ for the forward pass and $4ND$ for the backward pass. Backward is ~2x forward because it computes gradients with respect to both activations and weights. It's the same $6ND$ estimate behind compute-optimal training budgets in [[Concept - Scaling Laws]]; MFU tells you how much of that budgeted compute you actually realize. Divide $6ND$ by measured wall-clock training time to get achieved FLOP/s, then divide by the chip's peak dense FLOP/s ([[Concept - Tensor Cores]] explains why "dense" matters) to get MFU.

## In practice

Some anchors. Google's PaLM paper reported **46.2% MFU** on TPU v4 pods, and at the time that was strong enough to call out explicitly. GPT-3-class dense-transformer runs commonly land at **30-50%**. Well-tuned Megatron-LM-style runs on H100 clusters with careful 3D-parallelism tuning reach **~50-60%**, and anything above 60% is considered excellent. The theoretical ceiling is 100%, but no real distributed run gets close: communication, synchronization and memory-bound operations can't be removed from a transformer. In [[Deep Dive - Anatomy of a Pretraining Run]], MFU sits on the training dashboard next to loss, because a sudden drop is often the first sign of a hardware or communication problem, not a modeling one.

MFU sets cost and time-to-train almost mechanically. Total FLOPs required ($6ND$) is fixed by model size and token count, so wall-clock time is inversely proportional to MFU. Going from 40% to 55% MFU cuts training time, and GPU-hour cost with it, by roughly $1 - 40/55 \approx 27\%$, with no change to the model or data (see [[Concept - Cost Engineering for LLM Applications]]). Infrastructure teams treat MFU as a KPI worth dedicated headcount for that reason. It isn't a vanity metric.

## Failure modes

- **What erodes MFU, roughly in order of how often it dominates.** Memory-bound operations tensor cores can't touch (LayerNorm/RMSNorm, softmax, attention's non-matmul steps; see [[Concept - The Memory Wall]]) burn wall-clock time and add nothing to the numerator. Exposed, non-overlapped [[Concept - All-Reduce and Collective Operations]] from data/tensor/pipeline parallelism sits on the critical path doing zero model FLOPs. Pipeline bubbles leave stages idle waiting for activations. Small matmuls (short sequences, small per-GPU batch after aggressive sharding) never reach the compute roof. Kernel-launch overhead compounds across the tens of thousands of kernels one forward/backward pass issues.
- **The peak-FLOPs denominator trap.** Vendor spec sheets often quote *sparse* peak FLOPs (the 2:4-sparsity-inflated number) or boost-clock peak instead of sustained dense peak. Divide achieved FLOP/s by an inflated denominator and MFU looks artificially low; use it the other way, as a marketing denominator, and MFU looks artificially high. Always check which peak a reported MFU used. [[Concept - GPU Clocks, Power, and Thermal Throttling]] explains why sustained clocks differ from boost-clock spec numbers.
- **Comparing MFU across parallelism configurations without context.** A run with more aggressive tensor/pipeline parallelism can show lower MFU from communication overhead even when it's the only way the model fits in memory. MFU is a real efficiency signal, but it's not a context-free leaderboard.

## The non-obvious

Once memory-bound ops dominate the remaining gap, chasing MFU has sharply diminishing returns. Teams sometimes over-invest in the last few points when the same engineering time on data pipeline throughput or checkpoint frequency would cut total wall-clock cost more. The right order is almost always: fix the big leaks first (communication overlap, pipeline bubbles, activation recomputation tuning) using the fix-map in [[Playbook - Profiling and Optimizing a GPU Kernel]], and only chase kernel-level roofline gains once parallelism-strategy choices are no longer the obvious bottleneck. A 50%→55% MFU gain from kernel tuning is worth far less engineering time than a 30%→50% gain from fixing a communication-overlap bug.

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
