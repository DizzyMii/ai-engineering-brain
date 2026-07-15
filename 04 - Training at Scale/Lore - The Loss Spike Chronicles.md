---
tags: [lore, domain/training-at-scale, level/unicorn]
aliases: [loss spikes, loss spike war stories]
summary: "War stories of pretraining loss spikes—OPT-175B, PaLM, GLM-130B, BLOOM—and the restart-skip-lower-LR folklore they produced."
---

# Lore - The Loss Spike Chronicles

## What happened

Every stabilizer in a modern pretraining recipe — qk-norm, z-loss, beta2=0.95, tight gradient clipping, bf16 over fp16 — is scar tissue. It was added because a specific large run at a specific lab went off the rails and someone spent a bad week figuring out why. The 2022 cohort of publicly documented runs is where most of that folklore was minted.

**OPT-175B (Meta, Zhang et al. 2022)** published its training logbook, and it remains the most honest document in the field. Over ~2 months on 992 A100s the team fought a continuous war: hardware node failures, spontaneous loss divergences, and repeated fp16 **loss-scale collapse** — the dynamic loss scaler driven toward zero by recurring overflow, at which point learning stalls (the mechanism lives in [[Lore - Loss Scaling and the fp16 Underflow Crisis]]). Their tactic was manual and unglamorous: watch the loss, and when it diverged, roll back to an earlier checkpoint, lower the learning rate, and resume — sometimes many times. The logbook reads like a submarine damage-control log, and that was the point of publishing it.

**PaLM (Google, Chowdhery et al. 2022)** documented roughly **20 loss spikes** across its 540B run and made the sharpest observation in the genre: *there was no single bad batch.* When they rewound to a checkpoint before a spike and **re-ran the exact same data, the spike did not recur** — yet skipping the ~200–500 batches around the spike location and continuing did. Same data, different outcome. Their recipe became canonical: restart from a checkpoint ~100 steps before the spike and skip the batches it passed through. Because the data was not intrinsically toxic, the spike had to be an interaction between a particular *optimizer state* and a particular data ordering, not a property of the data alone.

**GLM-130B (Tsinghua/Zhipu, Zeng et al. 2022)** localized its instability more mechanistically. It attributed spikes to **embedding-layer gradient growth** and attention-softmax logits blowing up, and fixed them with **embedding-gradient shrink** (scale down the embedding gradient) and DeepNorm for the residual path. GLM-130B is also the run that documented fp16-vs-bf16 pain on **non-NVIDIA hardware** (it trained across multiple platforms), which sharpened the field's understanding that precision behavior is hardware-specific, not universal.

**BLOOM (BigScience, 2022)** and the broader Megatron-DeepSpeed community turned these episodes into a default. BLOOM trained in **bf16 specifically to escape the fp16 loss-scale collapse** OPT had fought, trading fp16's precision for bf16's dynamic range. The "restart, skip the batch, lower the LR" recipe entered common practice, and qk-layernorm and z-loss became standard architectural insurance rather than exotic tricks — see [[Concept - z-loss and Logit Soft-Capping]] and the broader mechanism note [[Concept - Training Stability and Loss Spikes]].

There is a fifth actor that hides in every one of these logs: **the machine itself.** A single-rank NaN that looks like an optimization spike is often an ECC error or [[Lore - Silent Data Corruption at Scale|silent data corruption]] on one GPU. Distinguishing "the optimizer diverged everywhere" from "one bad card poisoned the all-reduce" is the first fork of any real debugging session, and getting it wrong sends you tuning hyperparameters when you should be draining a node.

## The lesson

Mechanically, a loss spike is the moment **AdamW's second-moment estimate `v` goes stale relative to a sudden shift in the gradient direction.** Adam normalizes each update by `sqrt(v)`; when a batch pushes the gradient into a direction whose curvature `v` has not yet caught up to, the effective step in that direction is enormous, activations and logits saturate, the softmax gradient vanishes or `exp` overflows in bf16, and the loss jumps. Whether it self-heals or diverges depends on how much of the network got knocked off the manifold.

That single mechanism explains why the folklore fixes are the fixes, each attacking a different term:

- **Lower `beta2` (0.999 → 0.95)** — let `v` track the variance faster so it is less often stale. This is why [[Concept - AdamW at Scale|AdamW at scale]] uses 0.95 almost universally.
- **Gradient clipping (global norm ~1.0)** — bound the worst-case step so a stale-`v` direction cannot produce an unbounded update.
- **Longer warmup** — do not trust `v` while it is still uncalibrated in the first thousands of steps.
- **Skip the batch on restart** — change the *ordering* so the optimizer state meets that data in a different, benign configuration (the PaLM result).
- **qk-norm / z-loss** — cap the attention and output logits structurally so the saturation half of the failure cannot happen (adopted after these runs specifically).
- **bf16 over fp16** — remove the loss-scale-collapse failure mode entirely by trading mantissa for range ([[Concept - Mixed Precision Training]]).

The operational drill these runs bequeathed — triage, isolate data vs optimizer vs hardware, recover or restart — is written up as [[Playbook - Debugging a Diverging Training Run]]. The deep point: none of this is theory. The stabilizer stack is a list of past disasters, and every item on it has a name and a date.

## Evidence status

- **OPT-175B logbook: verified/published.** Meta released the actual chronological notes; the fuller history is catalogued in [[Lore - The OPT-175B Logbook]].
- **PaLM's ~20 spikes and the skip-batches finding: well-sourced**, stated directly in Chowdhery et al. (2022).
- **GLM-130B's embedding-gradient-shrink and DeepNorm fixes: well-sourced** from Zeng et al. (2022).
- **BLOOM's bf16 choice: well-documented** from the BigScience engineering write-ups.
- **The "restart / skip / lower LR" recipe as universal practice: well-sourced practitioner folklore** — consistently reported, rarely written as a formal result.
- **The stale-`v` mechanistic story: a well-supported model**, consistent with the Adam update rule and the observed correlates (logit/embedding-norm growth), but "the second moment went stale" is an interpretive frame, not a measured quantity in these papers.

## Connections

- [[Concept - Training Stability and Loss Spikes]] — the mechanism note these war stories are the evidence for; read it for the qk-norm/z-loss/precision details.
- [[Lore - The OPT-175B Logbook]] — the primary-source history whose spike-and-recover tactics this note extracts and generalizes.
- [[Concept - Mixed Precision Training]] — the fp16 loss-scale collapse that OPT fought and BLOOM designed around by moving to bf16.
- [[Concept - AdamW at Scale]] — the `beta2=0.95` / clipping choices are the direct descendants of these spikes.
- [[Concept - z-loss and Logit Soft-Capping]] — the output-logit stabilizers that became standard because of the softmax-blowup episodes.
- [[Playbook - Debugging a Diverging Training Run]] — the operational drill distilled from all four runs.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the numerics behind the loss-scale-collapse battles central to the OPT story.
- [[Lore - Silent Data Corruption at Scale]] — the hardware-fault case a single-rank NaN can masquerade as, the first fork in any spike triage.
