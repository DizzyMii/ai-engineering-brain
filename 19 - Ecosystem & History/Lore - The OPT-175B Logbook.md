---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [OPT, OPT-175B, Open Pre-trained Transformer, the OPT chronicles]
summary: "Meta's OPT-175B shipped weights, code, AND its full training logbook — the first public look at what babysitting a 175B run really costs."
---

# Lore - The OPT-175B Logbook

> In May 2022 Meta AI did something no frontier lab had done. Along with a GPT-3-scale model and its code, it released the **daily logbook of the training run**: spikes, NaNs, dead GPUs and 3 a.m. manual restarts, warts and all. For a generation of engineers it was the first honest answer to "what is training a 175B model actually like?"

## What happened

**OPT-175B** (Zhang et al., Meta AI, "OPT: Open Pre-trained Transformer Language Models," May 2022) was an open reproduction of GPT-3 at 175B parameters. It shipped with weights for researchers, full training code in the `metaseq` repo, and, the radical part, a `chronicles` folder of the team's real-time notes. Susan Zhang led the run. The team trained on **992 A100-80GB GPUs** over roughly two months of wall-clock, and the logbook (well over a hundred pages of daily entries) recorded the run *as it happened*, not as a cleaned-up retrospective. That broke with the [[Reference - The AI Lab Landscape]] norm of publishing capability numbers and withholding the operational reality.

The reality was **firefighting**. There was no smooth loss curve, just a sequence of divergences and recoveries. The loss would spike or go NaN, and a human on call would roll back to the last checkpoint, change something and relaunch. The team restarted from checkpoints **dozens of times** (Susan Zhang has discussed the cadence in public talks). Most restarts had nothing to do with the model. They were **hardware**: dead GPUs, uncorrectable ECC memory errors, and NCCL collective hangs that froze the whole [[Concept - Data Parallelism and ZeRO]] job until someone killed and rescheduled it. The parallelism itself, [[Concept - Tensor and Pipeline Parallelism]] across the cluster via Megatron, worked. The substrate under it kept failing.

A major subplot was **numerical**. OPT-175B trained in **fp16**, not bf16, and fp16's narrow exponent range let gradients underflow to zero. The team relied on **dynamic loss scaling**: multiply the loss by a large factor so small gradients stay representable, then unscale before the optimizer step. Much of the logbook's drama is the loss scale hitting its floor and the run diverging into NaNs anyway, the pathology catalogued in [[Lore - Loss Scaling and the fp16 Underflow Crisis]] (the mechanism is in [[Concept - Mixed Precision Training]]). Their toolkit for escaping a divergence was blunt and manual: **lower the learning rate, skip the problem batches, restore optimizer state from a good checkpoint, and re-tune the loss-scaling factor.** They also had to learn *triage* on the job, telling a **hardware-induced** spike (a flipped bit, a flaky link) from a **data- or optimization-induced** one (a bad batch, an LR too hot), because the fixes are completely different.

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

That last relation is the main engineering lesson: **checkpoint cadence sets the price of each failure.** Checkpoint too rarely and every crash costs hours of recomputation on 992 GPUs; too often and I/O eats throughput. The team also published an unusually honest **compute/carbon** accounting. OPT put its own training footprint at roughly **one-seventh of the estimated GPT-3 figure** (Meta's estimate was on the order of ~75 tCO₂e), a rare case of a lab quantifying the real cost of a frontier run.

## The lesson

**At frontier scale, pretraining is an operations problem as much as an ML problem.** The bottleneck isn't a cleverer optimizer. It's reliability, checkpointing discipline, failure triage and a human on-call rotation. The [[Deep Dive - Anatomy of a Pretraining Run]] toolkit engineers now take for granted (frequent async checkpoints, automatic restart from checkpoint, spike detection, batch skipping on divergence, health monitoring for silent GPU failures) is essentially what OPT was inventing *live and writing down*. The hardware half of it, detecting and routing around dead GPUs and ECC storms, is now its own discipline (see [[Gotchas - Hardware Failures at Scale]]).

The second-order lesson is **transparency as infrastructure**. Publishing the logbook turned private tribal knowledge into a shared operational baseline. Two months later, [[Lore - The BLOOM Training Run]], trained on public compute by the BigScience collaboration, formalized much of the same firefighting into documented process and **switched to bf16** to avoid the fp16 loss-scaling crisis OPT had lived through. OPT is the corporate run that made the pain legible; the open-collaboration run turned it into a template.

## Evidence status

**Primary-source, verified.** None of this is folklore. The OPT paper, the model weights, the `metaseq` training code and the `chronicles` logbook are all public, and the run lead (Susan Zhang) has spoken about it publicly. The soft spot is exact counts: treat the number of restarts as "dozens, discussed in talks," not a single citable figure, and the carbon numbers are Meta's own estimates under a stated methodology. Everything important here comes from the published logbook and paper, which is why OPT-175B is a well-documented war story and not a legend.

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
