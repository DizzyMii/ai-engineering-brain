---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [BLOOM, BigScience, BLOOM 176B, BigScience Workshop]
summary: "BigScience's BLOOM 176B: 1000+ researchers trained a fully-open multilingual LLM on a French public supercomputer, firefighting and all."
---

> **One-paragraph hook:** In 2022 a one-year, thousand-person, sixty-country academic collaboration trained a 176B-parameter multilingual language model on a grant of public supercomputer time in France — no corporate lab, no ad revenue, no closed API at the end. BLOOM is the proof-of-existence that frontier-scale pretraining can happen outside big tech, and the most transparent training run ever conducted: public loss curves, a documented corpus, a novel license, and honest carbon numbers. It is also a case study in how much the coordination overhead of doing it that way actually costs.

## What happened

**BigScience** (2021–2022) was a **one-year open research workshop** convening **1000+ researchers from 60+ countries**, coordinated in large part by Hugging Face and organized around **Jean Zay**, the French national public supercomputer operated by IDRIS/GENCI. The compute was a public research grant (millions of GPU-hours), not a corporate cluster — which is the entire point. This was frontier-scale model training run as an academic, publicly-funded, radically-open collaboration, a deliberate counterpoint to the corporate labs (see [[Reference - The AI Lab Landscape]]).

The flagship was **BLOOM 176B** (BigScience, July 2022): a 176-billion-parameter decoder-only model covering **46 natural languages and 13 programming languages**, trained on the **ROOTS corpus** — ~**1.6 TB** of text (~366B tokens) assembled through a documented, consent-aware data-governance process rather than an anonymous web scrape. Training ran on **384 A100-80GB GPUs** over roughly **3.5 months** (11 March – 6 July 2022). Architecturally BLOOM was GPT-3-shaped with two stability-motivated deviations: **ALiBi** positional biases instead of learned positional embeddings, and an **extra LayerNorm right after the embedding layer** — a change added specifically because earlier experiments diverged without it.

What makes BLOOM a *lore* entry rather than a spec sheet is the **radical openness of the process**, end to end:

- A **public TensorBoard** streamed the live loss curve while the run was happening — anyone on the internet could watch a 176B model train in real time, spikes and all.
- **Stas Bekman's engineering chronicles** (the `bigscience-workshop` "chronicles" and "lessons learned" writeups) documented the day-to-day firefighting in the same spirit as [[Lore - The OPT-175B Logbook|Meta's OPT-175B logbook]], but from a non-corporate team.
- The **data-governance and consent framework** for ROOTS was published, an attempt to do at scale what almost no pretraining corpus does: document provenance and licensing deliberately.

The engineering reality echoed every large run's war stories (see [[Deep Dive - Anatomy of a Pretraining Run]]). BLOOM used **Megatron-DeepSpeed 3D parallelism**, composing [[Concept - Tensor and Pipeline Parallelism|tensor parallelism (TP=4, within a node over NVLink) and pipeline parallelism (PP=12, across nodes)]] with [[Concept - Data Parallelism and ZeRO|ZeRO-backed data parallelism (DP=8)]] — $4 \times 12 \times 8 = 384$ GPUs, exactly. The arithmetic that forces this: 176B parameters in bf16 is ~352 GB of weights alone; add Adam's fp32 optimizer states and master copy (~12 bytes/param → ~2.1 TB) and gradients, and the training state runs into multiple terabytes against 80 GB per GPU. No single GPU, and no single axis of parallelism, holds it — hence 3D.

Crucially, BLOOM was preceded by a **failed 104B-parameter experimental run** whose instabilities were the actual curriculum. That earlier run taught the team the concrete fixes — moving from fp16 to **bf16** to dodge loss-scaling underflow, adding the embedding LayerNorm, and tuning throughput to reach usable model-FLOPs utilization — that made the 176B run survivable. The 104B failure is why the 176B succeeded; the debugging happened on the cheaper model.

BLOOM shipped under the **BigScience RAIL (Responsible AI License)**: an [[Reference - Open Weights Licensing|open-weights license with behavioral-use restrictions]] — you get the weights and can build on them, but the license enumerates prohibited uses. It was a deliberate governance experiment, staking out a middle path between fully-permissive (Apache/MIT) and closed, and it seeded the OpenRAIL family that later models adopted.

