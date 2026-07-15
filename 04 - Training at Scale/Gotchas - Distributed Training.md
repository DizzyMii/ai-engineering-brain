---
tags: [gotchas, domain/training-at-scale, level/advanced]
aliases: [distributed training pitfalls, multi-GPU training gotchas, NCCL hangs]
summary: "Multi-GPU training pitfalls ordered by pain: NCCL hangs, silent gradient desync, non-determinism, uneven shards, mesh misconfiguration."
---

# Gotchas - Distributed Training

## 1. NCCL hangs on a collective mismatch

**Symptom:** the job stops making progress. No crash, no traceback — GPU utilization on every rank drops to near zero and stays there until a watchdog timeout (often 10-30 minutes later) finally kills it.
**Cause:** collectives are **rendezvous points** — every rank in a process group must call the same collective, in the same order, the same number of times, or the call blocks forever waiting for a peer that never shows up. The classic trigger is data-dependent control flow: one rank's microbatch happens to be empty, or hits a different code branch (an `if` on a locally-computed condition, a try/except that only fires on one rank), and that rank silently skips an [[Concept - All-Reduce and Collective Operations|all-reduce]] or all-gather that every other rank is still waiting on.
**Fix:** make control flow **rank-invariant** — any branch that changes how many collectives fire must be decided from a value that's identical across all ranks (broadcast the decision, or all-reduce a boolean flag, before branching), not from local data.
**Detection:** `NCCL_DEBUG=INFO` and `TORCH_NCCL_ASYNC_ERROR_HANDLING=1` surface which collective is stuck and on which rank; a stack-trace dump on hang (via `py-spy dump` across ranks, or `torch.distributed`'s built-in flight-recorder in recent PyTorch) shows the mismatched call site directly. This is listed first because it burns the most wall-clock of any failure mode here — jobs routinely sit hung for the full timeout window before anyone notices, and at 1000+ GPUs that's not a small amount of wasted spend.

## 2. Silent gradient desync

**Symptom:** the job runs, the loss curve looks completely normal — until an eval metric that should match a known-good run doesn't, or a checkpoint restored on a different rank layout produces different outputs than expected. There is no crash to point at.
**Cause:** something subtly different happens per rank while every rank still executes the same number of collectives, so nothing hangs. Common root causes: a dropout or augmentation RNG that isn't correctly seeded per-rank (so ranks either all get identical "randomness," defeating the point, or drift from each other in a way that should have been synchronized); a buffer (e.g., a running statistic) that's updated locally but never re-synced; or a manually-written gradient hook that fires on some ranks and not others.
**Fix:** audit every source of per-rank state for whether it's *supposed* to be identical or *supposed* to be independent, and make sure the implementation matches the intent — buffers that must match across ranks need an explicit sync (broadcast from rank 0, or periodic all-reduce), not an assumption that identical code produces identical state.
**Detection:** periodically all-reduce a checksum (e.g., a hash or a sum) of a parameter tensor across ranks and assert it's identical; if it isn't, ranks have desynced and every subsequent step is now training a different model per rank without anyone knowing.

## 3. Non-determinism defeats reproducibility

**Symptom:** re-running the identical config, identical seed, identical data produces a measurably different loss curve — not wildly different, but different enough that A/B comparisons between two "identical" runs are noise.
**Cause:** several independent sources of nondeterminism stack up: per-rank dataloader worker seeding that isn't derived deterministically from the global seed and rank ID; nondeterministic cuDNN/cuBLAS kernel selection (many GPU kernels use algorithms whose exact floating-point reduction order isn't fixed run-to-run); and atomic reductions in collectives, where floating-point addition is not associative, so summing the same numbers in a different order produces a different bit pattern (see [[Lore - The Nondeterminism of Floating-Point Reductions]]).
**Fix:** set `torch.use_deterministic_algorithms(True)`, seed dataloader workers as a function of `(base_seed, rank, worker_id)`, and accept the throughput cost of deterministic kernel variants where reproducibility genuinely matters (debugging a regression, reproducing a published number) — but don't pay that cost by default in production training, where it isn't worth the throughput loss.
**Detection:** run the same config twice for a few hundred steps and diff the loss curves; anything beyond floating-point noise in the first few decimal places indicates a real source of nondeterminism worth chasing down.

## 4. Uneven data shards stall or deadlock DDP

**Symptom:** training hangs specifically near the end of an epoch, or throughput degrades and then the job stalls, without an obvious error.
**Cause:** if the dataset doesn't divide evenly across ranks, some ranks run out of batches before others. Under plain DDP, a rank that finishes its epoch early and moves on to backward/optimizer/next-epoch setup, while other ranks are still expecting it to participate in a gradient all-reduce, produces exactly the collective-mismatch hang described in gotcha #1 — this is a specific, extremely common instance of that general failure.
**Fix:** use `drop_last=True` on the sampler to guarantee equal batch counts per rank, or PyTorch's `Join` context manager, which lets finished ranks participate in "shadow" no-op collectives so ranks that finish early don't desync the ones still working. Always call `DistributedSampler.set_epoch(epoch)` at the start of each epoch — omitting it means every epoch reshuffles identically, silently reducing your effective data diversity.
**Detection:** a hang that correlates with epoch boundaries (rather than being uniformly distributed across the run) is the tell; checking each rank's per-epoch batch count is the direct confirmation.

## 5. Rank, mesh, and environment misconfiguration

**Symptom:** ranges from an immediate crash (`RuntimeError: Distributed package doesn't have NCCL built in`, address-already-in-use) to something much worse — a job that runs, trains, and produces a model, but at a fraction of the MFU it should hit, with nothing in the logs actively complaining.
**Cause:** `WORLD_SIZE`, `RANK`, `LOCAL_RANK`, and `MASTER_ADDR`/`MASTER_PORT` set incorrectly (especially common when hand-rolling multi-node launches instead of using `torchrun` or a scheduler-integrated launcher); a [[Concept - Tensor and Pipeline Parallelism|tensor-parallel]] group that ends up spanning nodes instead of staying intra-node — silent because the job still runs correctly, just over a much slower link than TP was designed for (see [[Pattern - 3D Parallelism Composition]] for why TP must stay intra-node); or mismatched CUDA/NCCL/driver versions across nodes in a heterogeneous cluster, which can produce anything from a crash to a silent correctness bug depending on the mismatch.
**Fix:** always launch via `torchrun` or the cluster scheduler's native distributed launch integration rather than hand-setting environment variables; explicitly log and assert the device-mesh shape and which physical GPUs/nodes each parallelism dimension maps to at startup, so a misplaced TP group is visible in the logs before it costs a full run's worth of MFU.
**Detection:** an MFU number well below the expected range (see [[Deep Dive - Anatomy of a Pretraining Run]] for what "expected" looks like) with no other symptom is the signature of a topology misconfiguration — always check the mesh-to-hardware mapping before assuming the model or kernels are the problem.

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
