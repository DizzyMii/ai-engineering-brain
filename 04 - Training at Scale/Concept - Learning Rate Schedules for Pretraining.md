---
tags: [concept, domain/training-at-scale, level/core]
aliases: [LR schedule, WSD, warmup-stable-decay, trapezoidal schedule, cosine decay, cosine annealing, inverse-sqrt schedule]
summary: "The warmup-plus-decay shapes (cosine, WSD/trapezoidal, inverse-sqrt) that govern how the learning rate moves over an LLM pretraining run."
---

# Concept - Learning Rate Schedules for Pretraining

> **One-paragraph hook:** The peak learning rate gets all the attention in a config file, but the *shape* of the schedule around it — how fast you ramp up, how long you hold, how you decay — determines whether a multi-million-dollar run spikes in the first thousand steps or wastes its last 10% of compute at a rate too high to converge. The schedule is not a hyperparameter you tune once; it's a commitment that interacts with your token budget, your data plan, and whether you can even change your mind mid-run.

## The mechanism

Every LLM pretraining schedule has (at minimum) a **warmup** phase and a **decay** phase, and the differences between schedules are almost entirely about what happens between them.

**Warmup**: a linear ramp from ~0 to the peak learning rate over roughly **0.5-4% of total steps** (often around 2000 steps in absolute terms, regardless of total run length). This exists because [[Concept - AdamW at Scale|Adam's]] second-moment estimate $v$ starts at zero and is uncalibrated for the first many steps — the effective step size $\text{lr}/\sqrt{\hat v}$ can be enormous while $\hat v$ is still small and noisy, and combined with a poorly-conditioned early loss landscape this is enough to spike or destabilize a run that jumps straight to peak LR. Warmup too short reproduces exactly that early spike; warmup too long just burns steps at a suppressed learning rate.

**Cosine decay** anneals from peak down to roughly **10% of peak** over the *entire planned token budget*, following

$$\text{lr}(t) = \text{lr}_{\min} + \tfrac{1}{2}(\text{lr}_{\max}-\text{lr}_{\min})\left(1+\cos\!\left(\pi \frac{t - t_{\text{warmup}}}{T - t_{\text{warmup}}}\right)\right)$$

for $t$ between the end of warmup and the total step count $T$. The catch is baked into the formula: $T$ has to be known in advance, because the whole curve is shaped around hitting the target LR exactly at step $T$. Stop early and you're left at a *high* learning rate the schedule assumed you'd have long since decayed away from — the loss you see at that checkpoint is artificially inflated relative to what more decay would have bought you, and you cannot fix it without either continuing the original schedule or restarting a new one.

**Warmup-stable-decay** (WSD / trapezoidal — MiniCPM, Hu et al. 2024) sidesteps that commitment: warmup → a **long constant phase at peak LR** → a **short rapid decay** (typically the last 10-20% of steps). Because the stable phase holds a fixed LR with no reference to a final step count, a run can be checkpointed, extended, or branched at any point during the plateau without invalidating the schedule the way cutting a cosine run short does — you simply decide *later* how long to hold before triggering the decay tail. This flexibility is the entire point: teams have started using it to defer the token-budget decision, or to branch multiple decay runs off one shared stable checkpoint to try different anneal strategies.

**Inverse-sqrt** ($\text{lr}(t) = \text{lr}_{\max}\sqrt{t_{\text{warmup}}/t}$ for $t > t_{\text{warmup}}$) is the original Transformer schedule (Vaswani et al. 2017) and, like WSD, needs no fixed horizon — it just keeps decaying slowly forever, making it a natural fit for open-ended or continually-trained models rather than a run with a hard stop.

| Schedule | Shape | Needs total steps upfront? | Best fit |
|---|---|---|---|
| Cosine | warmup → smooth cosine decay to ~10% peak | yes | fixed-budget runs where $T$ is known and fixed |
| WSD / trapezoidal | warmup → long constant → rapid decay (last 10-20%) | no, until you trigger decay | extendable runs, checkpoint branching, deferred budget |
| Inverse-sqrt | warmup → $\propto 1/\sqrt{t}$ decay | no | open-ended or continually-trained runs |

The rapid-decay phase, in both cosine's tail and WSD's decay window, is where a disproportionate share of a model's final capability gets locked in — which is why **annealing on higher-quality or domain-specific data** during just that phase (pairing the LR schedule with a [[Concept - Data Mixtures|data schedule]]) has become standard practice rather than holding the data mixture constant throughout.

## In practice

Peak-LR magnitude scales inversely with model width — this is the empirical basis for [[Concept - muP and Hyperparameter Transfer|muP]], which lets you tune LR on a small proxy model and transfer it to a much larger one without a fresh sweep. Real numbers: **~3e-4** is a typical peak for mid-size dense models; GPT-3 175B ran an unusually low **6e-5** paired with a huge batch size. On the batch side, the [[Concept - Critical Batch Size|linear scaling rule]] holds for small batches, but Adam's effective scaling at large batch is closer to $\sqrt{\text{batch size}}$ — the peak LR has to track batch size or the extra samples per step buy you nothing (or push you unstable). See [[Reference - LLM Pretraining Hyperparameters]] for a fuller table of peak-LR / batch-size / warmup-length combinations by model scale, and [[Deep Dive - Anatomy of a Pretraining Run]] for where the schedule sits in the full run lifecycle from budget to release.

Practically, warmup length is measured in [[Concept - Gradient Accumulation and Microbatching|optimizer steps]], not microbatches or samples — a run with heavy gradient accumulation reaches "2000 steps" after far more wall-clock and far more tokens than one with none, so porting a warmup-step count between configs with different accumulation settings without adjusting for that is a common and easy-to-miss bug.

## Failure modes

- **LR too high past warmup** triggers spikes or outright divergence — the schedule's peak value is doing double duty as both "fast convergence" and "the edge of stability," and it's easy to set it past that edge for a given architecture/batch/precision combination. See [[Concept - Training Stability and Loss Spikes]] for the broader catalog of what a spike looks like and how to recover from it.
- **Decaying fully to 0 vs. to ~10% of peak.** A schedule that anneals all the way to zero looks "more converged," but leaves nothing for continued training to build on — resuming from a near-zero-LR checkpoint starts the next phase cold, whereas stopping at ~10% preserves enough gradient signal that continued pretraining or annealing phases pick up smoothly. 10% is the more common choice for exactly this reason.
- **Resuming a cosine run with the wrong remaining-steps count.** Because the cosine formula's shape depends on $T$, restarting from a checkpoint with a mis-recorded step count or a changed target token budget silently re-derives a *different* curve for the rest of training — the LR decays too fast or too slow relative to what the original plan intended, and nothing errors out; the run just quietly under- or over-trains relative to its budget.

## The non-obvious

WSD's real advantage isn't a better final loss — in practice it lands close to cosine's. The advantage is *optionality*: cosine's schedule bakes a token-budget commitment into every future step from the moment training starts, so changing your mind about how long to train means either wasting compute (stopping early at an artificially high LR) or accepting a discontinuity (splicing schedules). WSD's stable phase defers that commitment until you actually trigger the decay tail, which is why teams have started using the plateau as a fork point — checkpoint once during the stable phase, then run several short decay branches with different anneal-data mixtures to see which one lands best before committing a full run to any one of them (folklore, weakly sourced: this branching pattern is reported informally by teams using WSD-style schedules but isn't something with a single canonical published ablation).

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
