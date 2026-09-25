---
tags: [lore, domain/training-at-scale, level/unicorn]
aliases: [loss spikes, loss spike war stories]
summary: "War stories of pretraining loss spikes—OPT-175B, PaLM, GLM-130B, BLOOM—and the restart-skip-lower-LR folklore they produced."
---

# Lore - The Loss Spike Chronicles

## What happened

Every stabilizer in a modern pretraining recipe is scar tissue: qk-norm, z-loss, beta2=0.95, tight gradient clipping, bf16 over fp16. Each was added because a specific large run at a specific lab went off the rails and someone spent a bad week working out why. Most of that folklore was minted by the 2022 cohort of publicly documented runs.

**OPT-175B (Meta, Zhang et al. 2022)** published its training logbook, and it's still the most honest document in the field. Over ~2 months on 992 A100s the team fought a continuous war: hardware node failures, spontaneous loss divergences, and repeated fp16 **loss-scale collapse**, where recurring overflow drives the dynamic loss scaler toward zero and learning stalls (mechanism in [[Lore - Loss Scaling and the fp16 Underflow Crisis]]). Their tactic was manual and unglamorous. Watch the loss; when it diverged, roll back to an earlier checkpoint, lower the learning rate, resume. Sometimes many times over. The logbook reads like a submarine damage-control log, which was the point of publishing it.

**PaLM (Google, Chowdhery et al. 2022)** documented roughly **20 loss spikes** across its 540B run and made the sharpest observation in the genre: *there was no single bad batch.* When they rewound to a checkpoint before a spike and **re-ran the exact same data, the spike did not recur**. Skipping the ~200–500 batches around the spike location and continuing did work. Same data, different outcome. Their recipe became canonical: restart from a checkpoint ~100 steps before the spike and skip the batches it passed through. Since the data wasn't intrinsically toxic, the spike had to come from an interaction between a particular *optimizer state* and a particular data ordering.

**GLM-130B (Tsinghua/Zhipu, Zeng et al. 2022)** pinned its instability down more mechanistically. It blamed spikes on **embedding-layer gradient growth** and attention-softmax logits blowing up, and fixed them with **embedding-gradient shrink** (scaling down the embedding gradient) plus DeepNorm on the residual path. GLM-130B also documented fp16-vs-bf16 pain on **non-NVIDIA hardware** (it trained across multiple platforms), which taught the field that precision behavior depends on the hardware.

**BLOOM (BigScience, 2022)** and the wider Megatron-DeepSpeed community turned these episodes into defaults. BLOOM trained in **bf16 specifically to escape the fp16 loss-scale collapse** OPT had fought, giving up fp16's precision for bf16's dynamic range. "Restart, skip the batch, lower the LR" entered common practice, and qk-layernorm and z-loss went from exotic tricks to standard architectural insurance. See [[Concept - z-loss and Logit Soft-Capping]] and the broader mechanism note [[Concept - Training Stability and Loss Spikes]].

A fifth actor hides in every one of these logs: **the machine itself.** A single-rank NaN that looks like an optimization spike is often an ECC error or [[Lore - Silent Data Corruption at Scale|silent data corruption]] on one GPU. The first fork of any real debugging session is telling "the optimizer diverged everywhere" apart from "one bad card poisoned the all-reduce." Get it wrong and you're tuning hyperparameters when you should be draining a node.

## The lesson

Mechanically, a loss spike is the moment **AdamW's second-moment estimate `v` goes stale relative to a sudden shift in the gradient direction.** Adam divides each update by `sqrt(v)`. When a batch pushes the gradient into a direction whose curvature `v` hasn't caught up with, the effective step in that direction is huge. Activations and logits saturate, the softmax gradient vanishes or `exp` overflows in bf16, and the loss jumps. Whether it self-heals or diverges depends on how much of the network got knocked off the manifold.

That one mechanism explains the folklore fixes. Each attacks a different term:

- **Lower `beta2` (0.999 → 0.95)** so `v` tracks the variance faster and goes stale less often. That's why [[Concept - AdamW at Scale|AdamW at scale]] uses 0.95 almost universally.
- **Gradient clipping (global norm ~1.0)** bounds the worst-case step, so a stale-`v` direction can't produce an unbounded update.
- **Longer warmup**: don't trust `v` while it's still uncalibrated in the first thousands of steps.
- **Skip the batch on restart** to change the *ordering*, so the optimizer state meets that data in a different, benign configuration (the PaLM result).
- **qk-norm / z-loss** cap the attention and output logits architecturally, so the saturation half of the failure can't happen (adopted specifically after these runs).
- **bf16 over fp16** removes loss-scale collapse entirely by trading mantissa for range ([[Concept - Mixed Precision Training]]).

The operational drill these runs left behind (triage, isolate data vs optimizer vs hardware, recover or restart) is written up as [[Playbook - Debugging a Diverging Training Run]]. None of this is theory. The stabilizer stack is a list of past disasters, and every item on it has a name and a date.

## Evidence status

- **OPT-175B logbook: verified/published.** Meta released the actual chronological notes; the fuller history is catalogued in [[Lore - The OPT-175B Logbook]].
- **PaLM's ~20 spikes and the skip-batches finding: well-sourced**, stated directly in Chowdhery et al. (2022).
- **GLM-130B's embedding-gradient-shrink and DeepNorm fixes: well-sourced** from Zeng et al. (2022).
- **BLOOM's bf16 choice: well-documented** in the BigScience engineering write-ups.
- **The "restart / skip / lower LR" recipe as universal practice: well-sourced practitioner folklore.** Consistently reported, rarely written up as a formal result.
- **The stale-`v` mechanistic story: a well-supported model.** It's consistent with the Adam update rule and the observed correlates (logit/embedding-norm growth), but "the second moment went stale" is an interpretive frame. These papers don't measure it.

## Connections

- [[Concept - Training Stability and Loss Spikes]] — the mechanism note these war stories are the evidence for; read it for the qk-norm/z-loss/precision details.
- [[Lore - The OPT-175B Logbook]] — the primary-source history whose spike-and-recover tactics this note extracts and generalizes.
- [[Concept - Mixed Precision Training]] — the fp16 loss-scale collapse that OPT fought and BLOOM designed around by moving to bf16.
- [[Concept - AdamW at Scale]] — the `beta2=0.95` / clipping choices are the direct descendants of these spikes.
- [[Concept - z-loss and Logit Soft-Capping]] — the output-logit stabilizers that became standard because of the softmax-blowup episodes.
- [[Playbook - Debugging a Diverging Training Run]] — the operational drill distilled from all four runs.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the numerics behind the loss-scale-collapse battles central to the OPT story.
- [[Lore - Silent Data Corruption at Scale]] — the hardware-fault case a single-rank NaN can masquerade as, the first fork in any spike triage.
