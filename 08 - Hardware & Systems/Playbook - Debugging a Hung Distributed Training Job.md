---
tags: [playbook, domain/hardware-systems, level/advanced]
aliases: [NCCL hang debugging, distributed training hang]
summary: "Diagnostic sequence for a multi-GPU job that stalls: isolate collective deadlock, straggler, dead GPU, or network fault."
---

> **Goal:** find out why a multi-GPU/multi-node training job stopped making progress, and get it running again without silently losing correctness.
> **When to run this:** the step-time log stops advancing, or the framework raises "Watchdog caught collective timeout" (PyTorch) or an equivalent NCCL error.
> **Prerequisites:** shell access to all nodes (or a log-aggregation system that has it), `nvidia-smi`, `ibstat`/`ibdiagnet` if on InfiniBand, and permission to restart the job from checkpoint.

## Steps

1. **Capture the hang signature before touching anything.** Set `NCCL_DEBUG=INFO` and `NCCL_DEBUG_SUBSYS=ALL` (relaunch if they weren't set; many teams leave them on permanently on training clusters) and grab the full stderr/stdout from every rank, not only rank 0. *Expected:* a "Watchdog caught collective timeout" message naming a rank, a collective type and a timeout duration (PyTorch's `c10d` default is ~30 minutes). *If not:* no watchdog message and a job that's slow but still moving means a chronic slowdown, not a hang. Jump to step 5.

2. **Find which collective and which rank(s) stalled.** Match the timeout message against your parallelism layout (data/[[Concept - Tensor and Pipeline Parallelism|tensor/pipeline]] ranks) to tell whether the stalled op is a gradient [[Concept - All-Reduce and Collective Operations]] (data-parallel), an all-to-all (MoE dispatch) or a point-to-point send/recv (pipeline stage boundary). *Expected:* one or a few ranks show "still waiting" while most report having entered the collective and are blocked on it. *If not:* every rank blocked the same way with no outlier suggests something systemic, like the network fabric being down, and not one bad node. Go straight to step 5.

3. **Rule out a mismatched-collective deadlock.** Check that every rank called the *same* collective, with the same tensor shape and dtype, in the same order. Divergent control flow is the most common self-inflicted cause. Typical versions: `if has_data: dist.all_reduce(...)` where one rank's local batch came up empty, uneven per-rank batch counts from a dataset split that isn't a multiple of world size, or an `if rank == 0` branch that accidentally wraps a collective. *Expected:* code review or a per-rank call-order log shows the divergence. *If not:* if every rank provably called identical ops in identical order, it's not a logic bug. Move on to hardware and network.

4. **Localize a straggler.** Ring [[Concept - All-Reduce and Collective Operations|all-reduce]] waits for its slowest participant every step, so one slow GPU or node stalls the whole ring. Add per-rank step-time logging if you don't have it, and turn on the PyTorch NCCL flight recorder (`TORCH_NCCL_TRACE_BUFFER_SIZE`) to capture the last N collective calls per rank with timestamps. *Expected:* one rank's step time is a clear outlier (2x+ its peers) in the steps before the hang. *If not:* no outlier and a uniformly slow ring point at fabric-wide congestion (step 6), not a single node.

