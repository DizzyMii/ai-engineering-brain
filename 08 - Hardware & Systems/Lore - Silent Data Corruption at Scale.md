---
tags: [lore, domain/hardware-systems, level/unicorn]
aliases: [SDC, mercurial cores, corrupt execution errors, CEE]
summary: "Meta and Google found chips that silently compute wrong answers — mercurial cores — and what SDC taught large-fleet ML training."
---

## What happened

Around 2020–2021, two of the largest compute fleets on earth each found the same unsettling thing: some perfectly healthy-looking processors were computing wrong answers. They didn't crash, log an error or trip ECC. They returned the wrong result for certain inputs, deterministically, on one specific core. The industry had treated "the CPU computes exactly what I asked" as an axiom for decades. At fleet scale it was false often enough to matter.

Meta's account, **"Silent Data Corruptions at Scale" (Dixit et al. 2021)**, started as a debugging nightmare. A data-processing pipeline produced corrupted output that reproduced only on certain machines. Months of tracing pointed away from software and toward a single CPU core that miscomputed one operation on specific operands. Meta turned that into an operational fact: across millions of cores, a few per several thousand machines are **"mercurial,"** silently and repeatably wrong. They built dedicated infrastructure to hunt them: *Fleetscanner* (opportunistic out-of-production silicon testing) and *Ripple* (lightweight periodic in-production checks).

Google's **"Cores that Don't Count" (Hochschild et al. 2021, HotOS)** named the same phenomenon independently: **corrupt execution errors (CEEs)** from mercurial cores, and sharpened the mechanism. The errors are often deterministic and specific to a data path. One core botches a particular multiply, vector op or data-dependent computation while the rest of the chip is fine. They can shift with voltage, frequency, temperature and age, and they tend to *appear after burn-in* instead of as classic infant mortality, so manufacturing screens can't catch them. Google's headline rate matched Meta's order of magnitude: a few mercurial cores per several thousand machines.

For anyone running a large [[Deep Dive - Anatomy of a Pretraining Run|pretraining run]], SDC is concrete. It shows up as an unexplained loss spike or NaN that reproduces on one rank and vanishes when the job moves. Far worse, it can be gradient corruption that never trips a NaN check and silently poisons a checkpoint you keep training from. Meta's Llama 3 team documented the GPU version directly (Dubey et al. 2024): among 419 unexpected interruptions on 16k H100s they attribute events to silent data corruption, and they describe building deterministic value checks to catch GPUs computing wrong results. The folklore version is everywhere. A large fraction of big-run logbooks, including [[Lore - The OPT-175B Logbook]], have a passage shaped like *"the run diverged, we could not find a bug, we swapped the node, it went away."*

## The lesson

Mechanically: **at scale, hardware isn't a trustworthy oracle.** Most engineers assume the silicon executes exactly what they asked, so any wrong answer is their bug. That convenient fiction breaks once you multiply by $10^4$ devices and $10^7$ device-seconds. When a big run misbehaves, "it's probably a bug in our code" is sometimes a lie the silicon tells you, and it's a seductive one because it sends the investigation in the wrong direction.

The engineering answer is redundancy and verification, taking the posture of [[Concept - Floating Point for Deep Learning|defensive numerics]] down from arithmetic to the device:

- **Deterministic replay / dueling replicas.** Run the same computation twice on different hardware and compare. A divergence points to the bad device, not a bad line of code.
- **Checksums and idempotency checks** around communication and I/O, confirming that what a computation or transfer produced matches an independent recomputation.
- **Per-rank monitoring.** Grad-norm and activation-norm outliers *by rank* expose a misbehaving device before it poisons a checkpoint.
- **Quarantine discipline.** A suspect node gets cordoned and stress-tested out of band, not thrown straight back into the scheduler pool.

The localization habit (move the job, see whether the fault follows the node) is the one from [[Playbook - Debugging a Hung Distributed Training Job]]. SDC is the worst entry in the wider [[Gotchas - Hardware Failures at Scale|at-scale failure taxonomy]] because, unlike an Xid or an ECC event, it raises no signal. There's also a symmetry with performance. The process variation that makes some chips slow under a power cap (see [[Concept - GPU Clocks, Power, and Thermal Throttling]]) is a cousin of the variation that makes a rare core mercurial. Silicon isn't identical unit to unit, in speed *or* in correctness.

## Evidence status

- **Verified.** The phenomenon is published, peer-reviewed, and independently corroborated by two organizations: Meta (Dixit et al. 2021) and Google (Hochschild et al. 2021). The rate (a few bad cores per several thousand machines) and the deterministic, data-dependent, age- and temperature-sensitive character are well established.
- **Well-sourced.** The AI-training manifestation and deterministic-check detection are documented in the Llama 3 paper (Dubey et al. 2024) and corroborating engineering write-ups.
- **Well-sourced folklore.** Specific "we swapped the node and the divergence went away" episodes in individual training logbooks are real and common, but rarely instrumented tightly enough to *prove* SDC over some other transient fault. Treat them as strong folklore, not proof, and label them that way when you retell them.

## Connections
- [[Gotchas - Hardware Failures at Scale]] — SDC is entry #1 in that taxonomy; this note is its war-story expansion and the reason it ranks worst.
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — the performance face of the same silicon variation: speed drift here, correctness drift there.
- [[Lore - The OPT-175B Logbook]] — a primary logbook full of the "swap the node, divergence vanished" episodes SDC explains.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where SDC actually bites: mid-run divergence and, worst case, a silently poisoned checkpoint.
- [[Playbook - Debugging a Hung Distributed Training Job]] — the localization procedure (move the job, see if the fault follows) reused for SDC hunting.
- [[Concept - Floating Point for Deep Learning]] — the defensive-numerics mindset SDC extends from the arithmetic to the hardware executing it.

## Sources
- Dixit et al. (2021) — *Silent Data Corruptions at Scale* (Meta). First large-scale characterization; introduces the Fleetscanner/Ripple detection split.
- Hochschild et al. (2021) — *Cores that Don't Count* (Google, HotOS XVIII). Names CEEs / mercurial cores; establishes the deterministic, condition-sensitive mechanism and the rate.
- Dubey et al. (2024) — *The Llama 3 Herd of Models.* Documents silent data corruption in GPU training and deterministic detection at 16k-GPU scale.
