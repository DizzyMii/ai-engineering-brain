---
tags: [playbook, domain/training-at-scale, level/unicorn]
aliases: [debugging divergence, loss spike triage, NaN in training, spike recovery procedure]
summary: "On-call procedure for a pretraining run that spikes, diverges, or NaNs: triage the signature, isolate the cause, then recover or restart."
---

# Playbook - Debugging a Diverging Training Run

> **Goal:** get a live run whose loss just spiked, drifted, or NaN'd back onto its pre-event trajectory with minimum wasted cluster time — or make a clean kill/relaunch decision.
> **When to run this:** the grad-norm alarm fires, the loss snaps vertical, or a `NaN`/`Inf` appears in the loss on a run costing four-to-six figures per hour. Not for pre-launch config bugs — that is [[Checklist - Pre-Launch for a Large Training Run]].
> **Prerequisites:** recent loadable checkpoints ([[Concept - Distributed Checkpointing]]), per-step logs of loss, global grad-norm, LR, and per-rank health, and the ability to reproduce a step from a checkpoint deterministically.

The mechanism behind every branch here is [[Concept - Training Stability and Loss Spikes]]; this note is the operational sequence, not the theory. Work the steps in order — each is cheap and rules out a class of cause before the expensive ones.

## Steps

**1. Classify the signature before touching anything.** Pull up grad-norm, loss, and per-rank health for the last few hundred steps. → You will see one of three shapes: a **sharp spike** (grad-norm jumps 10–100× over a handful of steps, loss follows with a few-step lag) points at optimizer/data; a **slow drift** (loss quietly diverges from a reference curve over thousands of steps with no single jump) points at numerics/bf16 accumulation; a **hard NaN at a specific step** with no grad-norm ramp points at hardware or a single bad tensor. → If the three shapes are ambiguous (e.g. a spike *and* a NaN), treat it as the more localized cause first (hardware) — misclassifying an ECC fault as an optimizer spike wastes a rewind.

**2. Isolate data.** From a clean pre-event checkpoint, replay the exact batches spanning the event with the same seed and dataloader position. → If the divergence **reproduces**, inspect those batches for repeated tokens, a garbage/near-empty document, a decoding/encoding artifact, or a packing bug that bled attention across concatenated docs. If it **does not reproduce** — the PaLM finding, where the same data trained fine on a second pass — it is an optimizer-state × data *interaction*, not bad data per se, and no amount of data cleaning will fix it. → A non-reproducing spike is the signal to stop hunting the batch and move to a structural fix (Step 5).

**3. Isolate hardware vs numerics.** Read **per-rank pre-reduce** gradient norms, not just the post-all-reduce global norm. → A single anomalous rank implicates that GPU — an ECC error or silent data corruption on one device poisons every rank after the all-reduce, but the *origin* is local (cross-ref [[Lore - Silent Data Corruption at Scale]] and [[Playbook - Debugging a Hung Distributed Training Job]] for the sibling failure). All ranks moving together implicates optimization. → While here, confirm the numerics invariants: the gradient/all-reduce accumulation dtype is **fp32** (a bf16 reduce loses precision at scale and drives slow drift — see [[Concept - Mixed Precision Training]] and the numeric-conditioning pitfalls in [[Gotchas - Numerical Stability]]), and layernorm/softmax/loss run in fp32 not bf16. A violated invariant *is* the Step-1 slow-drift cause.

**4. Recover.** Apply the least-invasive action that fits the signature, then resume:
- Rewind to the last checkpoint **before** the event. → Expected: training resumes on the pre-event loss value.
- Skip the offending N batches (the blanket PaLM tactic: restart ~100 steps back, skip ~200–500 batches spanning the culprit). → Expected: the loss rejoins its old trajectory within tens of steps and does not re-spike at the same token position.
- Temporarily lower the LR (e.g. ×0.5) for a short re-ramp, and/or tighten global-norm clip from 1.0 toward 0.5–0.3. → Expected: grad-norm stays bounded through the previously-unstable region.
- Enable/keep on the standing stabilizers — z-loss on the output softmax and QK-norm on attention ([[Concept - z-loss and Logit Soft-Capping]]) — if the run had them off. → Expected: attention/output logit magnitudes stop growing.