5. **Isolate hardware on the suspect node(s).** Check `dmesg` for Xid errors (NVIDIA's GPU error codes: Xid 79 is "GPU has fallen off the bus", Xid 63/64 are ECC errors). Run `nvidia-smi -q` for ECC counts and thermal state, `ibstat` for InfiniBand link flaps or down ports, and DCGM (`dcgmi diag`) for a fuller health sweep that includes thermal throttling. *Expected:* a concrete hardware signal (Xid error, ECC uncorrectable count > 0, IB port down, failed DCGM health check) on the straggler or stalled rank from step 4. *If not:* clean hardware on the suspect node points back to the network fabric or software.

6. **Tell a true deadlock from a chronic slowdown.** A real hang makes zero progress until the watchdog fires at its timeout (~30 min default, often too long for fast iteration, so teams commonly tighten it in dev). A chronic slowdown crawls forward at a fraction of expected throughput and never times out. If you suspect that, don't wait for a watchdog that won't fire. Use step 4's per-rank timing. If you're diagnosing this repeatedly, temporarily lower the collective timeout (`TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC` or equivalent) so future failures show up faster.

7. **Diagnose network-fabric faults.** On RoCE, look for PFC (priority flow control) storms or ECN misconfiguration causing congestion collapse. The symptom is many ranks stalling at roughly the same time with no single bad node. On InfiniBand, look for a flaky cable or transceiver (intermittent link flaps in `ibstat`/`ibdiagnet` logs) or an adaptive-routing misconfiguration that creates a hot spot. [[Concept - Network Topology for AI Clusters]] explains how oversubscription and rail layout make some traffic patterns (e.g., all-to-all under MoE) more fragile than plain all-reduce.

8. **Recover.** Exclude the bad node (cordon it in the scheduler or drop it from the rank list) and restart from the last checkpoint. This is the standing argument for frequent checkpointing and elastic, fault-tolerant training: what a hang costs you is the progress lost on restart, not the hang itself.

## Verification

The job resumes and step time is back to baseline on *all* ranks, including the ones that were fine before, for at least several minutes of continuous progress. Re-check `dmesg`/DCGM on the excluded node before returning it to the pool. A node pulled for one Xid error can and does fail again.

## When it goes wrong

| Symptom | Likely cause | Jump to |
|---|---|---|
| Watchdog fires, one rank never entered the collective | Divergent control flow (uneven batches, conditional collective) | Step 3 |
| Watchdog fires, all ranks entered but one never finished | Straggler GPU/node: slow, throttling, or ECC-degraded | Steps 4-5 |
| No watchdog, throughput just degraded fleet-wide | Chronic slowdown, not a hang. Check thermal throttling ([[Concept - GPU Clocks, Power, and Thermal Throttling]]) or fabric congestion | Steps 6-7 |
| Many ranks stall near-simultaneously, no single outlier | Network fabric issue: RoCE PFC storm, IB fabric-wide fault, or an oversubscribed link | Step 7 |
| Job hangs again soon after resuming on the same node | Hardware fault wasn't really excluded, or is intermittent (bad cable, marginal DIMM) | Step 5, exclude more aggressively |
| Numerically wrong results *without* a hang | A different failure class. See [[Lore - Silent Data Corruption at Scale]], not this playbook | N/A |

## Connections
- [[Concept - Tensor and Pipeline Parallelism]] — knowing which rank layout produced the stalled collective (data-parallel all-reduce vs pipeline send/recv) is a prerequisite for step 2.
- [[Concept - All-Reduce and Collective Operations]] — the collective semantics (ring steps, bandwidth-optimal vs latency-optimal) that step 2 and 4 require you to reason about.
- [[Breakdown - NCCL]] — the library actually emitting the `NCCL_DEBUG` output this playbook is built around; know its internals to read the logs correctly.
- [[Gotchas - Hardware Failures at Scale]] — the taxonomy of the hardware faults step 5 is screening for.
- [[Concept - Network Topology for AI Clusters]] — why fabric topology and oversubscription determine whether step 7's faults are rare or routine at your cluster's scale.
- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — the physical layer underneath both the straggler and network-fault branches of this playbook.
- [[Deep Dive - Anatomy of a Pretraining Run]] — situates a hang as one specific failure mode inside the broader operational reality of running a long pretraining job.
- [[Lore - Silent Data Corruption at Scale]] — the scarier cousin of a hang: the run that doesn't stop but silently produces wrong gradients.
- [[Playbook - Incident Response for LLM Systems]] — the general incident-response shape (detect, isolate, recover, postmortem) this playbook specializes for the training-cluster case.

## Sources
- PyTorch distributed documentation — the `c10d` watchdog timeout behavior and `TORCH_NCCL_TRACE_BUFFER_SIZE` flight-recorder mechanism referenced in steps 1 and 4.
- NVIDIA Xid error reference — the Xid code taxonomy (e.g., 79 = GPU fallen off the bus) used in step 5's hardware isolation.
- folklore, weakly sourced: "always check for uneven per-rank batch counts first" is close to universal tribal knowledge among distributed-training engineers, rarely written up as a formal incident but the single most common self-inflicted hang cause reported informally.
