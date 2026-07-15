---
tags: [concept, domain/training-at-scale, level/advanced]
aliases: [DCP, sharded checkpointing, checkpoint resharding, torch.distributed.checkpoint]
summary: "Saving and reloading sharded model+optimizer state across thousands of GPUs without stalling training or losing resumability."
---

# Concept - Distributed Checkpointing

> **One-paragraph hook:** A 405B-parameter run's optimizer state alone is multiple terabytes of fp32 floats scattered across thousands of GPUs — writing that to durable storage without stalling training for minutes, and being able to load it back onto a cluster shaped differently than the one that saved it, is a distributed-systems problem in its own right, not an afterthought bolted onto the training loop.

## The mechanism

The core problem is scale: a dense model's checkpoint needs the fp32 master weights, the Adam moments $m$ and $v$, and the model weights themselves — roughly 16-20 bytes/param total (see [[Concept - Why Models Don't Fit on One GPU]]) — which for a 70B+ model is already hundreds of gigabytes to terabytes, and no single host has the RAM or disk bandwidth to write that as one file within a reasonable time. The solution every framework converges on is **sharded checkpointing**: each rank writes only the shard of state it locally owns (whatever [[Concept - Data Parallelism and ZeRO]] or [[Concept - Fully Sharded Data Parallel (FSDP)]] already partitioned to it), producing N shard files plus a metadata sidecar describing how the shards map to the logical, unsharded tensor. PyTorch's `torch.distributed.checkpoint` (DCP), Megatron's distributed checkpoint format, and DeepSpeed's ZeRO checkpoint format all follow this shape. Consolidating shards into one portable file (for release, for a different framework, or for eval) is a deliberate, separate offline step — never something done inline during training.

```
Rank 0 --shard 0--> [state_0.pt] --\
Rank 1 --shard 1--> [state_1.pt] ---+--> metadata.json (global tensor layout, DTensor placement)
Rank 2 --shard 2--> [state_2.pt] --/
   ...
Rank N --shard N--> [state_N.pt]

reload onto a DIFFERENT mesh (e.g. TP=8/PP=16 -> TP=4/PP=8):
metadata.json + shard files --reshard--> new per-rank shards matching new mesh
```

**Async checkpointing** hides the write behind ongoing compute: the state is first copied from GPU to pinned host (CPU) memory — a fast, blocking D2H transfer of seconds, not minutes — and a background thread then streams that pinned buffer to storage while the GPU resumes the next training step. DCP's `async_save` implements exactly this, turning what would be a multi-minute training stall into a few-second one.

**Resumability requires more than the weights.** A checkpoint that omits any of the following silently corrupts the resumed run rather than failing loudly: the Adam optimizer moments and fp32 master weights (without these, resuming looks like restarting training from scratch with warm weights — a de facto LR/momentum discontinuity); the LR-scheduler's step count (get this wrong and [[Concept - Learning Rate Schedules for Pretraining]] silently mis-schedules the rest of the run, e.g. resuming a cosine decay with the wrong remaining-steps count); the dataloader's position and shuffle seed (omitting this either replays already-seen data, wasting compute and risking memorization, or skips a data range entirely); and per-rank RNG state for CPU and GPU (missing this desynchronizes dropout masks and any other stochastic op across ranks in ways that are subtle rather than crash-loud).

**Reshard-on-load** is what separates a real distributed checkpoint format from a flat one. Continuing a run — or fine-tuning — on a differently-shaped cluster than the one that trained it (say, saved at TP=8/PP=16 and reloaded at TP=4/PP=8, or loaded without any pipeline parallelism at all for evaluation) requires recombining and re-splitting shards along the new mesh boundaries. DTensor-based formats (DCP with FSDP2, Megatron-Core's distributed checkpoint) carry enough global-layout metadata to do this automatically; a naive checkpoint that is just `torch.save`'d local state dicts per rank does not, and reshaping it requires a bespoke, error-prone conversion script.

## In practice

The checkpoint interval itself is an optimization problem, not a fixed cadence. The classic Young/Daly model for optimal checkpoint interval under a Poisson failure process is:

$$T^* \approx \sqrt{2 \cdot M \cdot C}$$

where $M$ is mean time between failures (MTBF) and $C$ is the wall-clock cost of writing one checkpoint. Illustratively: at $M = 4$ hours (240 min) and $C = 3$ min, $T^* = \sqrt{2 \cdot 240 \cdot 3} = \sqrt{1440} \approx 38$ minutes — checkpointing much more often than that wastes compute on redundant writes, and much less often risks losing more than the formula's break-even amount of work per failure. At 10,000+ GPU scale, where a node fails every few hours as a matter of routine (not an incident — see [[Deep Dive - Anatomy of a Pretraining Run]]), this pushes real production runs toward checkpointing every 20-40 minutes, which is only tolerable because async checkpointing keeps the stall cost low enough to afford that frequency.

## Failure modes

- **Corrupted or partial checkpoint from a mid-write crash**: a node failure or job preemption during the write leaves a half-written shard on disk. The fix is atomicity — write to a temporary path, `fsync`, then atomically rename into place — combined with retaining the last N checkpoints (never just the most recent one), so a corrupted latest checkpoint doesn't destroy the only recovery point.
- **Missing RNG or dataloader state**: as above, this doesn't crash — it silently changes what the resumed run is actually doing (different dropout patterns, replayed or skipped data), and the bug typically shows up much later as an unexplained loss discontinuity or an anomalously low held-out loss from data leakage.
- **OOM during consolidation**: merging all shards into a single portable file on one host can exceed that host's RAM even when the distributed sharded write worked perfectly, because consolidation naively materializes the full unsharded tensor in memory — the fix is streaming consolidation that writes each merged tensor to disk incrementally rather than holding the whole model in host RAM at once.
- **Slow storage bottlenecking the entire cluster**: if the durable storage backend's aggregate write bandwidth is lower than the burst write volume from every rank checkpointing simultaneously, all GPUs stall waiting on I/O — and because this looks identical to a generic training hang in cluster-level monitoring, it is a classic on-call trap that costs hours of debugging before someone checks the storage layer instead of the training code.

## The non-obvious

The most expensive checkpointing bugs live in the read path, not the write path. A checkpoint that saves cleanly every time but can't actually be resharded onto next quarter's differently-configured cluster is, for practical purposes, not a checkpoint at all — it's a write-only artifact. The discipline this implies: never trust a checkpoint format for a long run until you've exercised a full reshard-and-resume (different TP/PP/DP degrees than the run that saved it), not just a same-shape reload test, because same-shape reloads pass even when the metadata needed for resharding is silently missing or wrong.

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
