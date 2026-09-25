---
tags: [concept, domain/hardware-systems, level/unicorn]
aliases: [thermal throttling, DVFS, boost clock, power capping, clock stragglers]
summary: "Why real GPUs drift below spec — boost clocks, power caps, thermal throttling — creating stragglers, non-determinism, and MFU variance."
---

> **One-paragraph hook:** A GPU's datasheet FLOPs number is a best case, measured near boost clock on cold silicon with unconstrained power. Under sustained training or serving load in a warm rack it runs slower. The slowdown varies GPU to GPU and minute to minute, so it produces stragglers, benchmarks you can't reproduce, and a gap between your napkin peak-FLOPs and measured [[Concept - Model FLOPs Utilization (MFU)|MFU]]. Everyone who locks clocks before profiling got burned by this once.

## The mechanism

GPUs run **DVFS** (dynamic voltage and frequency scaling): the clock is picked moment to moment as the highest value the power and thermal budget allows. Four effects push it below the number on the box.

**Base vs boost clock.** Spec sheets quote a *boost* clock (H100 SXM ≈ 1980 MHz) that the chip only holds with power and thermal headroom. The guaranteed floor is the lower *base* clock, and the headline 989 BF16 TFLOP/s is computed at boost. Dynamic power scales as
$$P \approx C\,V^2 f,$$
capacitance $C$ times voltage squared times frequency. A stable higher $f$ needs a higher $V$, so power climbs *super-linearly* with clock. The last few percent of frequency eat a disproportionate share of the 700 W board budget, and they're the first thing throttling gives back.

**Power capping.** An H100 SXM is a 700 W part. When a dense matmul drives it to the power limit, firmware downclocks to stay in budget. Operators also cap on purpose (`nvidia-smi -pl 500`) to fit a rack's power and cooling envelope. Datacenters are frequently *power-limited before they are compute-limited*, so giving up a few percent of clock for more GPUs per rack is a rational, common trade.

**Thermal throttling.** Above a junction-temperature threshold (mid-80s to ~90 °C for the core; HBM has its own limit), hardware slowdown cuts clocks to protect the silicon. Inlet air temperature, airflow and rack position all change the clock a GPU can hold; the *same* job runs slower on a hotter GPU. Cooling is a first-order performance variable, and it pushes GB200-class racks (~120 kW) onto liquid cooling. Power and cooling are the hard limits that define an [[Concept - Anatomy of an AI Training Cluster|AI training cluster]].

**Silicon lottery.** Process variation means two nominally identical dies need different voltages to hit the same frequency. Under a fixed power cap the leakier die settles at a lower clock. Every fleet has GPUs that are a few percent slower forever, with no fault to detect.

## In practice

- **Stragglers.** Synchronous data-parallel training waits at a barrier, the [[Concept - All-Reduce and Collective Operations|all-reduce]], so the slowest rank sets step time for the whole job. One GPU throttled 5% by heat or silicon luck taxes all 16k GPUs ~5% until it catches up. One row in the [[Gotchas - Hardware Failures at Scale|at-scale failure taxonomy]], and a standing argument for straggler-aware scheduling.
- **Reproducibility.** Clock drift makes microbenchmarks noisy. A kernel that "regressed 8%" between runs often just caught a different clock. Lock clocks with `nvidia-smi -lgc <min,max>` (and turn off auto-boost) before any [[Concept - The Roofline Model|roofline]] measurement; it's basic profiling hygiene. Numeric run-to-run variation is a related but separate problem, covered in [[Concept - Nondeterminism in LLM Inference]].
- **Monitoring.** DCGM exposes clock and throttle-reason bitfields (SW power cap, HW thermal slowdown, HW power brake, SW thermal), and `nvidia-smi -q -d PERFORMANCE` shows the same "Clocks Throttle Reasons." Lining up throttle events against MFU dips is how you pin a slow run on physics instead of your code.
- **Cost.** Sustained clock is money. Power caps and cooling set throughput and the electricity bill, which feeds straight into [[Concept - Cost Engineering for LLM Applications]]. A cluster capped for density is trading $/token against $/rack on purpose.

## Failure modes

- **Peak-FLOPs inflation.** Vendors quote boost-clock (and sometimes sparse) peaks, so the denominator of an MFU calculation is optimistic. A run at "45% MFU" against boost peak can be materially higher against *sustained* peak. Use a measured sustained peak or the metric lies; it's one concrete reason [[Concept - Model FLOPs Utilization (MFU)|MFU]] looks disappointing.
- **Chronic straggler misread as a network fault.** A persistently slow rank looks like a bad link. Check DCGM throttle reasons before blaming the fabric; the differential is in [[Playbook - Debugging a Hung Distributed Training Job]].
- **Power excursions.** Synchronized compute, with every GPU jumping from idle back to full power at a collective boundary, causes facility power swings of tens of MW (reported during Llama 3 training). That stresses PSUs and the grid. Firmware power smoothing and clock ramping mitigate it.
- **Thermal runaway in a bad slot.** Top-of-rack or poor-airflow GPUs throttle chronically. You find them with per-GPU temperature-plus-clock telemetry; cluster-wide averages hide the outlier.

## The non-obvious

Two nominally identical GPUs aren't identical, in speed *or* in correctness. The silicon lottery guarantees a spread of sustained clocks across any fleet, so "identical" data-parallel workers finish at different times *by default*. The slowest one is a permanent tax, not a transient you can wait out. The process variation that makes one GPU slow is a cousin of what makes a rare core compute wrong answers ([[Lore - Silent Data Corruption at Scale]]). Locking clocks for benchmarks, capping power for density, scheduling around the hottest and slowest GPUs: all of it responds to one fact. The datasheet describes an idealized chip that your warm, power-limited rack doesn't contain.

## Connections
- [[Concept - Model FLOPs Utilization (MFU)]] — sustained-clock reality is a chief reason measured MFU trails a naive peak-FLOPs estimate.
- [[Gotchas - Hardware Failures at Scale]] — thermal/clock stragglers are one entry in that taxonomy; this note is their mechanism.
- [[Lore - Silent Data Corruption at Scale]] — the correctness face of the same silicon variation behind clock spread.
- [[Concept - The Roofline Model]] — its peak-FLOPs ceiling assumes a fixed clock that throttling violates; lock clocks to measure honestly.
- [[Playbook - Debugging a Hung Distributed Training Job]] — throttle-reason checks are part of isolating a straggler from a genuine network fault.
- [[Concept - Anatomy of an AI Training Cluster]] — power and cooling are the binding constraints there; throttling is where they cash out in performance.
- [[Concept - Cost Engineering for LLM Applications]] — power caps and cooling set both throughput and the electricity bill behind $/token.
- [[Concept - Nondeterminism in LLM Inference]] — clock variation is one source of the run-to-run timing noise that complicates reproducibility.

## Sources
- NVIDIA (2022) — *NVIDIA H100 Tensor Core GPU / Hopper Architecture Whitepaper.* Base/boost clocks, 700 W TDP, and the boost-clock-derived 989 BF16 TFLOP/s figure.
- NVIDIA — *DCGM and nvidia-smi documentation.* Throttle-reason bitfields, `-lgc` clock locking, `-pl` power capping.
- Dubey et al. (2024) — *The Llama 3 Herd of Models.* Reports tens-of-MW datacenter power fluctuations from synchronized GPU compute at 16k-GPU scale.
