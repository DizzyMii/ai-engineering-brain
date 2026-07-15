---
tags: [home, domain/home, level/surface]
aliases: []
summary: "Vault home: orientation to ~660 notes across 25 domains, the Engineering Wing, the Applied Wing, and the guided ladders."
---

# Home

This vault holds roughly 660 interconnected notes spread across 25 domains, covering AI engineering from the math substrate up through frontier deployment economics. Every topic is laddered from surface (what it is, why it exists) through core and advanced, out to frontier and unicorn — the tribal knowledge almost nobody writes down. Nineteen domains make up the **Engineering Wing** (01-19): the mechanisms, architectures, training runs, and infrastructure that make models work. Five more make up the **Applied Wing** (20-24): where those models actually landed in software, business, and the economy, and what that's worth.

## The Engineering Wing (01-19)

- 01 — [[MOC - Foundations]] — the math and numerics substrate (linear algebra, probability, floating point) every other domain quietly assumes.
- 02 — [[MOC - Neural Networks]] — how a network turns inputs into predictions and a loss signal into updated weights.
- 03 — [[MOC - Architectures]] — the block diagram (attention, MoE, positional encoding, sequence mixers) that sets a model's cost and quality.
- 04 — [[MOC - Training at Scale]] — parallelism, precision, and the mechanics of turning a dataset and architecture into trained weights across thousands of GPUs.
- 05 — [[MOC - Data Engineering]] — sourcing, filtering, deduplicating, and mixing the corpus a model actually trains on.
- 06 — [[MOC - Post-Training]] — SFT, RLHF, DPO/GRPO: the pipeline that turns a raw next-token predictor into a deployed assistant.
- 07 — [[MOC - Inference & Serving]] — the request lifecycle (KV cache, batching, quantization, speculative decoding) that decides tokens-per-dollar at scale.
- 08 — [[MOC - Hardware & Systems]] — GPU/TPU internals, kernels, and cluster networking, the physical substrate every latency and cost claim is bounded by.
- 09 — [[MOC - Prompting & Context]] — shaping what goes into the context window, and why cosmetic-looking choices swing output quality by double digits.
- 10 — [[MOC - Agents]] — the control loop, tool use, planning, and memory that turn a text-completion engine into a system that acts.
- 11 — [[MOC - Retrieval & RAG]] — turning documents into retrievable facts a frozen model wasn't trained on.
- 12 — [[MOC - Fine-Tuning]] — adapting a pretrained model's weights, full FT through the LoRA/PEFT family, once prompting and retrieval run out of runway.
- 13 — [[MOC - Evaluation]] — turning model behavior into a trustworthy number, and catching the ways a benchmark quietly stops measuring what it claims to.
- 14 — [[MOC - Safety & Interpretability]] — keeping a model from being manipulated, and understanding what it's actually computing well enough to catch failures no transcript would surface.
- 15 — [[MOC - Multimodal]] — aligning images, audio, and video with language: vision-language models and diffusion/audio generation.
- 16 — [[MOC - Production & Ops]] — deploying, observing, costing, and keeping an LLM-backed system alive under real traffic and provider drift.
- 17 — [[MOC - Classical ML]] — the non-neural toolkit (tree ensembles, gradient boosting, calibration) that still runs most production tabular systems.
- 18 — [[MOC - Frontier & Esoterica]] — training-dynamics anomalies and open problems that don't fit cleanly into any other domain's narrative.
- 19 — [[MOC - Ecosystem & History]] — labs, model lineage, licensing, and the field's landmark war stories, the context behind every benchmark headline.

## The Applied Wing (20-24)

- 20 — [[MOC - AI in Software Engineering]] — what AI coding tools measurably do, where the RCTs agree, where they contradict, and how to deploy them safely.
- 21 — [[MOC - AI Across Business Functions]] — where GenAI actually shipped across support, legal, health, education, marketing, finance, HR, and sales, and what happened when it did.
- 22 — [[MOC - AI Economics]] — value capture, unit economics, pricing, and moats: where the money in AI actually goes.
- 23 — [[MOC - Adoption & Blockers]] — why roughly 95% of enterprise GenAI pilots never reach production, mechanism by mechanism.
- 24 — [[MOC - Trajectory & Navigation]] — capability, cost, and deployment trajectories separated from vendor forecasting, and what to build regardless of which branch wins.

## Ladders

Guided walks through existing notes, surface to unicorn — pick the track that matches where you're headed:

- [[Ladder - Zero to Inference Engineer]] — from matmul arithmetic to running and tuning production LLM serving: KV cache, batching, quantization, kernels, and the serving war stories.
- [[Ladder - Zero to Pretraining Engineer]] — from backprop to babysitting a multi-thousand-GPU run: parallelism, precision, data pipelines, stability, and the loss-spike lore.
- [[Ladder - Zero to Post-Training Engineer]] — from KL divergence to running SFT/RLHF/RLVR pipelines and recognizing reward hacking before it ships.
- [[Ladder - Zero to AI Application Engineer]] — from prompting to shipping reliable LLM products: context engineering, RAG, agents, evals, and production ops.
- [[Ladder - Zero to Interpretability Engineer]] — from the residual stream to SAEs, activation patching, and the model-internals folklore.
- [[Ladder - Zero to Multimodal Engineer]] — from ViT and CLIP through VLMs, diffusion, and audio: how models see, hear, and generate.
- [[Ladder - Navigating the AI Economy]] — a guided, nineteen-step walk through the Applied Wing (20-24): what actually happened, what it costs, what blocks it, where it's going, and how to play it.

## Where to go deeper

Once you've oriented, [[Reference - The 2026 Navigation Cheatsheet]] is the synthesized, date-stamped landing point: what's profitable now, what's overhyped, the cost and reliability curves, and the forecast spread — the deeper note this orientation page is the front door to.
