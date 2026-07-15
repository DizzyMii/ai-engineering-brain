---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [loss spikes, training instability, spike recovery, gradient blowup]
summary: "Why LLM pretraining loss suddenly explodes, the stabilizers that prevent it, and the rewind-skip-lower-LR recipe that recovers a run."
---

# Concept - Training Stability and Loss Spikes

> **One-paragraph hook:** Somewhere between step 10,000 and step 200,000 of a nine-figure training run, the gradient norm that has been calmly oscillating around 1.0 jumps to 40, the loss that has been sliding down a smooth curve snaps vertical, and someone on call has to decide in the next few minutes whether the run self-heals, needs a rewind, or is quietly dying. Every frontier pretraining run — GPT-3, OPT-175B, PaLM, GLM-130B — has documented spikes; the difference between a lab that ships on schedule and one that burns a week of cluster time is whether they have instrumentation and a playbook ready before the first one happens.

## The mechanism

A spike's anatomy is consistent across labs: the gradient norm (tracked as a scalar per step) grows by 10-100x over a handful of steps, the loss follows with a delay of a few steps, and the run either damps back to baseline on its own within tens of steps or diverges outright if nothing intervenes. The leading indicators, in the order they usually show up, are attention-logit growth (the pre-softmax $QK^\top/\sqrt{d}$ scores drift to larger magnitudes), layernorm-gain growth (the learned scale parameters in [[Concept - RMSNorm and LayerNorm]] creep upward, amplifying everything downstream), and — less often but more insidiously — a single anomalous data batch that happens to produce an unusually large loss and gradient.

