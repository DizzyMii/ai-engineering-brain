---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [loss spikes, training instability, spike recovery, gradient blowup]
summary: "Why LLM pretraining loss suddenly explodes, the stabilizers that prevent it, and the rewind-skip-lower-LR recipe that recovers a run."
---

# Concept - Training Stability and Loss Spikes

> **One-paragraph hook:** Somewhere between step 10,000 and step 200,000 of a nine-figure training run, the gradient norm that's been oscillating calmly around 1.0 jumps to 40. The loss, sliding down a smooth curve until now, snaps vertical, and someone on call has a few minutes to decide whether the run self-heals, needs a rewind, or is quietly dying. Every frontier pretraining run (GPT-3, OPT-175B, PaLM, GLM-130B) has documented spikes. Whether a lab ships on schedule or burns a week of cluster time comes down to having instrumentation and a playbook ready before the first one.

## The mechanism

Spikes look the same across labs. The gradient norm (tracked as a scalar per step) grows 10-100x over a handful of steps, the loss follows a few steps later, and the run either damps back to baseline on its own within tens of steps or diverges outright if nothing intervenes. The leading indicators, in the order they usually appear:

- attention-logit growth (the pre-softmax $QK^\top/\sqrt{d}$ scores drift to larger magnitudes);
- layernorm-gain growth (the learned scale parameters in [[Concept - RMSNorm and LayerNorm]] creep upward and amplify everything downstream);
- less often but more insidiously, a single anomalous data batch that produces an unusually large loss and gradient.

The underlying failure is almost always **attention entropy collapse**. As logits grow, the softmax saturates toward near-one-hot, its gradient approaches a delta function, and a delta-function gradient backpropagated through dozens of layers produces a large, correlated update that blows up the global gradient norm. Two systemic factors compound it. bf16's coarse 7-bit mantissa (see [[Concept - Mixed Precision Training]]) lets small per-layer rounding errors accumulate across depth uncorrected. And Adam's second-moment estimate, the denominator that normalizes each parameter's update, lags a sudden jump in gradient magnitude by a few steps, so for that window the update is under-normalized and the spike gets amplified instead of damped.

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

Each known stabilizer targets one link in this chain.

- **QK-norm** (Dehghani et al. 2023, ViT-22B; also adopted in OLMo-2) applies [[Concept - RMSNorm and LayerNorm]]-style normalization to Q and K *before* the dot product. That caps attention-logit growth regardless of what the rest of the network does, so it goes at the root cause.
- **Z-loss** (used in PaLM) adds an auxiliary term $z\_loss = 10^{-4} \cdot \log^2 Z$, where $Z$ is the softmax normalizer of the output logits. It discourages the final softmax from operating where $\log Z$ drifts far from zero; [[Concept - z-loss and Logit Soft-Capping]] covers the mechanism in depth.
- **Embedding-gradient control**: GLM-130B shrinks the gradient flowing into the embedding layer by a fixed factor. This prevents unbounded embedding-norm growth, which would otherwise push instability into every layer that reads the residual stream.
- **Lower beta2**: 0.95 instead of Adam's default 0.999, standard practice per [[Concept - AdamW at Scale]]. The second-moment estimate then tracks sudden variance changes faster, shortening the window where a growing gradient is under-normalized.
- **Tighter global-norm gradient clipping**, dropping from 1.0 toward 0.5-0.3 during a rough patch, bounds the damage of any single bad step before the root cause is found.

## In practice

When a spike appears, check the five root-cause buckets in this order. (1) A specific corrupted or repeated data batch: the single most common cause and the most fixable. (2) LR too high for the current phase, typically right after warmup ends (see [[Concept - Learning Rate Schedules for Pretraining]]). (3) Dead or exploding experts in an MoE model, where routing has become imbalanced and one expert's gradient dominates (see [[Concept - MoE Training and Load Balancing]]). (4) bf16 precision drift, which accumulates slowly instead of spiking sharply. (5) A hardware fault (ECC error, a single bad GPU emitting NaN/Inf) that looks like an optimization spike but is a rank-local corruption.

OPT-175B, PaLM and GLM-130B all used the same recovery playbook ([[Lore - The OPT-175B Logbook]] has the war story): rewind to the last checkpoint before the spike (see [[Concept - Distributed Checkpointing]]), identify or blanket-skip the suspicious data batches, optionally lower the LR for a short re-ramp, and resume. The PaLM paper (Chowdhery et al., 2022) documents ~20 loss spikes over the run and a pragmatic variant. The team didn't root-cause each spike. They restarted from a checkpoint roughly 100 steps before it, skipped roughly 200-500 data batches spanning the suspected culprit, and resumed. That fixed essentially all of them, and they never confirmed the exact cause of most.

## Failure modes

- **Sharp optimizer/data spike vs. slow bf16 divergence.** A true spike shows in the raw loss and grad-norm curve within a handful of steps. bf16 drift is different: the loss tracks a bf16-vs-fp32 reference run correctly for tens of thousands of steps, then diverges gradually, almost imperceptibly. Loss lags the underlying drift, so catching it means watching auxiliary signals like activation norms and logit magnitudes.
- **Hardware fault masquerading as an optimization spike.** One GPU with a silent ECC error or a NaN-producing kernel corrupts its rank's gradient. After the all-reduce that corruption poisons the global gradient on every rank, and the aggregate loss curve looks identical to a real optimization spike. Locality gives it away. Check per-rank pre-reduce gradient norms: a hardware fault shows one anomalous rank, an optimization spike shows all ranks moving together.
- **Over-clipping hides a real data problem.** Cranking clipping down until every visible spike disappears stops the symptom and leaves the cause. If the issue is a corrupted or duplicated data shard, the model still trains on garbage every time that shard recurs, clipped or not. Since the dashboard looks clean, nobody ever excludes the shard.

## The non-obvious

A decade of spike post-mortems says you almost never need to know *why* a spike happened to fix it. Rewind-skip-resume works whether the cause was a bad batch, a transient LR mismatch or an unlucky initialization of a routing decision. Demanding a confirmed root cause before resuming a run that burns tens of thousands of dollars per hour is usually the wrong tradeoff. The catch: because skip-batch recovery works so reliably without diagnosis, teams that never build instrumentation to tell a data-caused spike from an LR-caused one keep re-triggering the same problem on the next run. The data or hyperparameter issue was masked, never fixed.

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
