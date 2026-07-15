---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [OPT, OPT-175B, Open Pre-trained Transformer, the OPT chronicles]
summary: "Meta's OPT-175B shipped weights, code, AND its full training logbook — the first public look at what babysitting a 175B run really costs."
---

# Lore - The OPT-175B Logbook

> In May 2022 Meta AI did something no frontier lab had done: it released not just a GPT-3-scale model and its code, but the **daily logbook of the training run** — spikes, NaNs, dead GPUs, and 3 a.m. manual restarts, warts and all. For a generation of engineers it was the first honest answer to "what is training a 175B model actually like?"

## What happened

**OPT-175B** (Zhang et al., Meta AI, "OPT: Open Pre-trained Transformer Language Models," May 2022) was an open reproduction of GPT-3 at 175B parameters, released with weights to researchers, full training code in the `metaseq` repo, and — the radical part — a `chronicles` folder containing the team's real-time notes. Susan Zhang led the run. The team trained on **992 A100-80GB GPUs** over roughly two months of wall-clock, and the logbook (well over a hundred pages of daily entries) documented the run *as it happened*, not as a sanitized retrospective. This was the opposite of the [[Reference - The AI Lab Landscape]] norm, where labs publish capability numbers and withhold the operational reality; OPT laid the reality bare.

The reality was **firefighting**. The run did not proceed as a smooth loss curve. It was a sequence of divergences and recoveries: the loss would spike or go NaN, and a human on-call would roll back to the last checkpoint, change something, and relaunch. The team restarted from checkpoints **dozens of times** over the run (Susan Zhang has discussed the cadence in public talks). Most restarts were not the model's fault at all — they were **hardware**: dead GPUs, uncorrectable ECC memory errors, and NCCL collective hangs that froze the whole [[Concept - Data Parallelism and ZeRO]] job until someone killed and rescheduled it. The parallelism itself — [[Concept - Tensor and Pipeline Parallelism]] across the cluster via Megatron — worked; it was the substrate underneath that kept failing.

A crucial subplot was **numerical**. OPT-175B was trained in **fp16**, not bf16, and fp16's narrow exponent range meant gradients could underflow to zero. The team leaned on **dynamic loss scaling** — multiply the loss by a large factor to keep small gradients representable, then unscale before the optimizer step — and much of the logbook's drama is the loss scale hitting its floor and the run diverging into NaNs anyway (this is the exact pathology catalogued in [[Lore - Loss Scaling and the fp16 Underflow Crisis]]; the mechanism itself is [[Concept - Mixed Precision Training]]). Their toolkit for escaping a divergence was blunt and manual: **lower the learning rate, skip the problematic data batches, restore optimizer state from a good checkpoint, and re-tune the loss-scaling factor.** A running skill they had to develop on the job was *triage* — telling a **hardware-induced** spike (a flipped bit, a flaky link) apart from a **data-or-optimization-induced** one (a bad batch, an LR too hot), because the fix is completely different.

```
        ┌────────────── steady training ──────────────┐
        │                                              ▼
   [checkpoint]  ──►  loss NaN / spike  ──►  triage: hardware or data/opt?
        ▲                                    │              │
        │                                    ▼              ▼
        │                          dead GPU / ECC /   bad batch / LR too hot
        │                          NCCL hang           lower LR, skip batch,
        │                                    │          re-tune loss scale
        └──────── roll back, relaunch ◄──────┴──────────────┘

  work lost per failure  ≈  steps since last checkpoint  →  checkpoint cadence
                                                            is the cost dial
```

That last relation is the load-bearing engineering lesson: **checkpoint cadence sets how expensive each failure is.** Checkpoint too rarely and every crash costs hours of recomputation on 992 GPUs; checkpoint too often and I/O eats throughput. The team also published an unusually honest **compute/carbon** accounting — OPT put its own training footprint at roughly **one-seventh of the estimated GPT-3 figure** (Meta's estimate was on the order of ~75 tCO₂e), a rare case of a lab quantifying the true cost of a frontier run instead of hiding it.

## The lesson

Stated mechanically: **at frontier scale, pretraining is an operations problem as much as an ML problem.** The bottleneck is not a cleverer optimizer — it is reliability, checkpointing discipline, failure triage, and a human on-call rotation. The [[Deep Dive - Anatomy of a Pretraining Run]] that engineers now take for granted — frequent async checkpoints, automatic restart-from-checkpoint, spike detection, batch-skipping on divergence, health monitoring for silent GPU failures — is essentially the toolkit OPT was inventing *in real time and writing down*. The hardware side of that toolkit — how you detect and route around dead GPUs and ECC storms — is now its own discipline (see [[Gotchas - Hardware Failures at Scale]]).

The second-order lesson is about **transparency as infrastructure**. By publishing the logbook, OPT converted private tribal knowledge into a shared operational baseline. Two months later, [[Lore - The BLOOM Training Run]] — trained on public compute by the BigScience collaboration — formalized much of the same firefighting into documented process, and notably **switched to bf16** specifically to dodge the fp16 loss-scaling crisis OPT had lived through. The OPT logbook is the connective tissue: the corporate run that made the pain legible, which the open-collaboration run then turned into a template.

## Evidence status

**Primary-source, verified.** This is not folklore. The OPT paper, the model weights, the `metaseq` training code, and the actual `chronicles` logbook are all public and on the record; the run lead (Susan Zhang) has spoken about it publicly. The one soft spot is exact counts — the precise number of restarts is best treated as "dozens, discussed in talks" rather than a single citable figure, and the carbon numbers are Meta's own estimates using a stated methodology. Everything load-bearing here is drawn from the published logbook and paper, which is precisely what makes OPT-175B an unusually well-documented war story rather than legend.

## Connections

- [[Deep Dive - Anatomy of a Pretraining Run]] — OPT was inventing this note's checkpoint/restart/triage toolkit live; read it to see the formalized version of the logbook's improvisation.
- [[Concept - Mixed Precision Training]] — the fp16 + dynamic loss scaling mechanism whose failure modes fill the logbook.
- [[Concept - Data Parallelism and ZeRO]] — the sharded-data-parallel substrate whose NCCL hangs and dead workers forced many of the rollbacks.
- [[Concept - Tensor and Pipeline Parallelism]] — the model-parallel decomposition (Megatron) that held the 175B run across 992 GPUs.
- [[Lore - The BLOOM Training Run]] — the open-collaboration successor that formalized OPT's firefighting and switched to bf16 to avoid the fp16 crisis.
- [[Reference - The AI Lab Landscape]] — situates Meta AI/FAIR and its commoditize-the-complement openness posture that produced OPT in the first place.
- [[Gotchas - Hardware Failures at Scale]] — the hardware-triage discipline (dead GPUs, ECC, NCCL hangs) that most OPT restarts actually exercised.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the exact numerical pathology OPT fought and BLOOM later engineered around.

## Sources
- Zhang et al. (2022) — *OPT: Open Pre-trained Transformer Language Models*. The paper, weights, and (via `metaseq`) the code and `chronicles` logbook.
- Meta AI `metaseq` repository — the public training code and the daily `chronicles` notes documenting spikes, restarts, and hardware failures.
- Susan Zhang, public talks (2022–2023) — first-hand recollections of the restart cadence and triage practice from the run's lead.
