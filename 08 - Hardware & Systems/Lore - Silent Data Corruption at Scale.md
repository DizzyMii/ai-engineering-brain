---
tags: [lore, domain/hardware-systems, level/unicorn]
aliases: [SDC, mercurial cores, corrupt execution errors, CEE]
summary: "Meta and Google found chips that silently compute wrong answers — mercurial cores — and what SDC taught large-fleet ML training."
---

## What happened

Around 2020–2021 two of the largest compute fleets on earth quietly discovered the same unsettling thing: some of their perfectly healthy-looking processors were computing wrong answers. Not crashing, not logging an error, not tripping ECC — just returning the wrong result for certain inputs, deterministically, on one specific core. The industry had spent decades treating "the CPU computes exactly what I asked" as an axiom. At fleet scale, it turned out to be false often enough to matter.

Meta's account, **"Silent Data Corruptions at Scale" (Dixit et al. 2021)**, began as a debugging nightmare. A data-processing pipeline produced corrupted output that reproduced only on certain machines; months of tracing pointed not to a software bug but to a single CPU core that miscomputed a specific operation on specific operands. Meta generalized this into an operational fact: across millions of cores, a few per several thousand machines are **"mercurial"** — silently, repeatably wrong. They built dedicated detection infrastructure to hunt it: *Fleetscanner* (opportunistic out-of-production silicon testing) and *Ripple* (lightweight periodic in-production checks).

Google's **"Cores that Don't Count" (Hochschild et al. 2021, HotOS)** named the phenomenon independently: **corrupt execution errors (CEEs)** from mercurial cores. Their observations sharpened the mechanism. The errors are often deterministic and data-path-specific — one core botches a particular multiply, vector op, or data-dependent computation while the rest of the chip is fine. They can shift with voltage, frequency, temperature, and age, and they tend to *appear after burn-in* rather than as classic infant mortality, so you cannot screen them out at manufacturing. Their headline rate matched Meta's order of magnitude: a few mercurial cores per several thousand machines.

For anyone running a large [[Deep Dive - Anatomy of a Pretraining Run|pretraining run]], SDC stopped being an abstraction. It shows up as an unexplained loss spike or a NaN that reproduces on one rank and evaporates when the job moves — or, far worse, as gradient corruption that never trips a NaN check and silently poisons a checkpoint that you keep training from. Meta's Llama 3 team documented the GPU version directly (Dubey et al. 2024): among 419 unexpected interruptions on 16k H100s they attribute events to silent data corruption and describe building deterministic value checks to catch GPUs computing wrong results. The folklore version is everywhere — a large fraction of big-run logbooks, including the [[Lore - The OPT-175B Logbook]], contain a passage of the shape: *"the run diverged, we could not find a bug, we swapped the node, it went away."*

## The lesson

Mechanically: **at scale, hardware is not a trustworthy oracle.** The mental model most engineers carry — the silicon executes exactly what you asked, so any wrong answer is your bug — is a convenient fiction that breaks once you multiply by $10^4$ devices and $10^7$ device-seconds. When a big run misbehaves, *"it's probably a bug in our code"* is sometimes a lie the silicon tells you, and it is a seductive one because it points investigation in exactly the wrong direction.

The engineering response is redundancy and verification, extending the same defensive posture as [[Concept - Floating Point for Deep Learning|defensive numerics]] from arithmetic down to the device itself:

- **Deterministic replay / dueling replicas.** Run the same computation twice on different hardware and compare; divergence localizes the bad device rather than the bad line of code.
- **Checksums and idempotency checks** around communication and I/O — verify that what a computation or transfer produced matches an independent recomputation.
- **Per-rank monitoring.** Grad-norm and activation-norm outliers *by rank* surface a misbehaving device before it poisons a checkpoint.
- **Quarantine discipline.** A suspect node is cordoned and stress-tested out of band, not thrown straight back into the scheduler pool.

The localization muscle — move the job, watch whether the fault follows the node — is the same one used in [[Playbook - Debugging a Hung Distributed Training Job]], and SDC is the worst entry in the broader [[Gotchas - Hardware Failures at Scale|at-scale failure taxonomy]] precisely because, unlike an Xid or an ECC event, it raises no signal. There is also a deep symmetry with performance: the very process variation that makes some chips slow under a power cap (see [[Concept - GPU Clocks, Power, and Thermal Throttling]]) is a cousin of the variation that makes a rare core mercurial. Silicon is not identical unit-to-unit — in speed *or* in correctness.

## Evidence status

- **Verified.** The phenomenon is published, peer-reviewed, and independently corroborated by two organizations: Meta (Dixit et al. 2021) and Google (Hochschild et al. 2021). The rate (a few bad cores per several thousand machines) and the deterministic, data-dependent, age/temperature-sensitive character are well established.
- **Well-sourced.** The AI-training manifestation and the deterministic-check detection practice are documented in the Llama 3 paper (Dubey et al. 2024) and corroborating engineering write-ups.
- **Well-sourced folklore.** Specific "we swapped the node and the divergence went away" attributions in individual training logbooks are real and common, but are rarely instrumented tightly enough to *prove* SDC versus another transient fault. Treat them as strong folklore, not proof — and label them that way when you retell them.

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
