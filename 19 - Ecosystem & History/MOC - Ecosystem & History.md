---
tags: [moc, domain/ecosystem-history, level/surface]
aliases: []
summary: "Map of Ecosystem & History: labs, model lineage, open-vs-closed licensing, the hardware market, and the field's landmark war stories."
---

# MOC - Ecosystem & History

This domain owns the field's social, organizational, and historical layer: who built what, when, under what license, and why — the context that turns a benchmark number into an informed bet instead of a headline. It traces the mechanism behind AI's booms and winters, maps the labs and their strategic postures, tracks how models actually descend from one another, and catalogs the recurring traps in reading a lab's own announcement. It matters because every architecture, training, or deployment decision made elsewhere in this vault is also, implicitly, a bet on an organization's licensing terms, a hardware supplier's compute allocation, or a lineage's legal exposure — bets this domain makes explicit. It is also where the vault keeps its best-verified war stories: the training runs, leaks, and origin stories that turn abstract mechanisms into lived, checkable history.

## Start here

- **Surface** → [[Deep Dive - From Perceptron to ChatGPT]] — the recurring data+compute+algorithm unlock behind every AI boom, and the funding-gap signature behind every winter, from the 1958 perceptron to the 2025 reasoning turn.
- **Core** → [[Reference - The AI Lab Landscape]] — who's actually building frontier and open models, and the five strategic postures (platform-API, safety-brand, commoditize-the-complement, sovereign, efficiency-challenger) that predict what they'll release next.
- **Advanced** → [[Concept - The Open vs Closed Model Divide]] — why open vs. closed weights is a business decision about capital recovery and distillation risk, not an ideology, and why the same lab makes both choices.
- **Frontier** → [[Breakdown - DeepSeek]] — the release run that erased ~$600B of NVIDIA market cap in a day and compressed the open-vs-closed reasoning gap from quarters to weeks.
- **Unicorn** → [[Lore - The Attention Is All You Need Origin Story]] — eight authors, a Beatles-referenced title, and a diaspora that went on to found or lead a meaningful fraction of the LLM industry.

## The historical arc, and how the field actually learns

- [[Deep Dive - From Perceptron to ChatGPT]] — the mechanism behind every AI spring (an old idea meets a newly abundant resource) and every winter (promise outruns delivery, funding evaporates), walked from Rosenblatt's perceptron to reasoning models.
- [[Concept - The Preprint and Social-Media Research Culture]] — why ML effectively abandoned journal peer review for an arXiv-plus-X pipeline that rewards being first and loud over right and reproducible.
- [[Reference - Where Real AI Knowledge Lives]] — the source map (lab tech reports, engineering blogs, code, named practitioners, communities) for finding real signal instead of marketing.
- [[Gotchas - Reading Model Announcements]] — eight recurring traps in lab launches, from a silently swapped API model to pass@k-inflated benchmark scores.

## Labs, models, and lineage

- [[Reference - The AI Lab Landscape]] — the frontier-closed, open-weight-major, Chinese, research/fully-open, and enterprise/niche labs, plus the acqui-hire pattern reshaping the roster.
- [[Reference - Model Genealogy]] — the family trees (GPT, Llama, Mistral, Qwen, DeepSeek, GLM, Claude, and more) and the five mechanisms of descent: architecture reuse, continued pretraining, distillation, merging, LoRA adapters.
- [[Breakdown - Hugging Face]] — how a 2016 chatbot app's side-library became the field's default model registry, and why `from_pretrained` is closer to a lingua franca than any product name should be.
- [[Breakdown - DeepSeek]] — the High-Flyer hedge-fund spinout whose V3/R1 release run combined frontier-adjacent capability, a disclosed ~$5.6M training cost, and an MIT license into the sharpest recent shock to the compute-moat narrative.
- [[Snippet - Tracing Model Lineage via Hugging Face Metadata]] — runnable code that corroborates a model's self-reported `base_model` claim against `config.json` geometry and tokenizer-hash fingerprints.

## Open vs. closed, licensing, and choosing an ecosystem

- [[Concept - The Open vs Closed Model Divide]] — open vs. closed weights as a rational business choice (capital recovery vs. commoditize-the-complement), and why the capability gap between them has been compressing.
- [[Reference - Open Weights Licensing]] — what Apache 2.0, MIT, the Llama Community License, Gemma Terms, and RAIL/OpenRAIL actually permit and restrict, and why the OSAID fight means "open" isn't one claim.
- [[Decision - Which Model Ecosystem to Bet On]] — default to a closed frontier API behind a provider-agnostic gateway and re-shop quarterly; deviate only when a hard licensing, volume, or data-residency constraint forces it.
- [[Checklist - Vetting an Open-Weights Model for Production]] — the pre-adoption go/no-go across license, provenance/supply-chain, lineage, real capability, format fit, and geopolitical sign-off.

## Hardware and the compute substrate

- [[Reference - The AI Hardware Market]] — NVIDIA's ~80-90% training-accelerator share, the CoWoS/HBM packaging chokepoints that actually gate GPU supply, export controls, and why every merchant-silicon challenger with real traction attacks inference, not training.
- [[Concept - The CUDA Moat]] — 15+ years of self-reinforcing kernel network effects, not silicon superiority, explain why buyers default to NVIDIA even when a rival wins on paper FLOPs/dollar.

## War stories

- [[Lore - The Attention Is All You Need Origin Story]] — the 2017 Transformer paper's eight authors, its Beatles-referenced title, and a diaspora (Cohere, Character.AI, Adept, Sakana, and more) that scattered to build a chunk of the industry the paper enabled.
- [[Lore - The OPT-175B Logbook]] — Meta's 2022 daily training chronicle proved that at 175B scale, pretraining is a checkpoint-cadence and hardware-triage operations problem as much as an ML one.
- [[Lore - The BLOOM Training Run]] — 1000+ researchers from 60+ countries trained a fully-open 176B multilingual model on a French public supercomputer, with a live public loss curve and honest carbon accounting.
- [[Lore - The LLaMA Leak]] — Meta's gated LLaMA 1 research release hit BitTorrent within about a week in March 2023, accidentally igniting llama.cpp, Alpaca, Vicuna, and the entire consumer-hardware open-weights scene.

## Adjacent domains

- [[MOC - Architectures]] — the Transformer this domain's history and lore orbit (Attention Is All You Need, the GPT/Llama lineages) is built and explained mechanically on that side of the vault.
- [[MOC - Hardware & Systems]] — the GPU/TPU internals and kernel programming that sit underneath this domain's hardware-market and CUDA-moat notes.
- [[MOC - AI Economics]] — the unit economics, pricing, and capex accounting that explain *why* labs choose the open/closed postures and pricing wars documented here.
- [[MOC - Post-Training]] — RLHF and reasoning-training mechanisms (InstructGPT, GRPO) that this domain's timeline and lab breakdowns treat as organizational history rather than re-deriving.
