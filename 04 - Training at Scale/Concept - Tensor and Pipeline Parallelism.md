---
tags: [concept, domain/training-at-scale, level/core]
aliases: [TP, PP, model parallelism, intra-layer parallelism, inter-layer parallelism, Megatron parallelism]
summary: "Splitting matmuls (tensor parallelism) or layers (pipeline parallelism) across GPUs to train models too large for state-sharding alone."
---

# Concept - Tensor and Pipeline Parallelism

> **One-paragraph hook:** ZeRO/FSDP shard a model's *redundant* state — every rank still needs enough bandwidth to reconstruct full layers on demand, and if the model is too deep or too wide even that becomes impractical. Tensor and pipeline parallelism instead split the model's actual computation graph: TP cuts each matrix multiply into pieces computed on different GPUs, PP puts different layers on different GPUs. Both let you train models where no single rank ever holds a full layer's worth of activations or weights — at the cost of turning the forward and backward pass into a distributed-systems problem.

## The mechanism

**Tensor parallelism** (Shoeybi et al. 2019, Megatron-LM) splits individual matmuls within a layer across ranks. For a linear layer $Y = XA$, Megatron uses two complementary splits depending on position:

- **Column-parallel**: split $A$ by columns, $A = [A_1, A_2]$, one shard per rank. Since $X$ is already replicated, each rank computes $Y_i = XA_i$ locally with **no communication** — the output is simply partitioned by columns.
- **Row-parallel**: split the weight by rows to match a column-partitioned input; each rank computes a partial sum, and the ranks must **all-reduce** to produce the final output.

The MLP block chains these on purpose: first linear column-parallel → activation (GeLU, elementwise, needs no sync since the partition is preserved) → second linear row-parallel → one all-reduce. Attention splits by heads across ranks (each rank owns a subset of heads — see [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] for how head count interacts with parallelism degree), then a row-parallel output projection needs its own all-reduce. Net result: **each of the two sub-blocks (attention, MLP) needs exactly one [[Concept - All-Reduce and Collective Operations|all-reduce]] in the forward pass and one in the backward pass** — a full transformer layer costs 4 all-reduces total. Because this traffic rides every layer's activations, TP demands the fastest link available (NVLink) and is essentially never run across nodes; degree is capped at ≤8 (a node's GPU count) in practice.

**Pipeline parallelism** partitions *layers* — not individual matmuls — into sequential stages, one or more per device. A microbatch's forward pass walks through stage 0, 1, 2, … in order, then backward walks back. The naive version (GPipe, Huang et al. 2019) runs all forward microbatches through all stages before starting any backward, which leaves early and late stages idle while the pipeline fills and drains:

```
GPipe schedule, p=4 stages, m=4 microbatches (F=forward, B=backward, .=idle bubble)
S0: F1 F2 F3 F4 .  .  .  B4 B3 B2 B1
S1: .  F1 F2 F3 F4 .  B4 B3 B2 B1 .
S2: .  .  F1 F2 F3 F4 B4 B3 B2 B1 .  .
S3: .  .  .  F1 F2 F3 F4 B4 B3 B2 B1 .  .  .
```

The idle fraction — the **bubble** — has a closed form:

$$\text{bubble} = \frac{p-1}{m+p-1}$$

for $p$ pipeline stages and $m$ microbatches. With $p=8$ and only $m=8$, the bubble is $7/15 \approx 47\%$ — nearly half your GPU-time wasted on fill/drain. Pushing $m$ well past $p$ (a rule of thumb is $m \geq 4p$) amortizes this toward zero.

**1F1B** (PipeDream, Narayanan et al. 2019) interleaves one forward and one backward per stage once the pipeline is full, so a stage never needs to hold more than a handful of microbatches' activations in flight — this caps activation memory that naive GPipe (which holds *all* $m$ microbatches' activations until the backward sweep) would blow through. **Interleaved / virtual pipelining** (Megatron, Narayanan et al. 2021) assigns each device several *non-contiguous* stages instead of one contiguous block, shrinking the bubble further at the cost of more, smaller point-to-point sends between stages. Zero-bubble schedules and DeepSeek's **DualPipe** (2024) push this further by splitting the backward pass itself into separate input-gradient and weight-gradient computations that can be scheduled independently, overlapping communication with compute even more tightly.

## In practice

