---
tags: [checklist, domain/training-at-scale, level/advanced]
aliases: [pretraining launch checklist, pre-flight for training runs]
summary: "Pre-flight checks across config, numerics, data, checkpointing, and observability before committing thousands of GPU-hours to a run."
---

# Checklist - Pre-Launch for a Large Training Run

A launch mistake caught at step 0 costs minutes. Caught at step 50,000, it costs a rewind, a wasted week of GPU-hours and, if it was silent, a model you have to distrust and maybe discard. Run every item below before scaling a config from a debug run to the full cluster. The checklist assumes the run is already designed (see [[Deep Dive - Anatomy of a Pretraining Run]]). It verifies the launch, not the design.

## Config & sizing

- [ ] Token budget matches the intended compute-optimal or overtraining target ([[Concept - Scaling Laws]]). Total tokens, not total steps, was the quantity you decided on.
- [ ] Global batch size arithmetic checks out: `microbatch_size × grad_accum_steps × data_parallel_world_size` equals the intended token batch, not an off-by-one approximation.
- [ ] The LR schedule's total-step count matches the token budget exactly. A cosine schedule computed against the wrong step count silently mis-schedules the whole run (see [[Concept - Learning Rate Schedules for Pretraining]]).
- [ ] Parallelism degrees multiply to the world size: `DP × TP × PP × CP × EP == num_GPUs`, with no silent under- or over-subscription.
- [ ] Weight decay is excluded from 1D parameters (LayerNorm/RMSNorm gains, biases and, per your convention, embeddings) via separate optimizer param groups.

## Numerics

- [ ] The precision decision (bf16 vs fp8) was made on purpose, not inherited from a template. See [[Concept - Mixed Precision Training]] and [[Concept - FP8 Training]].
- [ ] The gradient all-reduce / reduce-scatter dtype is fp32, not bf16, whatever the compute dtype.
- [ ] Loss computation, softmax and normalization-layer statistics run in fp32 even when the surrounding matmuls run in bf16/fp8.
- [ ] A gradient-clipping threshold (global norm, typically 1.0) is set and active.
- [ ] Stabilizers (qk-norm, [[Concept - z-loss and Logit Soft-Capping|z-loss]]) are on if the architecture or prior runs at this scale warrant them. See [[Concept - Training Stability and Loss Spikes]].

## Data

- [ ] All data shards are enumerated, and the shuffle/sampling order is deterministic and seeded.
- [ ] Packing / attention-reset masks are verified: concatenated documents don't silently attend across their boundary.
- [ ] Eval-set decontamination has been checked against the training corpus (see [[Concept - Benchmark Contamination]]) before the run consumes the data, not after.
- [ ] The dataloader resumes from an arbitrary step without re-shuffling or skipping/repeating data on restart.
- [ ] BOS/EOS/PAD handling is verified end-to-end: no double-BOS, no loss computed over padding tokens.

## Checkpoint & restart

- [ ] Asynchronous checkpointing is enabled and tested, not only configured: a save actually completes without stalling training for more than a few seconds.
- [ ] A full restart-from-checkpoint reproduces the pre-checkpoint loss trajectory exactly. RNG state, dataloader position and optimizer moments are all confirmed restored along with the weights (see [[Concept - Distributed Checkpointing]]).
- [ ] Checkpoint writes are atomic (write-then-rename) and a keep-last-N retention policy is active, so a crash mid-write can't corrupt the most recent usable checkpoint.

## Observability

- [ ] Dashboards for loss, gradient norm, learning rate, MFU and tokens-seen exist and update live during the run.
- [ ] NaN/Inf alerting pages someone, instead of logging a line nobody reads.
- [ ] Per-rank health (liveness, last heartbeat) is monitored, so automation catches a hung rank before a human notices the loss curve stopped moving.
- [ ] ETA and running cost are tracked against the budget that justified the run.

## Canary run

- [ ] The exact target configuration has run for 500-2000 steps at full scale (not a scaled-down proxy) before you commit to the full token budget.
- [ ] The canary hits the expected MFU range (roughly 40-55% for a well-tuned dense-model configuration). Missing it by a wide margin means something in the parallelism or kernel configuration is wrong, and finding that now is far cheaper.
- [ ] The canary includes at least one checkpoint-save-and-resume cycle, confirmed bit-for-bit consistent (or loss-consistent, given known nondeterminism) with an uninterrupted run over the same steps.
- [ ] No loss spikes or grad-norm anomalies occurred during the canary window.

## Why these items

- **LR schedule step-count matching** is here because of a specific, recurring incident. Resume a cosine-decay run after a config change with the wrong "remaining steps" and it silently re-derives a different decay curve. The loss curve looks *plausible*; it just isn't the run you meant to launch.
- **Eval decontamination before the run, not after,** because contamination found post-hoc makes every benchmark number from the run suspect, and you can't un-train on data you've already consumed.
- **Restart reproducing the exact pre-checkpoint trajectory** is the highest-value item on the list. An incomplete restore (missing dataloader state, wrong RNG seed) produces a visible loss discontinuity at every restart. At 10,000+ GPU scale a node fails every few hours, so a run that restarts imperfectly piles up dozens of small, compounding corruptions over its lifetime.
- **Fp32 reduce dtype**, because bf16-reduced gradients across hundreds of ranks are a documented, hard-to-diagnose source of slow divergence that looks like ordinary training noise until it doesn't.
- **The canary at full target configuration**, because scaled-down proxies (fewer GPUs, shorter sequences) routinely miss the bugs that only appear at real scale: interconnect topology mismatches, mesh misconfiguration, checkpoint I/O bottlenecks.

## Connections
- [[Deep Dive - Anatomy of a Pretraining Run]] — the full run lifecycle this checklist gates entry into; use that note to design the run, this one to verify it before launch.
- [[Playbook - Debugging a Diverging Training Run]] — what to do when a run fails despite passing this checklist, or when the canary itself reveals a problem.
- [[Concept - Distributed Checkpointing]] — the mechanism behind the checkpoint/restart section's items.
- [[Concept - Training Stability and Loss Spikes]] — the mechanisms behind the numerics-section stabilizer items.
- [[Concept - Mixed Precision Training]] — the precision decisions this checklist assumes have already been made deliberately.
- [[Concept - FP8 Training]] — the alternative precision path the numerics-section decision item weighs against bf16.
- [[Concept - Scaling Laws]] — the source of the token-budget target the config-sizing section verifies against.
- [[Concept - Learning Rate Schedules for Pretraining]] — the schedule whose total-step count must match the token budget exactly.
- [[Concept - z-loss and Logit Soft-Capping]] — one of the concrete stabilizers the numerics section checks for.
- [[Concept - Benchmark Contamination]] — the decontamination check that belongs in the data section, and why it must happen before consumption.
- [[Gotchas - Distributed Training]] — the specific failure signatures (hangs, silent desync, rank misconfiguration) that a rigorous canary run is designed to catch before they cost a full launch.
- [[Concept - LLM Observability and Tracing]] — the dashboarding and alerting infrastructure the observability section assumes is already built, not built during the run.
