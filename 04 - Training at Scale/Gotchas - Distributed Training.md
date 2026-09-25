---
tags: [gotchas, domain/training-at-scale, level/advanced]
aliases: [distributed training pitfalls, multi-GPU training gotchas, NCCL hangs]
summary: "Multi-GPU training pitfalls ordered by pain: NCCL hangs, silent gradient desync, non-determinism, uneven shards, mesh misconfiguration."
---

# Gotchas - Distributed Training

## 1. NCCL hangs on a collective mismatch

**Symptom:** the job stops making progress. No crash, no traceback. GPU utilization on every rank drops to near zero and stays there until a watchdog timeout (often 10-30 minutes later) kills it.
**Cause:** collectives are rendezvous points. Every rank in a process group has to call the same collective, in the same order, the same number of times, or the call blocks forever waiting for a peer that never arrives. The classic trigger is data-dependent control flow. One rank's microbatch happens to be empty, or it takes a different branch (an `if` on a locally computed condition, a try/except that only fires on one rank), and that rank silently skips an [[Concept - All-Reduce and Collective Operations|all-reduce]] or all-gather that every other rank is still waiting on.
**Fix:** make control flow rank-invariant. Any branch that changes how many collectives fire has to be decided from a value that's identical on all ranks: broadcast the decision, or all-reduce a boolean flag, before branching. Never branch on local data.
**Detection:** `NCCL_DEBUG=INFO` and `TORCH_NCCL_ASYNC_ERROR_HANDLING=1` show which collective is stuck and on which rank. A stack-trace dump on hang (`py-spy dump` across ranks, or the flight recorder built into `torch.distributed` in recent PyTorch) points straight at the mismatched call site. It's first on this list because it burns more wall-clock than anything else here. Jobs routinely sit hung for the full timeout before anyone notices, and at 1000+ GPUs that's a lot of wasted spend.

## 2. Silent gradient desync

**Symptom:** the job runs and the loss curve looks normal. Then an eval metric that should match a known-good run doesn't, or a checkpoint restored on a different rank layout gives different outputs than expected. There's no crash to point at.
**Cause:** something differs per rank while every rank still runs the same number of collectives, so nothing hangs. Common root causes:
- a dropout or augmentation RNG seeded wrong per rank, so ranks either all get identical "randomness" (defeating the point) or drift apart in a way that should have been synchronized;
- a buffer (a running statistic, say) updated locally and never re-synced;
- a hand-written gradient hook that fires on some ranks and not others.

**Fix:** audit every source of per-rank state for whether it's *supposed* to be identical or *supposed* to be independent, and check that the code matches the intent. Buffers that must match across ranks need an explicit sync (broadcast from rank 0, or a periodic all-reduce). Identical code doesn't guarantee identical state.
**Detection:** periodically all-reduce a checksum (a hash or a sum) of a parameter tensor across ranks and assert it's identical. If it isn't, the ranks have desynced, and from then on each rank is training a different model without anyone knowing.

## 3. Non-determinism defeats reproducibility

**Symptom:** rerunning the identical config, seed and data gives a measurably different loss curve. Not wildly different, but enough that an A/B comparison between two "identical" runs is noise.
**Cause:** several independent sources of nondeterminism stack up. Per-rank dataloader workers aren't seeded deterministically from the global seed and rank ID. cuDNN/cuBLAS kernel selection is nondeterministic, and many GPU kernels use algorithms whose floating-point reduction order isn't fixed from run to run. Collectives use atomic reductions, and since floating-point addition isn't associative, summing the same numbers in a different order gives a different bit pattern (see [[Lore - The Nondeterminism of Floating-Point Reductions]]).
**Fix:** set `torch.use_deterministic_algorithms(True)`, seed dataloader workers as a function of `(base_seed, rank, worker_id)`, and pay the throughput cost of deterministic kernels where reproducibility matters (debugging a regression, reproducing a published number). Don't pay it by default in production training, where the throughput loss isn't worth it.
**Detection:** run the same config twice for a few hundred steps and diff the loss curves. Anything beyond floating-point noise in the first few decimal places is a real source of nondeterminism and worth chasing.