The underlying failure is almost always **attention entropy collapse**: as logits grow, the softmax saturates toward a near-one-hot distribution, its gradient becomes close to a delta function, and a delta-function gradient backpropagated through dozens of layers produces exactly the kind of large, correlated update that blows up the global gradient norm. This compounds with two systemic factors: bf16's coarse 7-bit mantissa (see [[Concept - Mixed Precision Training]]) lets small per-layer rounding errors accumulate across depth without correction, and Adam's second-moment estimate (the denominator that normalizes each parameter's update) lags behind a sudden gradient-magnitude jump for a few steps, briefly under-normalizing the update and amplifying the spike rather than damping it.

```
loss
 |                              spike
 |                                /\
 |                               /  \___ self-recovers
 |  smooth descent   __________/       \____
 |  \_______________/                       \  or: diverges ->
 |                                            \
 +------------------------------------------------------> step
```

The known stabilizers each target one link in this chain. **QK-norm** (Dehghani et al. 2023, ViT-22B; also adopted in OLMo-2) applies [[Concept - RMSNorm and LayerNorm]]-style normalization to Q and K *before* the dot product, capping how large attention logits can grow regardless of what the rest of the network does — it treats the root cause directly. **Z-loss** (used in PaLM) adds an auxiliary term $z\_loss = 10^{-4} \cdot \log^2 Z$ where $Z$ is the softmax normalizer of the output logits, discouraging the final softmax from operating in a regime where $\log Z$ drifts far from zero — see [[Concept - z-loss and Logit Soft-Capping]] for the mechanism in depth. **Embedding-gradient control** (GLM-130B shrinks the gradient flowing into the embedding layer by a fixed factor) prevents unbounded embedding-norm growth, which otherwise propagates instability into every layer that reads from the residual stream. **Lower beta2** (0.95 instead of Adam's default 0.999, standard practice per [[Concept - AdamW at Scale]]) makes the second-moment estimate track sudden variance changes faster, shortening the window where the optimizer under-normalizes a growing gradient. **Tighter global-norm gradient clipping** (dropping from 1.0 toward 0.5-0.3 during a rough patch) bounds the damage of any single bad step without waiting for the root cause to be found.

## In practice

Root causes cluster into five buckets you should check in this order when a spike appears: (1) a specific corrupted or repeated data batch — the single most common and most fixable cause; (2) LR too high for the current phase, typically right after warmup ends (see [[Concept - Learning Rate Schedules for Pretraining]]); (3) dead or exploding experts in an MoE model, where one expert's gradient dominates because routing has become imbalanced (see [[Concept - MoE Training and Load Balancing]]); (4) bf16 precision drift accumulating slowly rather than spiking sharply; (5) a hardware fault (ECC error, a single bad GPU emitting NaN/Inf) that looks like an optimization spike but is actually a rank-local corruption.

The recovery playbook used across OPT-175B, PaLM, and GLM-130B (see [[Lore - The OPT-175B Logbook]] for the war story) is: rewind to the last checkpoint before the spike (see [[Concept - Distributed Checkpointing]]), identify or blanket-skip the suspicious data batches, optionally lower the LR for a short re-ramp, and resume. Chowdhery et al. (2022), the PaLM paper, documents ~20 loss spikes over the training run and describes a pragmatic variant: rather than root-causing each spike individually, they restarted from a checkpoint roughly 100 steps before the spike and skipped roughly 200-500 data batches spanning the suspected culprit, then resumed — a strategy that fixed essentially all of them without ever confirming the exact cause of most.

## Failure modes

- **Sharp optimizer/data spike vs. slow bf16 divergence**: a true spike is visible in the raw loss and grad-norm curve within a handful of steps; bf16 drift instead shows as a loss curve that tracks a bf16-vs-fp32 reference run correctly for tens of thousands of steps and then gradually, almost imperceptibly, diverges — catching it requires watching auxiliary signals (activation norms, logit magnitudes) rather than loss alone, since loss lags the underlying drift.
- **Hardware fault masquerading as an optimization spike**: a single GPU with a silent ECC error or a NaN-producing kernel corrupts one rank's gradient, and after an all-reduce that corruption poisons the global gradient for every rank, looking identical to a genuine optimization spike in the aggregate loss curve. The distinguishing signal is locality: check per-rank pre-reduce gradient norms — a hardware fault shows one anomalous rank, an optimization spike shows all ranks moving together.
- **Over-clipping hides a real data problem**: cranking gradient clipping down to suppress every visible spike stops the symptom but not the cause — if the underlying issue is a corrupted or duplicated data shard, the model is still training on garbage every time that shard recurs, clipped or not, and the fix (excluding the shard) never happens because the dashboard looks clean.

## The non-obvious

The deepest lesson from a decade of spike post-mortems is that you almost never need to know *why* a spike happened to fix it — the rewind-skip-resume recipe works whether the cause was a bad batch, a transient LR mismatch, or an unlucky initialization of a routing decision, and demanding a confirmed root cause before resuming a run burning tens of thousands of dollars per hour is usually the wrong tradeoff. The corollary that catches people out: because skip-batches recovery works so reliably without diagnosis, teams that never bother building the instrumentation to distinguish a data-caused spike from an LR-caused one end up repeatedly re-triggering the same problem on the next run, because the underlying data or hyperparameter issue was masked, not fixed.

## Connections
- [[Concept - z-loss and Logit Soft-Capping]] — the specific auxiliary-loss mechanism (used by PaLM) that bounds output-softmax growth, one of the direct stabilizers described here.
- [[Lore - The Loss Spike Chronicles]] — the narrative war-stories version of the same failure mode across multiple frontier labs.
- [[Concept - Mixed Precision Training]] — bf16's coarse mantissa is one of the two systemic factors (alongside attention entropy collapse) that make spikes more frequent at scale.
- [[Concept - AdamW at Scale]] — the beta2=0.95 convention and global-norm clipping are levers owned by this note and pulled directly to reduce spike sensitivity.
- [[Concept - RMSNorm and LayerNorm]] — QK-norm is a direct application of this normalization primitive to the attention logits, the most effective single stabilizer known.
- [[Playbook - Debugging a Diverging Training Run]] — the operational, step-by-step version of the rewind-skip-lower-LR recovery sketched here.
- [[Concept - MoE Training and Load Balancing]] — dead/exploding experts are one of the five root-cause buckets, specific to MoE models.
- [[Lore - The OPT-175B Logbook]] — the original public record of a frontier lab fighting loss spikes in real time, including manual interventions.
- [[Concept - Distributed Checkpointing]] — the rewind step of the recovery playbook depends entirely on having a recent, loadable checkpoint before the spike.
- [[Concept - Learning Rate Schedules for Pretraining]] — LR-too-high-after-warmup is one of the five root-cause buckets, and the schedule shape itself is owned by this note.

## Sources
- Chowdhery et al. (2022) — "PaLM: Scaling Language Modeling with Pathways" — documents ~20 loss spikes, the z-loss auxiliary term, and the restart-100-steps-back / skip-200-500-batches recovery recipe.
- Dehghani et al. (2023) — "Scaling Vision Transformers to 22 Billion Parameters" — introduces QK-layernorm to prevent attention-logit blowup at scale, later adopted in language models (e.g., OLMo-2).
- Zeng et al. (2022) — "GLM-130B: An Open Bilingual Pre-trained Model" — documents embedding-gradient-shrink and other stabilization tricks used to keep a 130B run from diverging.
