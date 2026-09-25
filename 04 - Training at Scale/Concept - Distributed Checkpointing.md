---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [DCP, sharded checkpointing, checkpoint resharding, torch.distributed.checkpoint]
summary: "Saving and reloading sharded model+optimizer state across thousands of GPUs without stalling training or losing resumability."
---

# Concept - Distributed Checkpointing

> **One-paragraph hook:** A 405B-parameter run's optimizer state alone is multiple terabytes of fp32 floats spread across thousands of GPUs. Writing that to durable storage without stalling training for minutes, then loading it back onto a cluster shaped differently from the one that saved it, is a distributed-systems problem in its own right. You can't bolt it onto the training loop as an afterthought.

## The mechanism

Start with size. A dense model's checkpoint holds the fp32 master weights, the Adam moments $m$ and $v$, and the model weights themselves: roughly 16-20 bytes/param total (see [[Concept - Why Models Don't Fit on One GPU]]). For a 70B+ model that's already hundreds of gigabytes to terabytes, and no single host has the RAM or disk bandwidth to write it as one file in reasonable time.

Every framework lands on **sharded checkpointing**. Each rank writes only the shard of state it owns locally (whatever [[Concept - Data Parallelism and ZeRO]] or [[Concept - Fully Sharded Data Parallel (FSDP)]] already partitioned to it). The output is N shard files plus a metadata sidecar that maps the shards to the logical, unsharded tensor. PyTorch's `torch.distributed.checkpoint` (DCP), Megatron's distributed checkpoint format and DeepSpeed's ZeRO checkpoint format all work this way. Consolidating shards into one portable file (for release, for a different framework, or for eval) is a separate offline step. It never happens inline during training.

```
Rank 0 --shard 0--> [state_0.pt] --\
Rank 1 --shard 1--> [state_1.pt] ---+--> metadata.json (global tensor layout, DTensor placement)
Rank 2 --shard 2--> [state_2.pt] --/
   ...
Rank N --shard N--> [state_N.pt]

reload onto a DIFFERENT mesh (e.g. TP=8/PP=16 -> TP=4/PP=8):
metadata.json + shard files --reshard--> new per-rank shards matching new mesh
```

**Async checkpointing** hides the write behind compute. State is first copied from GPU to pinned host (CPU) memory, a blocking D2H transfer that takes seconds. A background thread then streams the pinned buffer to storage while the GPU moves on to the next step. DCP's `async_save` does this, and it turns a multi-minute training stall into a few-second one.

Resuming needs more than the weights. Leave out any of the following and the resumed run is silently corrupted instead of failing loudly:

- The Adam moments and fp32 master weights. Without them, resuming amounts to restarting from scratch with warm weights, a de facto LR/momentum discontinuity.
- The LR scheduler's step count. Get it wrong and [[Concept - Learning Rate Schedules for Pretraining]] mis-schedules the rest of the run without complaint, e.g. resuming a cosine decay with the wrong remaining-steps count.
- The dataloader's position and shuffle seed. Missing these either replays data the model has seen (wasted compute, memorization risk) or skips a data range entirely.
- Per-rank RNG state for CPU and GPU. Without it, dropout masks and other stochastic ops desynchronize across ranks, and the effects are subtle, not crash-loud.

