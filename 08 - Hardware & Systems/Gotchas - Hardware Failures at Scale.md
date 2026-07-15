---
tags: [gotchas, domain/hardware-systems, level/unicorn]
aliases: [Xid errors, GPU fall-off-bus, at-scale hardware failures, SDC training]
summary: "At-scale GPU failure taxonomy: fall-off-bus/Xid, ECC, silent data corruption, thermal stragglers, IB flaps — symptoms and detection."
---

At a few thousand GPUs, hardware failure stops being an event and becomes the weather. The system failure rate is the sum of the per-device rates, so mean time between failures shrinks linearly with fleet size: $\text{MTBF}_{\text{sys}} \approx \text{MTBF}_{\text{device}} / N$. Assume a generous per-GPU MTBF of ~50,000 h (~5.7 yr) and a 16,384-GPU cluster fails on average every **~3 hours**. That is not a worst case — it is roughly what Meta measured on Llama 3 (Dubey et al. 2024): **419 unexpected interruptions in a 54-day snapshot** on 16k H100s (one every ~3.1 h), with **~78% traced to hardware**. The [[Lore - The OPT-175B Logbook]] is the canonical raw record of the same reality — ~35+ restarts and 100+ hosts cycled over a two-month run on 992 A100s — and BigScience's BLOOM 176B run averaged roughly one to two GPU failures per week. The consequence for a large [[Deep Dive - Anatomy of a Pretraining Run|pretraining run]]: failure is the steady state, so checkpoint frequently and make restart elastic. The gotchas below are ordered by how much they cost you when they hit.

## 1. A GPU computes wrong answers with no error flag (SDC)

**Symptom:** gradients or activations that are subtly wrong or produce NaNs; a loss spike or divergence that reproduces on a *specific rank/node* and vanishes when the job moves to other hardware; in the worst case, a silently poisoned checkpoint with no anomaly at all.
**Cause:** a defective ALU or data path that deterministically miscomputes on particular operand patterns — a "mercurial core." No ECC event, no Xid, no exception. This is the single most dangerous entry precisely because nothing fires.
**Fix:** quarantine the node, restore from a pre-corruption checkpoint, stress-test the suspect out of band before returning it to the pool.
**Detection:** the hardest of all — deterministic replay on a second GPU and compare; per-rank grad-norm / activation-norm outlier monitoring; checksums around [[Concept - All-Reduce and Collective Operations|collective operations]]. The war stories and detection discipline are in [[Lore - Silent Data Corruption at Scale]].

## 2. "GPU has fallen off the bus" and fatal Xid errors

**Symptom:** `nvidia-smi` hangs or reports the GPU is inaccessible; the training process dies or a collective times out. `dmesg` logs an `NVRM: Xid` line.
**Cause:** the GPU stopped responding on the PCIe/NVLink fabric. The high-value codes: **Xid 79** ("GPU has fallen off the bus" — often thermal, power, or a seating/hardware fault), **Xid 48** (double-bit ECC / uncorrectable), **Xid 119/120** (GSP RPC timeout, Hopper-specific). Xid 13/31 are usually application bugs, not dead silicon — read the code before condemning the card.
**Fix:** cordon and drain the node, restart from checkpoint on healthy hardware; an Xid 79 node frequently recurs, so re-verify before returning it.
**Detection:** scrape `dmesg`/journald for `Xid`, run DCGM health checks (`dcgmi diag`), and `nvidia-smi -q` for the fuller state.

## 3. The loss spike that is actually a dying GPU

**Symptom:** a sudden loss spike or NaN mid-run. The reflex is to blame the math — LR too high, a bad data shard, fp16 overflow.
**Cause:** at scale, a fraction of spikes are one bad GPU corrupting a gradient, not the optimization. The discriminating tell: a *math/data* spike reproduces when you replay the same step and data on any hardware; a *hardware* spike follows a specific rank/node regardless of the data. Confusing the two burns days.
**Fix:** localize by checkpoint-diffing per-rank grad norms and by moving the job off the suspect node — if the spike disappears, it was silicon, not your schedule.
**Detection:** per-rank grad-norm/activation-norm logging with outlier alerts, plus deterministic replay. The math-side differential (when it really *is* the optimizer) lives in [[Concept - Training Stability and Loss Spikes]].

## 4. One hot or slow GPU throttles all 16k (thermal/clock stragglers)