## 4. Uneven data shards stall or deadlock DDP

**Symptom:** training hangs near the end of an epoch, or throughput degrades and then the job stalls, with no obvious error.
**Cause:** if the dataset doesn't divide evenly across ranks, some ranks run out of batches first. Under plain DDP, a rank that finishes its epoch early moves on to backward/optimizer/next-epoch setup while the others still expect it in a gradient all-reduce. The result is the collective-mismatch hang from gotcha #1, and this is an extremely common instance of it.
**Fix:** use `drop_last=True` on the sampler so every rank gets the same batch count, or PyTorch's `Join` context manager, which has finished ranks join "shadow" no-op collectives so early finishers don't desync the ranks still working. Always call `DistributedSampler.set_epoch(epoch)` at the start of each epoch. Skip it and every epoch reshuffles identically, which silently cuts your effective data diversity.
**Detection:** the tell is a hang that lines up with epoch boundaries instead of landing anywhere in the run. Checking each rank's per-epoch batch count confirms it.

## 5. Rank, mesh, and environment misconfiguration

**Symptom:** anything from an immediate crash (`RuntimeError: Distributed package doesn't have NCCL built in`, address-already-in-use) to something much worse: a job that runs, trains and produces a model at a fraction of the MFU it should hit, with nothing in the logs complaining.
**Cause:** three common ones.
- `WORLD_SIZE`, `RANK`, `LOCAL_RANK` and `MASTER_ADDR`/`MASTER_PORT` set wrong, especially common when hand-rolling multi-node launches instead of using `torchrun` or a scheduler-integrated launcher.
- A [[Concept - Tensor and Pipeline Parallelism|tensor-parallel]] group that spans nodes instead of staying intra-node. It's silent because the job still runs correctly, only over a much slower link than TP was designed for (see [[Pattern - 3D Parallelism Composition]] for why TP must stay intra-node).
- Mismatched CUDA/NCCL/driver versions across nodes in a heterogeneous cluster, which can produce anything from a crash to a silent correctness bug depending on the mismatch.

**Fix:** always launch via `torchrun` or the cluster scheduler's native distributed launch integration; don't hand-set environment variables. At startup, log and assert the device-mesh shape and which physical GPUs/nodes each parallelism dimension maps to, so a misplaced TP group shows up in the logs before it costs a full run's worth of MFU.
**Detection:** MFU well below the expected range (see [[Deep Dive - Anatomy of a Pretraining Run]] for what "expected" looks like) with no other symptom is the signature of a topology misconfiguration. Check the mesh-to-hardware mapping before blaming the model or kernels.

## Connections
- [[Concept - Data Parallelism and ZeRO]] — the DDP mechanism whose collective structure gotcha #1 and #4 exploit the failure modes of.
- [[Concept - All-Reduce and Collective Operations]] — the collective primitives underlying every hang and desync described here.
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — inherits and compounds the same collective-mismatch risks, with more collectives per step (all-gather plus reduce-scatter) than plain DDP.
- [[Concept - Tensor and Pipeline Parallelism]] — the parallelism dimension whose intra-node placement requirement gotcha #5's mesh misconfiguration silently violates.
- [[Playbook - Debugging a Diverging Training Run]] — the operational procedure for numerics-driven failures (spikes, NaNs), the companion to this note's systems-driven failures (hangs, desync).
- [[Concept - Distributed Checkpointing]] — a hung or desynced job is only recoverable if checkpointing was working correctly beforehand; ties directly to gotcha #1 and #2's recovery path.
- [[Pattern - 3D Parallelism Composition]] — the placement rules (TP intra-node, PP/DP across nodes) that gotcha #5's mesh-misconfiguration failure mode violates.
- [[Deep Dive - Anatomy of a Pretraining Run]] — the reference for the expected MFU range that gotcha #5's detection method checks against.
- [[Playbook - Debugging a Hung Distributed Training Job]] — the hardware- and systems-level diagnostic playbook for exactly the hang scenario in gotcha #1, one level below this note's mechanism-first framing.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — the deeper mechanism (non-associative floating-point addition) behind gotcha #3's atomic-reduction nondeterminism.
