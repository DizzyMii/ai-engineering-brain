---
tags: [playbook, domain/hardware-systems, level/advanced]
aliases: [NCCL hang debugging, distributed training hang]
summary: "Diagnostic sequence for a multi-GPU job that stalls: isolate collective deadlock, straggler, dead GPU, or network fault."
---

> **Goal:** determine why a multi-GPU/multi-node training job has stopped making progress, and get it running again without silently losing correctness.
> **When to run this:** a job's step-time log stops advancing, or the framework raises a "Watchdog caught collective timeout" (PyTorch) or equivalent NCCL error.
> **Prerequisites:** shell access to all nodes (or a log-aggregation system that already has it), `nvidia-smi`, `ibstat`/`ibdiagnet` if on InfiniBand, and permission to restart the job from checkpoint.

## Steps

1. **Capture the hang signature before touching anything.** Set `NCCL_DEBUG=INFO` and `NCCL_DEBUG_SUBSYS=ALL` (re-launch if not already set — many teams set these permanently on training clusters) and grab the full stderr/stdout from every rank, not just rank 0. *Expected observation:* a "Watchdog caught collective timeout" message naming a specific rank, collective type, and a timeout duration (PyTorch's default is ~30 minutes for `c10d`). *Deviation meaning:* if there's no watchdog message at all and the job is merely slow (not stopped), you're chasing a chronic slowdown, not a hang — jump to step 5.

2. **Identify which collective and which rank(s) stalled.** Cross-reference the timeout message against your parallelism topology (data/[[Concept - Tensor and Pipeline Parallelism|tensor/pipeline]] rank layout) to know whether the stalled op is a gradient [[Concept - All-Reduce and Collective Operations]] (data-parallel), an all-to-all (MoE dispatch), or a point-to-point send/recv (pipeline stage boundary). *Expected observation:* one or a small number of ranks show "still waiting," while most ranks report having entered the collective and are blocked on it. *Deviation meaning:* if literally every rank is blocked identically with no outlier, suspect a systemic issue (network fabric down, not a single bad node) — go straight to step 5.

3. **Rule out a mismatched-collective deadlock.** Check whether all ranks actually called the *same* collective, with the same tensor shape/dtype, in the same order. Divergent control flow is the most common self-inflicted cause: a conditional `if has_data: dist.all_reduce(...)` where one rank's local batch happened to be empty, uneven per-rank batch counts from a non-multiple-of-world-size dataset split, or an `if rank == 0` branch that accidentally wraps a collective call. *Expected observation:* code review or a rank-by-rank call-order log reveals the divergence. *Deviation meaning:* if all ranks provably called identical ops in identical order, this isn't a logic bug — proceed to hardware/network isolation.

4. **Localize a straggler.** A single slow GPU or node stalls an entire ring — ring [[Concept - All-Reduce and Collective Operations|all-reduce]] must wait for its slowest participant every step. Add per-rank step-time logging if you don't already have it, and use the PyTorch NCCL flight recorder (`TORCH_NCCL_TRACE_BUFFER_SIZE`) to capture the last N collective calls per rank with timestamps. *Expected observation:* one rank's step time is a clear outlier (2x+ its peers) in the steps leading up to the hang. *Deviation meaning:* no single outlier and uniformly slow ring → look at fabric-wide congestion (step 6), not one bad node.

5. **Isolate hardware on the suspect node(s).** Check `dmesg` for Xid errors (NVIDIA's GPU error codes — Xid 79 is "GPU has fallen off the bus," Xid 63/64 are ECC errors), run `nvidia-smi -q` for ECC error counts and thermal state, `ibstat` for InfiniBand link flaps or down ports, and DCGM (`dcgmi diag`) for a fuller health sweep including thermal throttling. *Expected observation:* a concrete hardware signal (Xid error, ECC uncorrectable count > 0, IB port down, DCGM failing health check) that correlates with the straggler/stalled rank from step 4. *Deviation meaning:* clean hardware health on the suspect node points back toward a network-fabric or software cause.

6. **Distinguish a true deadlock from a chronic slowdown.** A true hang shows zero progress until the watchdog fires at its configured timeout (~30 min default — often too long for fast iteration, teams commonly tighten it in dev). A chronic slowdown instead shows the job crawling forward at a fraction of expected throughput without ever timing out. If you suspect the latter, don't wait for a watchdog that won't fire; use step 4's per-rank timing directly. If diagnosing repeatedly, temporarily lower the collective timeout (`TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC` / equivalent) so failures surface faster in future runs.

7. **Diagnose network-fabric faults.** On RoCE, check for PFC (priority flow control) storms or ECN misconfiguration causing congestion collapse — a symptom is many ranks stalling roughly simultaneously with no single bad node. On InfiniBand, check for a flaky cable/transceiver (intermittent link flaps in `ibstat`/`ibdiagnet` logs) or an adaptive-routing misconfiguration causing a hot spot. See [[Concept - Network Topology for AI Clusters]] for how oversubscription and rail layout make certain traffic patterns (e.g., all-to-all under MoE) more fragile than plain all-reduce.

8. **Recover.** Exclude the bad node (cordon it in the scheduler / drop it from the rank list) and restart from the last checkpoint. This is the concrete, standing case for frequent checkpointing and elastic/fault-tolerant training setups — the cost of a hang is bounded by how much progress you'd lose restarting, not by the hang itself.

## Verification

The job resumes and step-time returns to baseline across *all* ranks (not just the previously-healthy majority) for at least several minutes of continuous progress. Re-check `dmesg`/DCGM on the excluded node before returning it to the pool — a node pulled for one Xid error can and does recur.

## When it goes wrong

| Symptom | Likely cause | Jump to |
|---|---|---|
| Watchdog fires, one rank never entered the collective | Divergent control flow (uneven batches, conditional collective) | Step 3 |
| Watchdog fires, all ranks entered but one never finished | Straggler GPU/node — slow, throttling, or ECC-degraded | Steps 4-5 |
| No watchdog, throughput just degraded fleet-wide | Chronic slowdown, not a hang — check thermal throttling ([[Concept - GPU Clocks, Power, and Thermal Throttling]]) or fabric congestion | Steps 6-7 |
| Many ranks stall near-simultaneously, no single outlier | Network fabric issue: RoCE PFC storm, IB fabric-wide fault, or an oversubscribed link | Step 7 |
| Job hangs again shortly after resuming on the same node | Hardware fault wasn't actually excluded, or is intermittent (bad cable, marginal DIMM) | Step 5, exclude more aggressively |
| Numerically wrong results *without* a hang | Different failure class entirely — see [[Lore - Silent Data Corruption at Scale]], not this playbook | N/A |

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