**5. Escalate to a structural fix on repeat.** If the run re-spikes after a clean recovery, stop babysitting and change the run: lower the *peak* LR, drop $\beta_2$ from 0.999 toward 0.95 so Adam's second-moment estimate tracks variance faster ([[Concept - AdamW at Scale]]), add the stabilizers if absent, or move sensitive layers (embeddings, output head, first/last blocks) from fp8 up to bf16. → Expected: the structural change removes the recurrence, not just the instance. → Decide kill-vs-babysit by cost: if manual interventions are needed more than ~once per few hours, the relaunch with better hyperparameters is cheaper than the babysitting.

## Verification

The recovery worked when the loss **rejoins its pre-event trajectory within M steps** (typically tens to low hundreds) and the global grad-norm returns to its prior baseline band, *and* the previously-offending token position passes without re-spiking on the resumed run. A recovery that merely stops the NaN but leaves the loss on a permanently higher curve is not a fix — the model took damage before the rewind, and you need an earlier checkpoint.

## When it goes wrong

| Symptom | Likely cause | Fix / jump to |
|---|---|---|
| Sharp grad-norm spike, all ranks together, reproduces from checkpoint | Corrupted/repeated data batch | Step 2 → skip batches; inspect shard |
| Sharp spike, does **not** reproduce | Optimizer-state × data interaction (PaLM) | Step 4 skip + Step 5 lower $\beta_2$/LR |
| Slow divergence from reference over 10k+ steps | bf16 reduce dtype, or layernorm in bf16 | Step 3 → set fp32 reduce & fp32 norm |
| Hard NaN at one step, one anomalous rank | GPU ECC / silent data corruption | Isolate & drain the node; see [[Lore - Silent Data Corruption at Scale]] |
| Spike right after warmup ends | Peak LR too high for phase | Step 5 → lower peak LR ([[Concept - Learning Rate Schedules for Pretraining]]) |
| One MoE expert's grad dominates | Router imbalance / expert collapse | [[Concept - MoE Training and Load Balancing]]; add router z-loss |
| Job hangs rather than diverges | Collective mismatch, not a spike | This is a different failure — [[Gotchas - Distributed Training]] |

## Connections
- [[Concept - Training Stability and Loss Spikes]] — the mechanism (attention entropy collapse, stale second-moment, bf16 drift) behind every branch of this procedure.
- [[Lore - The Loss Spike Chronicles]] — the OPT-175B/PaLM/GLM-130B war stories this playbook distills into steps.
- [[Concept - Distributed Checkpointing]] — the rewind in Step 4 is only possible with a recent, loadable, fully-resumable checkpoint (RNG + dataloader state).
- [[Gotchas - Distributed Training]] — a *hang* is a distinct failure from a *divergence*; this table's last row points there so you don't run spike-recovery on an NCCL deadlock.
- [[Concept - Mixed Precision Training]] — the fp32-reduce and fp32-norm invariants checked in Step 3, and the bf16-drift signature in Step 1.
- [[Concept - AdamW at Scale]] — the $\beta_2$, LR, and grad-clip levers pulled in Steps 4–5 are owned there.
- [[Checklist - Pre-Launch for a Large Training Run]] — the pre-flight that prevents most of these; this playbook is its runtime counterpart.
- [[Concept - z-loss and Logit Soft-Capping]] — the specific output/attention-logit stabilizers enabled during recovery in Step 4.
- [[Playbook - Debugging a Hung Distributed Training Job]] — the sibling procedure for hangs/deadlocks, referenced when Step 3 finds a single-rank fault.
- [[Lore - Silent Data Corruption at Scale]] — why a single-rank NaN is a hardware story, and how SDC poisons all ranks post-all-reduce.
- [[Gotchas - Numerical Stability]] — the fp32-reduce / fp32-norm invariants of Step 3 are numeric-conditioning rules cataloged there.
- [[Concept - Learning Rate Schedules for Pretraining]] — the post-warmup-LR-too-high branch in the table, and the schedule shape you rewind within.
- [[Concept - MoE Training and Load Balancing]] — the expert-collapse branch: a dominant expert gradient is an MoE-specific divergence cause.

## Sources
- Chowdhery et al. (2022) — "PaLM: Scaling Language Modeling with Pathways" — the ~20-spike account and the restart-100-steps-back / skip-200–500-batches recovery, plus the non-reproducing-spike observation that anchors Step 2.
- Zhang et al. (2022) — "OPT: Open Pre-trained Transformer Language Models" — the logbook of real-time interventions (LR lowerings, clip tightening, hardware swaps) that this triage sequence generalizes.
- Zeng et al. (2022) — "GLM-130B: An Open Bilingual Pre-trained Model" — embedding-gradient-shrink and the numerics-vs-optimization distinction used in Step 3.
