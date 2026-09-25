---
tags: [home, domain/home, level/surface]
aliases: []
summary: "Vault home: orientation to ~660 notes across 25 domains, the Engineering Wing, the Applied Wing, and the guided ladders."
---

# Home

About 660 linked notes across 25 domains, covering AI engineering from the math substrate up to frontier deployment economics. Each topic is laddered surface (what it is, why it exists), core, advanced, frontier, unicorn. That last rung is the tribal knowledge almost nobody writes down. Nineteen domains form the **Engineering Wing** (01-19): the mechanisms, architectures, training runs and infrastructure that make models work. Five more form the **Applied Wing** (20-24): where those models landed in software, business and the economy, and what that's worth.

## The Engineering Wing (01-19)

- 01 [[MOC - Foundations]]: linear algebra, probability, floating point. The math and numerics every other domain assumes.
- 02 [[MOC - Neural Networks]]: how a network turns inputs into predictions, and a loss signal into updated weights.
- 03 [[MOC - Architectures]]: the block diagram (attention, MoE, positional encoding, sequence mixers) that sets a model's cost and quality.
- 04 [[MOC - Training at Scale]]: parallelism, precision, and the mechanics of turning a dataset and an architecture into trained weights across thousands of GPUs.
- 05 [[MOC - Data Engineering]]: sourcing, filtering, deduplicating and mixing the corpus a model trains on.
- 06 [[MOC - Post-Training]]: SFT, RLHF, DPO/GRPO. The pipeline from raw next-token predictor to deployed assistant.
- 07 [[MOC - Inference & Serving]]: the request lifecycle (KV cache, batching, quantization, speculative decoding) that sets tokens-per-dollar at scale.
- 08 [[MOC - Hardware & Systems]]: GPU/TPU internals, kernels and cluster networking. Every latency and cost claim is bounded by this layer.
- 09 [[MOC - Prompting & Context]]: shaping what goes into the context window, and why choices that look cosmetic swing output quality by double digits.
- 10 [[MOC - Agents]]: the control loop, tool use, planning and memory that turn a text-completion engine into a system that acts.
- 11 [[MOC - Retrieval & RAG]]: turning documents into retrievable facts a frozen model wasn't trained on.
- 12 [[MOC - Fine-Tuning]]: changing a pretrained model's weights, from full FT to the LoRA/PEFT family, once prompting and retrieval run out of runway.
- 13 [[MOC - Evaluation]]: turning model behavior into a number you can trust, and catching the ways a benchmark stops measuring what it claims to.
- 14 [[MOC - Safety & Interpretability]]: keeping a model from being manipulated, and understanding what it computes well enough to catch failures no transcript would show.
- 15 [[MOC - Multimodal]]: aligning images, audio and video with language. Vision-language models, diffusion and audio generation.
- 16 [[MOC - Production & Ops]]: deploying, observing, costing and keeping an LLM-backed system alive under real traffic and provider drift.
- 17 [[MOC - Classical ML]]: the non-neural toolkit (tree ensembles, gradient boosting, calibration) that still runs most production tabular systems.
- 18 [[MOC - Frontier & Esoterica]]: training-dynamics anomalies and open problems that don't fit neatly into any other domain.
- 19 [[MOC - Ecosystem & History]]: labs, model lineage, licensing and the field's landmark war stories. The context behind every benchmark headline.

## The Applied Wing (20-24)

- 20 [[MOC - AI in Software Engineering]]: what AI coding tools measurably do, where the RCTs agree and where they contradict, and how to deploy them safely.
- 21 [[MOC - AI Across Business Functions]]: where GenAI shipped across support, legal, health, education, marketing, finance, HR and sales, and what happened when it did.
- 22 [[MOC - AI Economics]]: value capture, unit economics, pricing and moats. Where the money in AI goes.
- 23 [[MOC - Adoption & Blockers]]: why roughly 95% of enterprise GenAI pilots never reach production, one mechanism at a time.
- 24 [[MOC - Trajectory & Navigation]]: capability, cost and deployment trajectories with the vendor forecasting stripped out, and what to build whichever branch wins.

## Ladders

Guided walks through existing notes, surface to unicorn. Pick the one that matches where you're headed:

- [[Ladder - Zero to Inference Engineer]]: from matmul arithmetic to running and tuning production LLM serving. KV cache, batching, quantization, kernels, serving war stories.
- [[Ladder - Zero to Pretraining Engineer]]: from backprop to babysitting a multi-thousand-GPU run. Parallelism, precision, data pipelines, stability, loss-spike lore.
- [[Ladder - Zero to Post-Training Engineer]]: from KL divergence to running SFT/RLHF/RLVR pipelines and spotting reward hacking before it ships.
- [[Ladder - Zero to AI Application Engineer]]: from prompting to shipping LLM products that hold up. Context engineering, RAG, agents, evals, production ops.
- [[Ladder - Zero to Interpretability Engineer]]: from the residual stream to SAEs, activation patching and model-internals folklore.
- [[Ladder - Zero to Multimodal Engineer]]: from ViT and CLIP through VLMs, diffusion and audio. How models see, hear and generate.
- [[Ladder - Navigating the AI Economy]]: nineteen steps through the Applied Wing (20-24). What happened, what it costs, what blocks it, where it's going, how to play it.

## Where to go deeper

After orienting, go to [[Reference - The 2026 Navigation Cheatsheet]]. It's the synthesized, date-stamped landing point: what's profitable now, what's overhyped, the cost and reliability curves, and the forecast spread.
