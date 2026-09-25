---
tags: [playbook, domain/training-at-scale, level/unicorn]
aliases: [debugging divergence, loss spike triage, NaN in training, spike recovery procedure]
summary: "On-call procedure for a pretraining run that spikes, diverges, or NaNs: triage the signature, isolate the cause, then recover or restart."
---

# Playbook - Debugging a Diverging Training Run

> **Goal:** get a live run whose loss just spiked, drifted, or NaN'd back onto its pre-event trajectory with minimum wasted cluster time, or make a clean kill/relaunch call.
> **When to run this:** the grad-norm alarm fires, the loss goes vertical, or a `NaN`/`Inf` shows up in the loss on a run costing four-to-six figures per hour. Pre-launch config bugs belong in [[Checklist - Pre-Launch for a Large Training Run]].
> **Prerequisites:** recent loadable checkpoints ([[Concept - Distributed Checkpointing]]), per-step logs of loss, global grad-norm, LR and per-rank health, and a way to reproduce a step from a checkpoint deterministically.

Theory for every branch: [[Concept - Training Stability and Loss Spikes]]. This is the operational sequence. Go in order: each step is cheap and rules out a class of cause before the expensive ones.

## Steps

**1. Classify the signature before touching anything.** Pull grad-norm, loss and per-rank health for the last few hundred steps. There are three shapes:
- **Sharp spike.** Grad-norm jumps 10–100× over a handful of steps; loss follows a few steps behind. Suspect optimizer or data.
- **Slow drift.** Loss slides off a reference curve over thousands of steps, no single jump. Suspect numerics (bf16 accumulation).
- **Hard NaN at one specific step**, no grad-norm ramp. Suspect hardware or a single bad tensor.

If it's ambiguous (a spike *and* a NaN, say), chase the more localized cause first: hardware. Calling an ECC fault an optimizer spike wastes a rewind.

**2. Isolate data.** From a clean pre-event checkpoint, replay the exact batches around the event with the same seed and dataloader position. If the divergence reproduces, check those batches for repeated tokens, a garbage or near-empty document, an encoding/decoding artifact, or a packing bug that let attention bleed across concatenated docs.

If it doesn't reproduce, you're in the PaLM case: the same data trained fine on a second pass. That's an optimizer-state × data interaction. The data isn't bad on its own and cleaning it won't fix anything. Stop hunting the batch and go to Step 5.

**3. Separate hardware from numerics.** Read the **per-rank pre-reduce** gradient norms; the post-all-reduce global norm hides the origin. One anomalous rank points at that GPU. ECC errors or silent data corruption on one device poison every rank after the all-reduce, but start locally (see [[Lore - Silent Data Corruption at Scale]], and [[Playbook - Debugging a Hung Distributed Training Job]] for the sibling failure). All ranks moving together points at optimization.

While you're there, check the numerics invariants. Gradient and all-reduce accumulation must be **fp32**; a bf16 reduce loses precision at scale and causes slow drift ([[Concept - Mixed Precision Training]]; the numeric-conditioning pitfalls are in [[Gotchas - Numerical Stability]]). Layernorm, softmax and loss run in fp32, not bf16. A broken invariant *is* your Step-1 slow drift.

**4. Recover.** Take the least invasive action that fits, then resume:
- Rewind to the last checkpoint **before** the event. Loss should resume at its pre-event value.
- Skip the offending N batches. PaLM's blanket tactic: restart ~100 steps back, skip ~200–500 batches spanning the culprit. The loss should rejoin its old trajectory within tens of steps and not re-spike at the same token position.
- Lower the LR temporarily (e.g. ×0.5) for a short re-ramp, and/or tighten global-norm clipping from 1.0 toward 0.5–0.3. Grad-norm should stay bounded through the region that blew up.
- If the run had them off, turn on the standing stabilizers: z-loss on the output softmax and QK-norm on attention ([[Concept - z-loss and Logit Soft-Capping]]). Attention and output logit magnitudes should stop growing.

**5. If it spikes again, change the run.** A re-spike after a clean recovery means stop babysitting. Lower the *peak* LR. Drop $\beta_2$ from 0.999 toward 0.95 so Adam's second-moment estimate tracks variance faster ([[Concept - AdamW at Scale]]). Add the stabilizers if they're missing. Move sensitive layers (embeddings, output head, first/last blocks) from fp8 up to bf16. The goal is killing the recurrence.

Kill vs. babysit is a cost call. Intervening by hand more than ~once every few hours? Relaunching with better hyperparameters is cheaper.

## Verification

It worked when the loss **rejoins its pre-event trajectory within M steps** (typically tens to low hundreds), global grad-norm is back in its old baseline band, *and* the offending token position passes on the resumed run without re-spiking.

If the NaN stops but the loss sits on a permanently higher curve, it isn't fixed. The model took damage before the rewind; use an earlier checkpoint.

## When it goes wrong

| Symptom | Likely cause | Fix / jump to |
|---|---|---|
| Sharp grad-norm spike, all ranks together, reproduces from checkpoint | Corrupted/repeated data batch | Step 2 → skip batches; inspect shard |
| Sharp spike, does **not** reproduce | Optimizer-state × data interaction (PaLM) | Step 4 skip + Step 5 lower $\beta_2$/LR |
| Slow divergence from reference over 10k+ steps | bf16 reduce dtype, or layernorm in bf16 | Step 3 → set fp32 reduce & fp32 norm |
| Hard NaN at one step, one anomalous rank | GPU ECC / silent data corruption | Isolate & drain the node; see [[Lore - Silent Data Corruption at Scale]] |
| Spike right after warmup ends | Peak LR too high for phase | Step 5 → lower peak LR ([[Concept - Learning Rate Schedules for Pretraining]]) |
| One MoE expert's grad dominates | Router imbalance / expert collapse | [[Concept - MoE Training and Load Balancing]]; add router z-loss |
| Job hangs instead of diverging | Collective mismatch, not a spike | Different failure; see [[Gotchas - Distributed Training]] |

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
