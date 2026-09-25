---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [gradient noise scale, critical batch, B_noise, B_crit]
summary: "The batch size beyond which more data per step stops buying proportionally faster training — a moving target that grows as loss falls."
---

# Concept - Critical Batch Size

> **One-paragraph hook:** More GPUs under [[Concept - Data Parallelism and ZeRO|data parallelism]] only help if the larger batch converts into fewer optimization steps. Past a threshold called the critical batch size, extra samples per step buy almost no step-count reduction and you're burning compute to fill a cluster. If you know where that threshold sits, and that it moves during training, you can choose a batch size from theory instead of from "however many GPUs we happened to reserve."

## The mechanism

A minibatch gradient is a noisy estimate of the true gradient over the full data distribution. **McCandlish, Kaplan, et al. (2018), "An Empirical Model of Large-Batch Training,"** formalize how much that noise limits optimization progress with the **gradient noise scale**:

$$B_{\text{noise}} \approx \frac{\text{tr}(H \Sigma)}{g^{\top} H g}$$

$H$ is the loss Hessian, $\Sigma$ the per-example gradient covariance and $g$ the true gradient. Intuitively it's the ratio of gradient *variance* (how much individual examples disagree) to gradient *curvature-weighted magnitude* (how much the true signal matters for the step). In practice you estimate it more cheaply from the ratio of the gradient's variance to its squared magnitude, measured at two batch sizes on the same step. Below $B_\text{noise}$, larger batches give a **linear** reduction in steps to a target loss: double the batch, roughly halve the step count, same total compute. Above it, returns fall off sharply. Doubling the batch still doubles compute per step but barely cuts the step count, so total compute grows for little wall-clock benefit.

The critical batch isn't a fixed model property. It **grows over training**. As loss falls, per-example gradients agree more (curvature-weighted disagreement shrinks relative to the signal), which raises $B_\text{noise}$. So batch-size **warmup**, starting small and ramping up instead of fixing one size for the whole run, is a real technique and more than a stability heuristic. GPT-3 ramped its batch from 32k to 3.2M tokens over training, tracking the rising critical batch instead of picking one compromise value.

## In practice

Batch size and [[Concept - Learning Rate Schedules for Pretraining|learning rate]] are coupled. The **linear scaling rule** (LR proportional to batch size) holds in the small-batch regime, but for [[Concept - AdamW at Scale|Adam-family optimizers]] at large batch the empirically useful scaling is closer to **square-root**. The LR has to track batch size: raise it too little and the extra samples per step are partly wasted, too much and the run destabilizes. Real numbers: GPT-3's final training batch was **3.2M tokens**; PaLM ran in the **1–4M token** range. Those aren't arbitrary. They sit near the estimated critical batch for models and datasets of that scale at that point in training.

Budgeting a run means deciding what you're optimizing for. Below the critical batch you're **compute-efficient but slow**, and each added GPU shortens wall-clock time. Above it you're **fast but wasteful**: you pay for compute that doesn't turn into fewer steps, a real cost at [[Concept - The Roofline Model|FLOPs]]-constrained cluster budgets. Reserving a large cluster regardless of model size pushes teams to run above critical batch just to keep every GPU busy. The result is a run that looks fully utilized (near-peak MFU) but converges no faster in wall-clock terms than a smaller, better-matched batch would have.

## Failure modes

- **Running far above the critical batch to saturate a cluster.** MFU looks excellent and the job "uses" every reserved GPU, but loss vs. wall-clock is barely better than at a smaller batch. The giveaway: compare loss at matched *wall-clock time* (not matched step count) against a lower-batch ablation.
- **Running far below the critical batch.** Leaves throughput on the table. More GPUs would help, but a fixed batch-size choice, not the noise-scale theory, is capping DP.
- **Ramping batch size too aggressively.** A jump that outpaces the growth of $B_\text{noise}$ is effectively a step change in optimization dynamics. If the LR isn't re-tuned to match, it can trigger the early instability covered in [[Concept - Training Stability and Loss Spikes]].

## The non-obvious

No batch size is "correct" independent of your objective. Below the critical batch you minimize total compute and pay in wall-clock time; above it you minimize wall-clock time and pay in total compute; and the crossover moves during training. So the critical batch is also a **schedule you can exploit**. Because $B_\text{noise}$ grows as loss falls, a well-designed batch-size ramp keeps a run near the compute/wall-clock optimum throughout training, where a single batch size fixed at step 0 can't. Frontier labs treat batch size as a schedule for this reason, mirroring the [[Concept - Learning Rate Schedules for Pretraining|learning-rate schedule]].

## Connections
- [[Concept - Gradient Accumulation and Microbatching]] — the mechanical technique (microbatching plus accumulation) used to actually hit a target batch size on limited per-GPU memory.
- [[Concept - Learning Rate Schedules for Pretraining]] — LR and batch size are coupled; a batch-size ramp without a matched LR adjustment risks instability.
- [[Concept - Scaling Laws]] — batch size is the lever, alongside parameter/data allocation, that determines how efficiently a fixed compute budget converts into loss reduction.
- [[Concept - AdamW at Scale]] — the optimizer whose large-batch LR scaling behaves closer to square-root than linear, directly shaped by the critical-batch regime.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where the batch-size-vs-compute tradeoff becomes a concrete global-batch-size and grad-accum configuration for a real run.
- [[Concept - The Roofline Model]] — the compute-efficiency framing (FLOPs spent vs. useful progress) that running above the critical batch violates.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the foundational stochastic-gradient noise this whole theory formalizes and quantifies at scale.
- [[Concept - The Hessian Spectrum in Deep Learning]] — the curvature term ($H$) inside the gradient-noise-scale formula that determines how much a given amount of gradient variance actually costs in optimization progress.

## Sources
- McCandlish, Kaplan, Amodei et al. (2018) — "An Empirical Model of Large-Batch Training" — defines the gradient noise scale and the critical batch size theory.
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3) — the batch-size ramp from 32k to 3.2M tokens over training, an applied instance of tracking the rising critical batch.
