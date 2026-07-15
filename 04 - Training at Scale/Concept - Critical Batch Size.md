---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [gradient noise scale, critical batch, B_noise, B_crit]
summary: "The batch size beyond which more data per step stops buying proportionally faster training — a moving target that grows as loss falls."
---

# Concept - Critical Batch Size

> **One-paragraph hook:** Throwing more GPUs at [[Concept - Data Parallelism and ZeRO|data parallelism]] only helps if the resulting larger batch actually converts into fewer optimization steps — past a threshold called the critical batch size, adding more samples per step buys almost nothing in step-count reduction, and you're simply burning compute to fill a cluster. Knowing where that threshold sits (and that it moves during training) is what separates a batch-size choice grounded in theory from one grounded in "however many GPUs we happened to reserve."

## The mechanism

The stochastic gradient computed from a minibatch is a noisy estimate of the true gradient over the full data distribution. **McCandlish, Kaplan, et al. (2018), "An Empirical Model of Large-Batch Training,"** formalize how much that noise limits optimization progress via the **gradient noise scale**:

$$B_{\text{noise}} \approx \frac{\text{tr}(H \Sigma)}{g^{\top} H g}$$

where $H$ is the loss Hessian, $\Sigma$ is the per-example gradient covariance, and $g$ is the true gradient — intuitively, the ratio of gradient *variance* (how much individual examples disagree) to gradient *curvature-weighted magnitude* (how much the true signal actually matters for the step). In practice this quantity is estimated more cheaply via the ratio of the gradient's variance to its squared magnitude, measured across two batch sizes on the same step. Below $B_\text{noise}$, larger batches give a **linear** reduction in the number of steps needed to reach a target loss — doubling batch size roughly halves step count, at the same total compute. Above it, returns diminish sharply: doubling batch size still doubles compute per step but barely reduces the step count further, so total training compute grows for little wall-clock benefit.

The critical batch is not a fixed model property — it **grows over the course of training**. As the loss falls, gradients from individual examples become more consistent with each other (curvature-weighted disagreement shrinks relative to the signal), which raises $B_\text{noise}$. This is why batch-size **warmup** — starting small and ramping up over training rather than fixing one batch size for the whole run — is a real technique, not just a stability heuristic: GPT-3 ramped its batch from 32k to 3.2M tokens over training, tracking the rising critical batch rather than picking a single compromise value.

## In practice

Batch size and [[Concept - Learning Rate Schedules for Pretraining|learning rate]] are coupled, not independent choices: the **linear scaling rule** (LR scales proportionally with batch size) holds in the small-batch regime, but for [[Concept - AdamW at Scale|Adam-family optimizers]] at large batch the empirically useful scaling is closer to **square-root** — the LR must track batch size or the extra samples per step are partially wasted (too little LR increase) or the run destabilizes (too much). Real numbers: GPT-3's final training batch was **3.2M tokens**; PaLM ran in the **1–4M token** range. These are not arbitrary — they sit near the estimated critical batch for models and datasets of that scale at that point in training.

Budgeting a run means deciding what you're actually optimizing for. Below the critical batch, you're **compute-efficient but slow**: each additional GPU genuinely shortens wall-clock time. Above it, you're **fast but wasteful**: you're paying for compute that isn't converting into fewer steps, which is a real cost at [[Concept - The Roofline Model|FLOPs]]-constrained cluster budgets, not just a theoretical inefficiency. A large cluster reserved regardless of model size creates a systemic pressure to run above critical batch simply to keep every GPU busy — a mismatch between hardware utilization and compute efficiency that shows up as a training run that looks fully utilized (near-peak MFU) while actually converging no faster, in wall-clock terms, than a smaller, better-matched batch would have.

## Failure modes

- **Running far above the critical batch to saturate a cluster**: MFU looks excellent and the job "uses" every reserved GPU, but the loss-vs-wall-clock curve is barely better than a smaller batch — the giveaway is comparing loss at matched *wall-clock time* (not matched step count) against a lower-batch ablation.
- **Running far below the critical batch**: leaves throughput on the table — more GPUs would genuinely help, but the run is DP-limited by a fixed batch-size choice rather than by the noise-scale theory.
- **Ramping batch size too aggressively**: a jump that outpaces the growth of $B_\text{noise}$ effectively injects a step change in optimization dynamics, which can trigger the kind of early instability covered in [[Concept - Training Stability and Loss Spikes]] if the LR isn't re-tuned to match.

## The non-obvious

There is no single "correct" batch size independent of what you're optimizing for — below the critical batch you minimize total compute at the cost of wall-clock time, above it you minimize wall-clock time at the cost of total compute, and the crossover point itself moves during training. This means the critical batch is not just a constraint to discover and respect, it's a **schedule you can deliberately exploit**: because $B_\text{noise}$ grows as loss falls, a well-designed batch-size ramp lets a run stay near-optimal on the compute/wall-clock tradeoff throughout training rather than being stuck with whichever single batch size was chosen at step 0 — which is precisely why frontier labs treat batch size as a schedule (mirroring the [[Concept - Learning Rate Schedules for Pretraining|learning-rate schedule]]) rather than a static hyperparameter.

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