The core trade is bandwidth vs. bubble: TP has cheap-to-express communication (a handful of all-reduces per layer) but it's *heavy* — full activation tensors, every layer, both passes — so it needs NVLink-class bandwidth. PP's point-to-point activation handoffs between stages are comparatively tiny, but you pay in idle time and in load-imbalance risk. Large training runs commonly use **TP=8** (a full node) combined with **PP=8-16** across nodes, layered under DP/ZeRO ([[Concept - Data Parallelism and ZeRO]]) as the outermost dimension — see [[Reference - Parallelism Strategies]] for the full comm/interconnect matrix and [[Pattern - 3D Parallelism Composition]] for how the degrees multiply to the total world size. A subtlety that trips up naive stage assignment: the **first pipeline stage carries the embedding table** and the **last stage carries the unembedding + loss**, both of which are disproportionately heavy (vocab × hidden params and FLOPs), so an even layer-count split still leaves the first/last stages doing more work than the middle ones — real deployments correct for this by giving the boundary stages fewer transformer layers.

## Failure modes

- **TP over a slow inter-node link collapses MFU.** The all-reduce volume is large and happens every layer; running TP across an InfiniBand hop instead of NVLink can drop [[Concept - Why Models Don't Fit on One GPU|MFU]] catastrophically because compute now waits on network round-trips every single layer.
- **PP stage imbalance from embedding/loss layers.** Pipeline throughput is set by its *slowest* stage — a heavier boundary stage stalls every other stage's steady-state cadence, invisible until you profile per-stage step time rather than aggregate throughput.
- **1F1B still needs activation recomputation to fit long sequences.** Interleaving forward/backward caps how many microbatches' activations you hold, but each individual microbatch's activations at long context can still be the dominant memory cost — recomputation (checkpointing) is usually still required on top.
- **Naive GPipe wastes memory storing all microbatch activations** until the backward sweep begins — a correctness-preserving but memory-hungry choice that 1F1B exists specifically to fix.

## The non-obvious

Interleaved/virtual pipelining is often presented as a strict win over naive PP because it shrinks the bubble — but it does so by roughly doubling the number of point-to-point communication events between stages (each device now hands off activations to and from more neighbors per step). On a cluster with marginal inter-node bandwidth, the extra communication overhead can eat the bubble savings, so "more interleaving" is not a free knob to crank; it needs to be tuned against the specific fabric, the same way TP degree does. The general lesson: every technique that shrinks *idle* time in these schedules does so by adding *communication* — there is no scheduling trick that avoids the fundamental bandwidth-vs-bubble trade, only ways to move along it.

## Connections
- [[Concept - Why Models Don't Fit on One GPU]] — the memory ceiling that motivates splitting the model's computation itself once state-sharding alone (ZeRO/FSDP) isn't enough.
- [[Concept - Data Parallelism and ZeRO]] — the outermost dimension in a real layout; DP/ZeRO shards redundant state while TP/PP split the computation graph itself, and the two compose rather than compete.
- [[Concept - Sequence and Context Parallelism]] — the companion dimension that shards the sequence axis instead of layers or tensors, for the activation-memory and long-context problems TP/PP don't solve.
- [[Concept - Expert Parallelism]] — the analogous idea for Mixture-of-Experts models, sharding experts instead of dense layers, with its own all-to-all comm pattern.
- [[Concept - All-Reduce and Collective Operations]] — the collective TP's column/row-parallel split relies on every layer.
- [[Reference - Parallelism Strategies]] — the lookup table placing TP/PP alongside DP, ZeRO, SP, CP, and EP with real comm-volume and interconnect numbers.
- [[Pattern - 3D Parallelism Composition]] — how TP and PP degrees compose with DP/ZeRO into a full device-mesh layout for a real cluster.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — head count directly bounds TP degree for the attention block, since heads are the natural unit tensor parallelism splits on.
- [[Breakdown - Megatron-LM]] — the reference implementation that introduced the column/row-parallel design and the interleaved pipeline schedule described here.

## Sources
- Shoeybi et al. (2019) — "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism" — the column/row-parallel tensor-parallel design.
- Huang et al. (2019) — "GPipe: Efficient Training of Giant Neural Networks using Pipeline Parallelism" — the original fill/drain pipeline schedule and its bubble cost.
- Narayanan et al. (2019) — "PipeDream: Generalized Pipeline Parallelism for DNN Training" — the 1F1B schedule that bounds in-flight activation memory.
- Narayanan et al. (2021) — "Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM" — the interleaved/virtual pipeline schedule.