**Reshard-on-load** is what makes a checkpoint format distributed in any useful sense. Say you continue or fine-tune on a cluster shaped differently from the one that trained the model: saved at TP=8/PP=16 and reloaded at TP=4/PP=8, or loaded with no pipeline parallelism at all for evaluation. The shards have to be recombined and re-split along the new mesh boundaries. DTensor-based formats (DCP with FSDP2, Megatron-Core's distributed checkpoint) carry enough global-layout metadata to do this automatically. A naive checkpoint of `torch.save`'d per-rank local state dicts doesn't, and reshaping one takes a bespoke, error-prone conversion script.

## In practice

How often to checkpoint is an optimization problem. The classic Young/Daly model for the optimal interval under a Poisson failure process is:

$$T^* \approx \sqrt{2 \cdot M \cdot C}$$

where $M$ is mean time between failures (MTBF) and $C$ is the wall-clock cost of writing one checkpoint. Illustratively, at $M = 4$ hours (240 min) and $C = 3$ min, $T^* = \sqrt{2 \cdot 240 \cdot 3} = \sqrt{1440} \approx 38$ minutes. Checkpoint much more often and you waste compute on redundant writes; much less often and each failure can cost more than the formula's break-even amount of work.

At 10,000+ GPU scale a node fails every few hours as routine, not as an incident (see [[Deep Dive - Anatomy of a Pretraining Run]]). That pushes real production runs toward checkpointing every 20-40 minutes, and they can only afford that frequency because async checkpointing keeps the stall short.

## Failure modes

- **Corrupted or partial checkpoint from a mid-write crash.** A node failure or preemption during the write leaves a half-written shard on disk. Make writes atomic (write to a temporary path, `fsync`, then atomically rename into place) and retain the last N checkpoints, never only the latest, so one corrupted checkpoint doesn't take out your only recovery point.
- **Missing RNG or dataloader state.** Nothing crashes. The resumed run just does something different (other dropout patterns, replayed or skipped data), and the bug typically surfaces much later as an unexplained loss discontinuity or a suspiciously low held-out loss from data leakage.
- **OOM during consolidation.** Merging all shards into one portable file on a single host can blow past that host's RAM even when the sharded write worked perfectly, because naive consolidation materializes the full unsharded tensor in memory. Streaming consolidation fixes it by writing each merged tensor to disk incrementally.
- **Slow storage stalling the whole cluster.** If the storage backend's aggregate write bandwidth is below the burst volume of every rank checkpointing at once, all GPUs sit waiting on I/O. In cluster-level monitoring this looks identical to a generic training hang, so it's a classic on-call trap: hours of debugging the training code before anyone checks the storage layer.

## The non-obvious

The expensive checkpointing bugs are in the read path. A checkpoint that saves cleanly every time but can't be resharded onto next quarter's differently configured cluster is, for practical purposes, write-only. So don't trust a checkpoint format for a long run until you've done a full reshard-and-resume with different TP/PP/DP degrees than the run that saved it. A same-shape reload test isn't enough: it passes even when the metadata needed for resharding is missing or wrong.

## Connections
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — FSDP2's DTensor-based per-parameter sharding is what makes reshard-on-load tractable in the modern PyTorch stack.
- [[Concept - Tensor and Pipeline Parallelism]] — TP and PP degrees define the mesh that a checkpoint's shards are laid out against, and that a reshard must translate between.
- [[Deep Dive - Anatomy of a Pretraining Run]] — checkpointing is one stage of the full run lifecycle; this note is the mechanism behind that stage's "async checkpoints every N steps" detail.
- [[Checklist - Pre-Launch for a Large Training Run]] — verifying checkpoint save/load/reshard correctness belongs on this checklist before a long run starts, not after the first failure.
- [[Gotchas - Distributed Training]] — the broader catalog of distributed-training pitfalls that this note's failure modes are drawn from.
- [[Concept - GPU Memory Hierarchy]] — the D2H copy to pinned host memory that makes async checkpointing fast depends on understanding this hierarchy's transfer costs.
- [[Gotchas - Hardware Failures at Scale]] — the failure rate (MTBF) that drives the checkpoint-interval math is exactly the hardware failure behavior cataloged there.
- [[Concept - Model Lifecycle and Versioning]] — the consolidated, portable checkpoint produced by the offline merge step is the artifact that downstream model-versioning and release processes actually consume.
- [[Concept - Data Parallelism and ZeRO]] — the sharding scheme (ZeRO stage) each rank already owns is exactly what determines the shard it checkpoints.
- [[Concept - Learning Rate Schedules for Pretraining]] — a checkpoint that omits the scheduler's step count silently mis-schedules the resumed run's LR.
- [[Concept - Why Models Don't Fit on One GPU]] — the ~16-20 bytes/param memory footprint that makes a single-host checkpoint infeasible in the first place.

## Sources
- PyTorch Distributed Checkpointing (`torch.distributed.checkpoint`, DCP) — the sharded, DTensor-aware checkpoint format used by FSDP2/TorchTitan-style training stacks, including `async_save`.
- Young, J. W. (1974) — "A First Order Approximation to the Optimum Checkpoint Interval" — origin of the $\sqrt{2MC}$ checkpoint-interval heuristic.
- Daly, J. T. (2006) — "A Higher Order Estimate of the Optimum Checkpoint Interval for Restart Dumps" — refines the Young model for high-failure-rate HPC-scale systems, the regime large GPU clusters now live in.