**Symptom:** global step time creeps up, or one rank is consistently the slowest participant in every all-reduce and the whole [[Concept - All-Reduce and Collective Operations|collective]] barrier waits on it.
**Cause:** a GPU in a hot rack position, with poor airflow, or with worse silicon throttles its clocks under sustained load and runs a few percent slower. Because a synchronous collective is a barrier, the slowest rank sets step time for the entire job — a 5% straggler taxes the whole cluster ~5%.
**Fix:** improve airflow, relocate, or exclude the chronic laggard; adopt straggler-aware scheduling.
**Detection:** per-rank step-time histograms and DCGM throttle-reason counters, correlated with inlet temperature. The mechanism is in [[Concept - GPU Clocks, Power, and Thermal Throttling]].

## 5. Uncorrectable ECC and row-remap exhaustion

**Symptom:** Xid 48/94/95, a killed process, or `nvidia-smi` showing remapped-row counts climbing toward "remapping failure."
**Cause:** HBM bit flips. Single-bit errors (SBE) are corrected silently; double-bit errors (DBE) are fatal. Ampere+ remaps bad rows from a small reserve pool, and when the reserve is exhausted the GPU is finished.
**Fix:** drain the GPU. A rising SBE/remap trend is a leading indicator of imminent DBE — retire proactively rather than let it kill a 12-hour-checkpoint-interval run.
**Detection:** `nvidia-smi -q -d ECC` for SBE/DBE and remapped-row counts; DCGM ECC fields; trend the SBE rate rather than reading a single snapshot.

## 6. IB link flaps and RoCE congestion collapse

**Symptom:** NCCL stalls or raises a collective timeout; scale-out throughput drops with no dead GPU.
**Cause:** a flaky transceiver or cable, an InfiniBand link flap, or RoCE PFC/ECN misconfiguration driving congestion collapse in the scale-out fabric — the failure surface of the [[Concept - Network Topology for AI Clusters|cluster's network topology]]. Oversubscribed upper tiers make all-to-all (MoE) traffic especially fragile.
**Fix:** isolate the port (`ibstat`/`ibdiagnet`), replace the transceiver, fix ECN/PFC, reroute around the fault.
**Detection:** `ibstat` for link flaps, IB port error counters, `NCCL_DEBUG=INFO`; the full isolation procedure is [[Playbook - Debugging a Hung Distributed Training Job]].

## 7. Power excursions from synchronized compute

**Symptom:** facility power swings of tens of MW as GPUs enter and exit compute at collective boundaries; PSU/breaker stress and transient power-cap throttling.
**Cause:** a synchronized job idles all GPUs during a large all-reduce, then slams them back to full power in unison — Meta reported tens-of-MW grid fluctuations during Llama 3 training. The power delivery, not the compute, becomes the stressed subsystem.
**Fix:** firmware/scheduler mitigations that ramp power or inject filler work at collective boundaries; leave power-cap headroom.
**Detection:** DCGM power telemetry and facility PDU monitoring, correlated against the training step's collective schedule.

## Connections
- [[Lore - Silent Data Corruption at Scale]] — the deep war-story treatment of gotcha #1, the failure that fires no alarm and poisons checkpoints.
- [[Playbook - Debugging a Hung Distributed Training Job]] — the step-by-step for when #2/#4/#6 surface as an NCCL hang.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — the mechanism behind the thermal/clock stragglers of #4 and the power excursions of #7.
- [[Concept - Network Topology for AI Clusters]] — where IB flaps and RoCE congestion (#6) live; topology also sets each failure's blast radius.
- [[Deep Dive - Anatomy of a Pretraining Run]] — the end-to-end run these failures interrupt; it motivates checkpoint cadence and elastic restart.
- [[Lore - The OPT-175B Logbook]] — the canonical primary record of relentless hardware failure during a large run.
- [[Concept - All-Reduce and Collective Operations]] — the synchronous barrier that turns one slow or dead GPU into a whole-job stall.
- [[Concept - Training Stability and Loss Spikes]] — the math-side differential diagnosis for gotcha #3, the loss spike that is *not* the silicon.

## Sources
- Dubey et al. (2024) — *The Llama 3 Herd of Models.* Reliability section: 419 unexpected interruptions in a 54-day snapshot on 16,384 H100s, ~78% hardware; documents SDC detection and datacenter power fluctuations.
- Zhang et al. (2022) — *OPT-175B* (and its public training logbook). Primary record of at-scale hardware failure: dozens of restarts and 100+ hosts cycled.
- BigScience (2022) — *BLOOM 176B* training chronicles. Recurring GPU failures across a ~3.5-month run on 384 A100s.
- NVIDIA — Xid error reference and DCGM documentation. Authoritative for Xid codes, ECC/row-remap fields, and throttle-reason counters.