Finally, the run reported **honest carbon accounting** (Luccioni et al., 2022, *Estimating the Carbon Footprint of BLOOM*): roughly **~25 tonnes of CO₂-equivalent** for the dynamic power of the final training run, kept low largely because Jean Zay runs on **France's low-carbon nuclear grid**; the full lifecycle figure including hardware embodied emissions and idle power roughly doubled that. Publishing a training carbon number at all was, and largely remains, rare.

## The lesson

Stated mechanically: **frontier-scale pretraining is achievable outside big tech — via public compute plus open collaboration — but the coordination overhead is the binding constraint, not the compute.** The 176B run itself was, in engineering terms, comparable to a corporate run of the era; what was different, and expensive, was organizing a thousand volunteers across sixty countries into working groups for data, modeling, tokenization, evaluation, and governance, then keeping them aligned for a year. BLOOM proves the *technical* barrier to non-corporate frontier work is surmountable on a national supercomputer grant; it also demonstrates that the *organizational* barrier is where the real cost migrates.

The transparency is the transferable asset. Because BLOOM published its corpus process, its live loss curves, its parallelism config, its failure (the 104B run), and its carbon, it is one of the few genuinely **reproducible** frontier runs — a template that the fully-open lineage (OLMo, Pythia) later formalized. The contrast with the corporate norm is the point: where a modern lab's "technical report" often omits architecture and compute, BigScience over-documented on principle. For sovereign and academic AI efforts, BLOOM is the reference implementation of "how to do a big run in the open," including the parts that hurt.

The non-obvious operational insight, and the one that connects it to every other large run: **the failed smaller run is not wasted compute — it is the debugging budget.** BigScience's 104B instabilities bought the fixes (bf16, embedding norm) that de-risked the 176B run. Teams that skip the deliberately-instrumented smaller run and jump straight to the flagship pay for the same lessons at 176B prices, on hardware that fails often enough to make every restart expensive (see [[Gotchas - Hardware Failures at Scale]]).

## Evidence status

**Verified — extensively.** BLOOM may be the best-documented large training run in existence. The model, the ROOTS corpus, the BLOOM paper (BigScience Workshop et al., 2022), the carbon-footprint paper (Luccioni et al., 2022), Stas Bekman's public engineering chronicles, the archived TensorBoard, and the Megatron-DeepSpeed configuration are all public and cross-checkable. This is the opposite of folklore: nearly every claim here traces to a primary artifact. The only soft edges are exact per-incident firefighting details, which are recorded in the chronicles but not always with the precision of a formal incident log. Its documentation is a deliberate contrast to — and complement of — the OPT-175B logbook.

## Connections
- [[Lore - The OPT-175B Logbook]] — the corporate parallel: a contemporaneous 175B open reproduction with its own public logbook; BLOOM is the academic counterpart doing the same transparency from outside big tech.
- [[Deep Dive - Anatomy of a Pretraining Run]] — BLOOM is a fully-documented instance of the generic run this note describes; read it for the mechanisms behind the firefighting.
- [[Concept - Tensor and Pipeline Parallelism]] — the TP=4 / PP=12 halves of BLOOM's 3D parallelism; the reason the model was sharded the way it was.
- [[Concept - Data Parallelism and ZeRO]] — the DP=8, ZeRO-backed outer axis that completes the 384-GPU 3D grid and shards the terabyte-scale optimizer state.
- [[Reference - Open Weights Licensing]] — BLOOM's RAIL license is the canonical example of the behavioral-use "middle path" that note catalogs.
- [[Reference - The AI Lab Landscape]] — BigScience is the defunct-but-influential fully-open collaboration on that map; BLOOM is why it belongs there.
- [[Gotchas - Hardware Failures at Scale]] — the dead-GPU/ECC/restart reality that BLOOM's chronicles document and that its checkpoint cadence was built to survive.

## Sources
- BigScience Workshop et al. (2022) — *BLOOM: A 176B-Parameter Open-Access Multilingual Language Model*. The primary paper: architecture (ALiBi, embedding norm), ROOTS corpus, 46+13 languages, training setup.
- Luccioni, Viguier & Ligozat (2022) — *Estimating the Carbon Footprint of BLOOM*. The ~25-tonne dynamic-training figure and its low-carbon-grid explanation.
- Bekman, S. (2022) — BigScience engineering *chronicles* and *lessons learned* writeups. The day-to-day firefighting record, including the 104B failed run and the bf16/embedding-norm fixes.
