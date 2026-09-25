---
tags: [lore, domain/ecosystem-history, level/unicorn]
aliases: [BLOOM, BigScience, BLOOM 176B, BigScience Workshop]
summary: "BigScience's BLOOM 176B: 1000+ researchers trained a fully-open multilingual LLM on a French public supercomputer, firefighting and all."
---

> **One-paragraph hook:** In 2022 a one-year academic collaboration of a thousand people from sixty countries trained a 176B-parameter multilingual language model on a grant of public supercomputer time in France. No corporate lab, no ad revenue, no closed API at the end. BLOOM proves frontier-scale pretraining can happen outside big tech, and it's the most transparent training run ever conducted: public loss curves, a documented corpus, a novel license and honest carbon numbers. It's also a case study in what the coordination overhead of working that way costs.

## What happened

**BigScience** (2021–2022) was a **one-year open research workshop** that brought together **1000+ researchers from 60+ countries**. Hugging Face did much of the coordinating, and the whole thing was organized around **Jean Zay**, the French national public supercomputer run by IDRIS/GENCI. The compute came from a public research grant (millions of GPU-hours), not a corporate cluster, and that was the point: frontier-scale training run as an academic, publicly funded, radically open collaboration, a deliberate counterweight to the corporate labs (see [[Reference - The AI Lab Landscape]]).

The flagship was **BLOOM 176B** (BigScience, July 2022), a 176-billion-parameter decoder-only model covering **46 natural languages and 13 programming languages**. It trained on the **ROOTS corpus**, ~**1.6 TB** of text (~366B tokens) assembled through a documented, consent-aware data-governance process instead of an anonymous web scrape. Training ran on **384 A100-80GB GPUs** for roughly **3.5 months** (11 March – 6 July 2022). The architecture was GPT-3-shaped with two changes made for stability: **ALiBi** positional biases in place of learned positional embeddings, and an **extra LayerNorm right after the embedding layer**, added because earlier experiments diverged without it.

What makes BLOOM lore and not just a spec sheet is how **open the process was**, end to end:

- A **public TensorBoard** streamed the live loss curve during the run. Anyone on the internet could watch a 176B model train in real time, spikes included.
- **Stas Bekman's engineering chronicles** (the `bigscience-workshop` "chronicles" and "lessons learned" writeups) recorded the day-to-day firefighting in the spirit of [[Lore - The OPT-175B Logbook|Meta's OPT-175B logbook]], from a non-corporate team.
- The **data-governance and consent framework** for ROOTS was published, an attempt to do at scale what almost no pretraining corpus does: document provenance and licensing on purpose.

The engineering matched every large run's war stories (see [[Deep Dive - Anatomy of a Pretraining Run]]). BLOOM used **Megatron-DeepSpeed 3D parallelism**, combining [[Concept - Tensor and Pipeline Parallelism|tensor parallelism (TP=4, within a node over NVLink) and pipeline parallelism (PP=12, across nodes)]] with [[Concept - Data Parallelism and ZeRO|ZeRO-backed data parallelism (DP=8)]]: $4 \times 12 \times 8 = 384$ GPUs, exactly. The arithmetic that forces it: 176B parameters in bf16 is ~352 GB of weights alone. Add Adam's fp32 optimizer states and master copy (~12 bytes/param → ~2.1 TB) plus gradients, and training state runs to multiple terabytes against 80 GB per GPU. No single GPU and no single axis of parallelism can hold that, hence 3D.

BLOOM was preceded by a **failed 104B-parameter experimental run**, and its instabilities were the real curriculum. That run taught the team the fixes that made 176B survivable: switching from fp16 to **bf16** to avoid loss-scaling underflow, adding the embedding LayerNorm, and tuning throughput to reach usable model-FLOPs utilization. The 104B failure is why the 176B run succeeded. The debugging happened on the cheaper model.

BLOOM shipped under the **BigScience RAIL (Responsible AI License)**, an [[Reference - Open Weights Licensing|open-weights license with behavioral-use restrictions]]. You get the weights and can build on them, but the license lists prohibited uses. It was a deliberate governance experiment, a middle path between fully permissive (Apache/MIT) and closed, and it seeded the OpenRAIL family later models adopted.

The run also reported **honest carbon accounting** (Luccioni et al., 2022, *Estimating the Carbon Footprint of BLOOM*): roughly **~25 tonnes of CO₂-equivalent** for the dynamic power of the final training run, kept low mostly because Jean Zay runs on **France's low-carbon nuclear grid**. The full lifecycle figure, including embodied hardware emissions and idle power, was roughly double. Publishing a training carbon number at all was rare then and mostly still is.

## The lesson

**Frontier-scale pretraining is achievable outside big tech with public compute and open collaboration, but coordination overhead is the real limit, more than compute.** In engineering terms the 176B run was comparable to a corporate run of its era. What differed, and cost a lot, was organizing a thousand volunteers in sixty countries into working groups for data, modeling, tokenization, evaluation and governance, and keeping them aligned for a year. BLOOM shows the *technical* barrier to non-corporate frontier work can be cleared with a national supercomputer grant, and that the cost moves to the *organizational* barrier.

The transparency is what transfers. BLOOM published its corpus process, live loss curves, parallelism config, its failure (the 104B run) and its carbon, which makes it one of the few properly **reproducible** frontier runs and a template the fully open lineage (OLMo, Pythia) later formalized. The contrast with the corporate norm matters: a modern lab's "technical report" often omits architecture and compute, and BigScience over-documented on principle. For sovereign and academic AI efforts, BLOOM is the reference implementation of doing a big run in the open, painful parts included.

The operational point that links it to every other large run: **the failed smaller run is your debugging budget, not wasted compute.** BigScience's 104B instabilities bought the fixes (bf16, embedding norm) that de-risked 176B. Teams that skip a deliberately instrumented smaller run and go straight to the flagship pay for the same lessons at 176B prices, on hardware that fails often enough to make every restart expensive (see [[Gotchas - Hardware Failures at Scale]]).

## Evidence status

**Verified, extensively.** BLOOM may be the best-documented large training run there is. The model, the ROOTS corpus, the BLOOM paper (BigScience Workshop et al., 2022), the carbon-footprint paper (Luccioni et al., 2022), Stas Bekman's public engineering chronicles, the archived TensorBoard and the Megatron-DeepSpeed configuration are all public and cross-checkable. Nearly every claim here traces to a primary artifact, the opposite of folklore. The only soft edges are exact per-incident firefighting details, which the chronicles record but not always with a formal incident log's precision. Its documentation deliberately contrasts with, and complements, the OPT-175B logbook.

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
