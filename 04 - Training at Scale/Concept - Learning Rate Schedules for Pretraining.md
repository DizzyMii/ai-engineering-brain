---
tags: [concept, domain/training-at-scale, level/core]
aliases: [LR schedule, WSD, warmup-stable-decay, trapezoidal schedule, cosine decay, cosine annealing, inverse-sqrt schedule]
summary: "The warmup-plus-decay shapes (cosine, WSD/trapezoidal, inverse-sqrt) that govern how the learning rate moves over an LLM pretraining run."
---

# Concept - Learning Rate Schedules for Pretraining

> **One-paragraph hook:** The peak learning rate gets all the attention in a config file. The *shape* of the schedule around it (how fast you ramp up, how long you hold, how you decay) decides whether a multi-million-dollar run spikes in the first thousand steps or wastes its last 10% of compute at a rate too high to converge. You don't tune a schedule once and forget it. It's a commitment that interacts with your token budget, your data plan, and whether you can change your mind mid-run at all.

## The mechanism

Every LLM pretraining schedule has at least a **warmup** phase and a **decay** phase. Schedules differ almost entirely in what happens between them.

**Warmup** is a linear ramp from ~0 to the peak learning rate over roughly **0.5-4% of total steps**, often around 2000 steps in absolute terms regardless of run length. It exists because [[Concept - AdamW at Scale|Adam's]] second-moment estimate $v$ starts at zero and stays uncalibrated for many steps. While $\hat v$ is small and noisy, the effective step size $\text{lr}/\sqrt{\hat v}$ can be enormous. Add a poorly conditioned early loss landscape and a run that jumps straight to peak LR can spike or destabilize. Too short a warmup reproduces that early spike. Too long just burns steps at a suppressed learning rate.

**Cosine decay** anneals from peak down to roughly **10% of peak** over the *entire planned token budget*, following

$$\text{lr}(t) = \text{lr}_{\min} + \tfrac{1}{2}(\text{lr}_{\max}-\text{lr}_{\min})\left(1+\cos\!\left(\pi \frac{t - t_{\text{warmup}}}{T - t_{\text{warmup}}}\right)\right)$$

for $t$ between the end of warmup and the total step count $T$. The catch is in the formula: you need $T$ in advance, because the curve is shaped to hit the target LR at step $T$. Stop early and you're sitting at a *high* learning rate the schedule assumed you'd decayed away from long ago. The loss at that checkpoint is inflated relative to what more decay would have bought, and the only fixes are continuing the original schedule or restarting a new one.

**Warmup-stable-decay** (WSD / trapezoidal; MiniCPM, Hu et al. 2024) avoids that commitment: warmup, then a **long constant phase at peak LR**, then a **short rapid decay** (typically the last 10-20% of steps). The stable phase holds a fixed LR with no reference to a final step count. So you can checkpoint, extend, or branch anywhere on the plateau without invalidating the schedule, unlike cutting a cosine run short, and decide *later* how long to hold before triggering the decay tail. That flexibility is why people use it. Teams have started using it to defer the token-budget decision, or to branch several decay runs off one shared stable checkpoint to try different anneal strategies.

**Inverse-sqrt** ($\text{lr}(t) = \text{lr}_{\max}\sqrt{t_{\text{warmup}}/t}$ for $t > t_{\text{warmup}}$) is the original Transformer schedule (Vaswani et al. 2017). Like WSD it needs no fixed horizon. It keeps decaying slowly forever, so it fits open-ended or continually trained models better than a run with a hard stop.

| Schedule | Shape | Needs total steps upfront? | Best fit |
|---|---|---|---|
| Cosine | warmup → smooth cosine decay to ~10% peak | yes | fixed-budget runs where $T$ is known and fixed |
| WSD / trapezoidal | warmup → long constant → rapid decay (last 10-20%) | no, until you trigger decay | extendable runs, checkpoint branching, deferred budget |
| Inverse-sqrt | warmup → $\propto 1/\sqrt{t}$ decay | no | open-ended or continually-trained runs |

The rapid-decay phase, in cosine's tail and in WSD's decay window alike, locks in a disproportionate share of the model's final capability. So **annealing on higher-quality or domain-specific data** during just that phase, pairing the LR schedule with a [[Concept - Data Mixtures|data schedule]], has become standard practice; holding the mixture constant throughout has not.

## In practice

Peak-LR magnitude scales inversely with model width. That's the empirical basis for [[Concept - muP and Hyperparameter Transfer|muP]], which lets you tune LR on a small proxy model and transfer it to a much larger one without a fresh sweep. Real numbers: **~3e-4** is a typical peak for mid-size dense models, and GPT-3 175B ran an unusually low **6e-5** with a huge batch size. On batch size, the [[Concept - Critical Batch Size|linear scaling rule]] holds for small batches, but Adam's effective scaling at large batch is closer to $\sqrt{\text{batch size}}$. Peak LR has to track batch size, or the extra samples per step buy nothing (or push you unstable). [[Reference - LLM Pretraining Hyperparameters]] has a fuller table of peak-LR / batch-size / warmup-length combinations by model scale, and [[Deep Dive - Anatomy of a Pretraining Run]] shows where the schedule sits in the run lifecycle from budget to release.

Warmup length is counted in [[Concept - Gradient Accumulation and Microbatching|optimizer steps]], not microbatches or samples. A run with heavy gradient accumulation reaches "2000 steps" after far more wall-clock time and far more tokens than one with none. Copying a warmup-step count between configs with different accumulation settings, without adjusting, is a common bug and easy to miss.

## Failure modes

- **LR too high past warmup** causes spikes or outright divergence. The peak value stands for both "fast convergence" and "the edge of stability," and it's easy to set it past that edge for a given architecture/batch/precision combination. [[Concept - Training Stability and Loss Spikes]] catalogs what a spike looks like and how to recover.
- **Decaying fully to 0 vs. to ~10% of peak.** Annealing to zero looks "more converged" but leaves nothing for continued training to build on. Resuming from a near-zero-LR checkpoint starts the next phase cold. Stopping at ~10% keeps enough gradient signal that continued pretraining or annealing phases pick up smoothly, and that's why 10% is the more common choice.
- **Resuming a cosine run with the wrong remaining-steps count.** The cosine shape depends on $T$. Restart from a checkpoint with a mis-recorded step count or a changed token budget and you silently get a *different* curve for the rest of training. The LR decays too fast or too slow relative to the original plan, nothing errors out, and the run under- or over-trains relative to its budget.

## The non-obvious

WSD doesn't buy a better final loss; in practice it lands close to cosine's. What it buys is *optionality*. Cosine bakes a token-budget commitment into every step from the start, so changing your mind about run length means wasting compute (stopping early at an artificially high LR) or accepting a discontinuity (splicing schedules). WSD's stable phase defers the commitment until you trigger the decay tail. Teams have started using the plateau as a fork point: checkpoint once during the stable phase, run several short decay branches with different anneal-data mixtures, and see which lands best before committing a full run (folklore, weakly sourced: this branching pattern is reported informally by teams using WSD-style schedules but isn't something with a single canonical published ablation).

## Connections
- [[Concept - AdamW at Scale]] — the optimizer whose uncalibrated second-moment estimate at step 0 is the mechanistic reason warmup exists.
- [[Concept - Critical Batch Size]] — the batch-size theory that couples directly to peak-LR choice via the sqrt-scaling rule for Adam.
- [[Concept - muP and Hyperparameter Transfer]] — explains why peak LR shrinks with model width and how to transfer a tuned LR across scales instead of re-sweeping.
- [[Concept - Data Mixtures]] — the data-schedule counterpart to the LR schedule; both are commonly annealed together during the rapid-decay phase.
- [[Deep Dive - Anatomy of a Pretraining Run]] — situates the LR schedule within the full run lifecycle, from compute-budget sizing through to release.
- [[Reference - LLM Pretraining Hyperparameters]] — a lookup table of peak-LR, warmup-length, and batch-size combinations by model scale.
- [[Concept - Training Stability and Loss Spikes]] — the failure catalog for what happens when the schedule's peak or warmup length is set wrong.
- [[Concept - Gradient Accumulation and Microbatching]] — warmup length is measured in optimizer steps, which this note's mechanics define relative to microbatch and accumulation settings.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the base optimization loop this schedule modulates; LR scheduling predates Adam and applies to any gradient-descent-family optimizer.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need" — the original Transformer's warmup + inverse-sqrt decay schedule.
- Loshchilov & Hutter (2017) — "SGDR: Stochastic Gradient Descent with Warm Restarts" — establishes cosine annealing as a learning-rate decay shape.
- Hu et al. (2024) — "MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategies" — introduces the warmup-stable-decay (WSD) schedule and its checkpoint-branching advantage.
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3) — reports the 6e-5 peak LR and 3.2M-token final batch size used at 175B scale.
