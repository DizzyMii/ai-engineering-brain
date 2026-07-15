---
tags: [concept, domain/hardware-systems, level/unicorn]
aliases: [thermal throttling, DVFS, boost clock, power capping, clock stragglers]
summary: "Why real GPUs drift below spec — boost clocks, power caps, thermal throttling — creating stragglers, non-determinism, and MFU variance."
---

> **One-paragraph hook:** A GPU's datasheet FLOPs number is a best case measured near its boost clock, on cold silicon, with power unconstrained. Under sustained training or serving load in a warm rack it runs slower — and because the slowdown varies GPU-to-GPU and minute-to-minute, it quietly manufactures stragglers, non-reproducible benchmarks, and a gap between your napkin peak-FLOPs and measured [[Concept - Model FLOPs Utilization (MFU)|MFU]]. Every engineer who locks clocks before profiling has been burned by this once.

## The mechanism

GPUs run **DVFS** (dynamic voltage and frequency scaling): clock frequency is not fixed, but chosen moment-to-moment as the highest value the current power and thermal budget allow. Four distinct effects push the real clock below the number on the box.

**Base vs boost clock.** Spec sheets quote a *boost* clock (H100 SXM ≈ 1980 MHz) that the chip sustains only with power and thermal headroom; the guaranteed floor is the lower *base* clock. The headline 989 BF16 TFLOP/s figure is computed at boost. Dynamic power scales as
$$P \approx C\,V^2 f,$$
capacitance $C$ times voltage squared times frequency — and because a stable higher $f$ requires higher $V$, power climbs *super-linearly* with clock. That is why the last few percent of frequency cost a disproportionate share of the 700 W board budget, and why throttling gives them back first.

**Power capping.** An H100 SXM is a 700 W part. When a dense matmul drives it to the power limit, firmware downclocks to stay within budget. Operators also cap deliberately (`nvidia-smi -pl 500`) to fit a rack's power and cooling envelope — datacenters are frequently *power-limited before they are compute-limited*, so trading a few percent of clock for GPU density per rack is a rational, common choice.

**Thermal throttling.** Above a junction-temperature threshold (mid-80s to ~90 °C for the core; HBM carries its own limit), hardware slowdown cuts clocks to protect the silicon. Inlet air temperature, airflow, and physical rack position therefore change the clock a given GPU can hold — the *same* job runs slower on a hotter GPU. This is what makes cooling a first-order performance variable and pushes GB200-class racks (~120 kW) onto liquid cooling; power and cooling are the binding constraints that define an [[Concept - Anatomy of an AI Training Cluster|AI training cluster]].

**Silicon lottery.** Process variation means two nominally identical dies need different voltages to reach the same frequency. Under a fixed power cap the "leakier" die settles at a lower clock — so some GPUs in any fleet are persistently a few percent slower, permanently, with no fault to detect.

## In practice

- **Straggler creation.** Synchronous data-parallel training is gated by a barrier — [[Concept - All-Reduce and Collective Operations|all-reduce]] — so the slowest rank sets step time for the whole job. A single GPU throttled 5% by heat or silicon luck taxes all 16k GPUs ~5% until it catches up. This is one row in the broader [[Gotchas - Hardware Failures at Scale|at-scale failure taxonomy]] and a standing argument for straggler-aware scheduling.
- **Reproducibility.** Clock drift makes microbenchmarks noisy: a kernel that "regressed 8%" between runs often just caught a different clock. Lock clocks with `nvidia-smi -lgc <min,max>` (and disable auto-boost) before any [[Concept - The Roofline Model|roofline]] measurement — it is basic profiling hygiene. Numeric-level run-to-run variation is a related but distinct problem, covered in [[Concept - Nondeterminism in LLM Inference]].
- **Monitoring.** DCGM exposes clock and throttle-reason bitfields (SW power cap, HW thermal slowdown, HW power brake, SW thermal); `nvidia-smi -q -d PERFORMANCE` surfaces the same "Clocks Throttle Reasons." Correlating throttle events against MFU dips is how you attribute a slow run to physics rather than to your code.
- **Cost.** Sustained clock is money: power caps and cooling set both throughput and the electricity bill, feeding straight into [[Concept - Cost Engineering for LLM Applications]]. A cluster capped for density is explicitly trading $/token against $/rack.

## Failure modes

- **Peak-FLOPs inflation.** Because vendors quote boost-clock (and sometimes sparse) peaks, the denominator in an MFU calculation is optimistic; a run at "45% MFU" against boost peak can be materially higher against *sustained* peak. Use a measured sustained peak or the metric lies — this is a concrete reason [[Concept - Model FLOPs Utilization (MFU)|MFU]] looks disappointing.
- **Chronic straggler misread as a network fault.** A persistently slow rank looks like a bad link; check DCGM throttle reasons before blaming the fabric. The differential is in [[Playbook - Debugging a Hung Distributed Training Job]].
- **Power excursions.** Synchronized compute — all GPUs slamming from idle at a collective boundary back to full power — causes tens-of-MW facility power swings (reported during Llama 3 training), stressing PSUs and the grid; firmware power-smoothing and clock ramping mitigate it.
- **Thermal runaway in a bad slot.** Top-of-rack or poor-airflow GPUs throttle chronically; detection is per-GPU temperature-plus-clock telemetry, not aggregate cluster averages that hide the outlier.

## The non-obvious

Two nominally identical GPUs are not identical — in speed *or* in correctness. The silicon lottery guarantees a spread of sustained clocks across any fleet, so "identical" data-parallel workers finish at different times *by default*; the slowest is a permanent tax, not a transient to wait out. The deeper cut: the same unit-to-unit process variation that makes one GPU slow is a cousin of what makes a rare core compute wrong answers — see [[Lore - Silent Data Corruption at Scale]]. Everything practitioners do here — locking clocks for benchmarks, capping power for density, scheduling around the hottest and slowest GPUs — is a reaction to one underlying fact: the datasheet describes an idealized chip that your warm, power-limited rack does not contain.

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
